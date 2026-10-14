"""Single-operator web administration and scheduled processing.

Run one process per data directory. OAuth and secrets stay in private local files.
"""
import copy
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .core import process
from .gmail import messages


def private_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else copy.deepcopy(default)


def validate_settings(value):
    if not isinstance(value, dict):
        raise ValueError('Cấu hình phải là một đối tượng.')
    def integer(name, raw, minimum, maximum):
        if isinstance(raw, bool) or not isinstance(raw, int) or not minimum <= raw <= maximum:
            raise ValueError(f'{name} phải từ {minimum} đến {maximum}.')
        return raw
    def text(name, raw, maximum=500, empty=False):
        if not isinstance(raw, str) or len(raw) > maximum or (not empty and not raw.strip()):
            raise ValueError(f'{name} không hợp lệ (tối đa {maximum} ký tự).')
        return raw.strip()
    source = value.get('source', 'demo')
    if source not in ('demo', 'gmail'):
        raise ValueError('Nguồn chưa được hỗ trợ.')
    zone = text('Múi giờ', value.get('timezone'))
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('Múi giờ không hợp lệ.') from None
    summary = value.get('summary')
    if not isinstance(summary, dict) or summary.get('mode') not in ('extractive', 'openai'):
        raise ValueError('Chế độ tóm tắt không hợp lệ.')
    if summary['mode'] == 'openai' and summary.get('ai_consent') is not True:
        raise ValueError('Cần xác nhận đồng ý xử lý nội dung qua OpenAI.')
    rules = value.get('rules')
    if not isinstance(rules, list) or len(rules) > 100:
        raise ValueError('Tối đa 100 quy tắc.')
    clean_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError('Quy tắc không hợp lệ.')
        clean = {'category': text('Tên nhóm', rule.get('category'), 100)}
        for field in ('keywords', 'senders'):
            entries = rule.get(field, [])
            if not isinstance(entries, list) or len(entries) > 100:
                raise ValueError('Tối đa 100 từ khóa/người gửi mỗi quy tắc.')
            clean[field] = [text('Từ khóa/người gửi', item, 200) for item in entries]
        clean_rules.append(clean)
    unmatched = value.get('unmatched_category')
    if unmatched is not None:
        unmatched = text('Nhóm mặc định', unmatched, 100)
    enabled = value.get('schedule_enabled', False)
    if not isinstance(enabled, bool):
        raise ValueError('Trạng thái lịch chạy không hợp lệ.')
    return {'source': source, 'schedule_enabled': enabled,
            'gmail_query': text('Bộ lọc Gmail', value.get('gmail_query'), 1000),
            'interval_seconds': integer('Chu kỳ (giây)', value.get('interval_seconds'), 60, 604800),
            'timezone': zone, 'rules': clean_rules, 'unmatched_category': unmatched,
            'summary': {'mode': summary['mode'],
                        'max_chars': integer('Độ dài trích đoạn', summary.get('max_chars', 1200), 100, 10000),
                        'max_input_chars': integer('Giới hạn đầu vào AI', summary.get('max_input_chars', 12000), 1000, 100000),
                        'model': text('Mô hình', summary.get('model', 'gpt-4o-mini'), 100),
                        'ai_consent': summary.get('ai_consent') is True}}


class MissingAIKey(RuntimeError):
    pass


def error_message(error):
    if isinstance(error, MissingAIKey):
        return 'Chưa có OpenAI API key. Lưu key trong Cài đặt hoặc chọn trích đoạn miễn phí.'
    if isinstance(error, FileNotFoundError):
        return 'Thiếu thông tin kết nối. Vào Cài đặt để kết nối Gmail.'
    if isinstance(error, HTTPError):
        if error.code in (401, 403):
            return 'Dịch vụ từ chối truy cập. Kiểm tra quyền Gmail/API hoặc kết nối lại tài khoản.'
        if error.code == 429:
            return 'Dịch vụ đang giới hạn lượt gọi. Kiểm tra hạn mức và thử lại sau.'
        return f'Dịch vụ trả lỗi HTTP {error.code}. Thử lại sau hoặc kiểm tra cài đặt.'
    if isinstance(error, (URLError, TimeoutError)):
        return 'Không kết nối được dịch vụ. Kiểm tra mạng rồi thử lại.'
    return 'Không xử lý được. Kiểm tra kết nối, cấu hình và thử lại; dữ liệu đã lưu được giữ nguyên.'


class Admin:
    def __init__(self, base, data_root=None):
        self.base = Path(base).resolve()
        self.root = Path(data_root or self.base / '.local').resolve()
        self.private = self.root / 'admin'
        self.private.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.settings_path = self.private / 'settings.json'
        self.credentials = self.private / 'gmail-client.json'
        self.token = self.private / 'gmail-token.json'
        defaults = read_json(self.base / 'config.json', {})
        defaults.update(source='demo', schedule_enabled=False)
        self.settings = validate_settings(read_json(self.settings_path, defaults))
        self.lock = threading.RLock()
        self.run_lock = threading.Lock()
        self.stop = threading.Event()
        self.next_due = None
        self.state = read_json(self.private / 'status.json', {'last_started': None, 'last_finished': None, 'last_added': None, 'last_source': None, 'error': None})
        if self.state.get('running'):
            self.state.update(error='Lượt trước bị gián đoạn khi máy chủ dừng. Chạy lại để tiếp tục.', last_added=None)
        self.state['running'] = False
        self.scheduler = None

    def config(self):
        with self.lock:
            return copy.deepcopy(self.settings)

    def save_settings(self, value):
        clean = validate_settings(value)
        with self.lock:
            private_json(self.settings_path, clean)
            self.settings = clean
            self.next_due = time.time() + clean['interval_seconds'] if clean['schedule_enabled'] else None
        return clean

    def status(self):
        with self.lock:
            return {**self.state, 'next_run': self.next_due if self.settings['schedule_enabled'] else None,
                    'schedule_enabled': self.settings['schedule_enabled'],
                    'gmail_connected': self.token.exists(), 'gmail_client_configured': self.credentials.exists(),
                    'ai_key_configured': bool(os.environ.get('OPENAI_API_KEY') or (self.private / 'ai-key.json').exists())}

    def start_run(self, source=None):
        if not self.run_lock.acquire(blocking=False):
            return False
        try:
            config = self.config()
            source = source or config['source']
            if source not in ('demo', 'gmail'):
                raise ValueError('Nguồn không hợp lệ.')
            with self.lock:
                self.state.update(running=True, last_started=datetime.now(timezone.utc).isoformat(), last_source=source, error=None)
            thread = threading.Thread(target=self._run, args=(config, source), daemon=True)
            thread.start()
            return True
        except Exception:
            self.run_lock.release()
            raise

    def _run(self, config, source):
        try:
            config['data_dir'] = str(self.root / ('demo' if source == 'demo' else 'gmail'))
            if source == 'demo':
                config['summary']['mode'] = 'extractive'
                incoming = read_json(self.base / 'examples/messages.json', [])
            else:
                key = read_json(self.private / 'ai-key.json', {}).get('key')
                config['_api_key'] = key
                if config['summary']['mode'] == 'openai' and not (key or os.environ.get('OPENAI_API_KEY')):
                    raise MissingAIKey()
                incoming = messages(config, self.credentials, self.token)
            added = process(incoming, config, source)
            with self.lock:
                self.state.update(last_added=added, error=None)
        except Exception as error:
            with self.lock:
                self.state.update(last_added=None, error=error_message(error))
        finally:
            try:
                with self.lock:
                    self.state.update(running=False, last_finished=datetime.now(timezone.utc).isoformat())
                    self.next_due = time.time() + self.settings['interval_seconds'] if self.settings['schedule_enabled'] else None
                    private_json(self.private / 'status.json', self.state)
            finally:
                self.run_lock.release()

    def start_scheduler(self):
        if self.scheduler and self.scheduler.is_alive():
            return
        with self.lock:
            if self.settings['schedule_enabled']:
                self.next_due = time.time() + self.settings['interval_seconds']
        def loop():
            while not self.stop.wait(1):
                with self.lock:
                    due = self.settings['schedule_enabled'] and self.next_due is not None and time.time() >= self.next_due
                if due:
                    self.start_run()
        self.scheduler = threading.Thread(target=loop, daemon=True)
        self.scheduler.start()

    def notes(self, source, day='', search='', category=''):
        if source not in ('demo', 'gmail'):
            raise ValueError('Nguồn không hợp lệ.')
        database = self.root / source / 'notes.sqlite3'
        if not database.exists():
            return {'notes': [], 'total': 0, 'categories': [], 'days': []}
        with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = [dict(row) for row in connection.execute('SELECT id,sender,subject,categories,summary,received_at,day,source FROM notes ORDER BY received_at DESC,id')]
        for row in rows:
            row['categories'] = json.loads(row['categories'])
        categories = sorted({item for row in rows for item in row['categories']})
        days = sorted({row['day'] for row in rows}, reverse=True)
        filtered = [row for row in rows if (not day or row['day'] == day)
                    and (not category or category in row['categories'])
                    and (not search or search.casefold() in '\n'.join([row['subject'], row['sender'], row['summary'], *row['categories']]).casefold())]
        return {'notes': filtered[:500], 'total': len(filtered), 'categories': categories, 'days': days}


def password_record(password):
    if not isinstance(password, str) or len(password) < 12 or len(password) > 256:
        raise ValueError('Mật khẩu cần từ 12 đến 256 ký tự.')
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600000).hex()
    return {'salt': salt, 'digest': digest, 'epoch': secrets.token_hex(16)}


def verify_password(password, record):
    if not isinstance(password, str) or len(password) > 256:
        return False
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(record['salt']), 600000).hex()
    return hmac.compare_digest(digest, record['digest'])
