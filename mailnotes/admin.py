"""Single-operator web administration and scheduled processing.

Run one process per data directory. OAuth and secrets stay in private local files.
"""
import copy
import hashlib
import hmac
import json
import math
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .core import process, ensure_schema, render_notes
from .gmail import messages
from .gmail_filters import validate_filter


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
    if source not in ('demo', 'gmail', 'pdf'):
        raise ValueError('Nguồn chưa được hỗ trợ.')
    zone = text('Múi giờ', value.get('timezone'))
    try:
        ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError('Múi giờ không hợp lệ.') from None
    gmail_filter = validate_filter(value.get('gmail_filter', {'period':'advanced'}))
    classification = value.get('classification_mode', 'rules')
    if classification not in ('rules', 'ai'):
        raise ValueError('Chế độ phân loại không hợp lệ.')
    summary = value.get('summary')
    if not isinstance(summary, dict) or summary.get('mode') not in ('extractive', 'openai'):
        raise ValueError('Chế độ tóm tắt không hợp lệ.')
    provider = summary.get('provider', 'deepseek')
    if provider != 'deepseek':
        raise ValueError('Nhà cung cấp AI không hợp lệ.')
    if (classification == 'ai' or summary['mode'] == 'openai') and summary.get('ai_consent') is not True:
        raise ValueError('Cần xác nhận đồng ý xử lý nội dung qua nhà cung cấp AI đã chọn.')
    raw_prices = summary.get('pricing', {})
    if not isinstance(raw_prices, dict):
        raise ValueError('Đơn giá không hợp lệ.')
    prices = {}
    for field in ('input_per_million', 'cached_input_per_million', 'output_per_million'):
        price = raw_prices.get(field)
        if price is not None and (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or not 0 <= price <= 100000):
            raise ValueError('Đơn giá phải là số không âm, tối đa 100.000 USD / triệu token.')
        prices[field] = price
    rules = value.get('rules')
    if not isinstance(rules, list) or len(rules) > 100:
        raise ValueError('Tối đa 100 quy tắc.')
    clean_rules = []
    for rule in rules:
        if not isinstance(rule, dict):
            raise ValueError('Quy tắc không hợp lệ.')
        clean = {'category': text('Tên nhóm', rule.get('category'), 100), 'description': text('Mô tả nhóm', rule.get('description', ''), 1000, empty=True)}
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
    return {'source': source, 'schedule_enabled': enabled, 'classification_mode': classification,
            'gmail_pdf': value.get('gmail_pdf', True) is True or (gmail_filter['period'] != 'advanced' and gmail_filter['pdf_only']), 'pdf_ocr': value.get('pdf_ocr', False) is True,
            'gmail_query': text('Bộ lọc Gmail', value.get('gmail_query', ''), 1000, empty=gmail_filter['period'] != 'advanced'),
            'gmail_filter': gmail_filter,
            'interval_seconds': integer('Chu kỳ (giây)', value.get('interval_seconds'), 60, 604800),
            'timezone': zone, 'rules': clean_rules, 'unmatched_category': unmatched,
            'summary': {'mode': summary['mode'], 'provider': provider,
                        'max_chars': integer('Độ dài trích đoạn', summary.get('max_chars', 1200), 100, 10000),
                        'max_input_chars': integer('Giới hạn đầu vào AI', summary.get('max_input_chars', 12000), 1000, 100000),
                        'model': text('Mô hình', summary.get('model', 'deepseek-chat'), 100),
                        'ai_consent': summary.get('ai_consent') is True, 'pricing': prices}}


class MissingAIKey(RuntimeError):
    pass


def error_message(error):
    if isinstance(error, MissingAIKey):
        return 'Chưa có API key cho nhà cung cấp AI đã chọn. Lưu key trong Cài đặt hoặc dùng rules và trích đoạn miễn phí.'
    if isinstance(error, FileNotFoundError):
        return 'Thiếu thông tin kết nối. Vào Cài đặt để kết nối Gmail.'
    if isinstance(error, HTTPError):
        host = urlsplit(error.geturl()).hostname
        # Interpret only known error codes; never display upstream messages,
        # which can include private email details, credentials or request data.
        try:
            body = json.loads(error.read(65536))
            info = body.get('error', {}) if isinstance(body, dict) else {}
            reasons = set()
            if isinstance(info, str):
                reasons.add(info)
            elif isinstance(info, dict):
                for field in ('errors', 'details'):
                    entries = info.get(field, [])
                    if isinstance(entries, list):
                        for item in entries:
                            if isinstance(item, dict) and isinstance(item.get('reason'), str):
                                reasons.add(item['reason'])
        except (ValueError, TypeError, OSError):
            reasons = set()
        if host == 'gmail.googleapis.com':
            if reasons & {'accessNotConfigured', 'SERVICE_DISABLED'}:
                return 'Gmail API chưa được bật trong project của file OAuth đang dùng. Vào Google Cloud → chọn đúng project → Gmail API → Enable, chờ vài phút rồi Chạy ngay.'
            if reasons & {'insufficientPermissions', 'ACCESS_TOKEN_SCOPE_INSUFFICIENT'}:
                return 'Kết nối hiện tại thiếu quyền đọc Gmail. Ngắt kết nối rồi Kết nối Gmail lại và cấp quyền đọc email.'
            if reasons & {'domainPolicy', 'ORG_RESTRICTION_VIOLATION'}:
                return 'Chính sách Google Workspace chặn ứng dụng. Cần quản trị viên tổ chức cho phép ứng dụng truy cập Gmail.'
            if error.code == 401:
                return 'Gmail không chấp nhận phiên truy cập. Kết nối Gmail lại rồi Chạy ngay.'
        if host == 'oauth2.googleapis.com':
            if 'invalid_grant' in reasons:
                return 'Quyền Gmail đã hết hạn hoặc bị thu hồi. Kết nối lại Gmail; token của ứng dụng Google ở chế độ Testing có thể hết hạn sau 7 ngày.'
            if reasons & {'invalid_client', 'unauthorized_client'}:
                return 'Cấu hình OAuth không còn hợp lệ. Kiểm tra OAuth client và tải lại file JSON đúng project.'
        if host == 'api.deepseek.com' and error.code == 402:
            return 'Tài khoản DeepSeek chưa đủ số dư. Kiểm tra tài khoản thanh toán của bạn.'
        if host == 'api.deepseek.com' and error.code in (401, 403):
            return 'DeepSeek từ chối API key hoặc quyền sử dụng. Kiểm tra key DeepSeek trong Cài đặt.'
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
        saved = read_json(self.settings_path, defaults)
        # A previous release offered other AI providers. Retain the private file
        # and its notes, but never call that provider after this migration.
        if saved.get('summary', {}).get('provider', 'deepseek') != 'deepseek':
            saved['summary'].update(provider='deepseek', model='deepseek-chat',
                                    mode='extractive', ai_consent=False,
                                    pricing={'input_per_million':None,
                                             'cached_input_per_million':None,
                                             'output_per_million':None})
            saved['classification_mode'] = 'rules'
        self.settings = validate_settings(saved)
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
                    'ai_key_configured': self.has_key(self.settings['summary']['provider']),
                    'ai_provider': self.settings['summary']['provider']}

    def usage(self, now=None):
        rows = []
        for source in ('gmail', 'pdf', 'demo'):
            database = self.root / source / 'notes.sqlite3'
            if not database.exists():
                continue
            with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
                connection.row_factory = sqlite3.Row
                if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_usage'").fetchone():
                    continue
                rows.extend({**dict(row), 'source': source} for row in connection.execute('SELECT * FROM ai_usage'))
        totals = {'api_calls': 0, 'local_cache_hits': 0, 'input_tokens': 0, 'cached_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, 'estimated_usd': 0.0, 'unknown_usage_calls': 0, 'unpriced_calls': 0}
        today = {name: 0 for name in totals}
        zone = ZoneInfo(self.config()['timezone'])
        today_date = (now or datetime.now(timezone.utc)).astimezone(zone).date()
        groups = {}
        def accumulate(target, row):
            if row['cache_hit']:
                target['local_cache_hits'] += 1
                return
            target['api_calls'] += 1
            for field in ('input_tokens','cached_tokens','output_tokens','total_tokens'):
                target[field] += row[field] or 0
            if row['input_tokens'] is None or row['output_tokens'] is None:
                target['unknown_usage_calls'] += 1
            if row['estimated_usd'] is None:
                target['unpriced_calls'] += 1
            else:
                target['estimated_usd'] += row['estimated_usd']
        for row in rows:
            accumulate(totals, row)
            if datetime.fromisoformat(row['created_at']).astimezone(zone).date() == today_date:
                accumulate(today, row)
            key = (row['provider'], row['model'])
            if key not in groups:
                groups[key] = {name: 0 for name in totals}
            accumulate(groups[key], row)
        recent = sorted(rows, key=lambda row:(row['created_at'],row['id']), reverse=True)[:50]
        # Return counters only, no stored price payload, email text or identifiers.
        return {'totals': totals, 'today': today, 'models': [{'provider': provider, 'model': model, **values} for (provider, model), values in groups.items()],
                'recent': [{key: row[key] for key in ('created_at','provider','model','source','cache_hit','input_tokens','cached_tokens','output_tokens','total_tokens','estimated_usd')} for row in recent]}

    def dashboard(self, source, now=None):
        notes = self.notes(source)
        config = self.config()
        zone = ZoneInfo(config['timezone'])
        today = (now or datetime.now(timezone.utc)).astimezone(zone).date()
        count_today = review_count = 0
        groups = {}
        database = self.root / source / 'notes.sqlite3'
        if database.exists():
            with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
                for categories, received in connection.execute('SELECT categories,received_at FROM notes'):
                    categories = json.loads(categories)
                    count_today += datetime.fromisoformat(received).astimezone(zone).date() == today
                    review_count += 'Cần xem lại' in categories
                    for category in set(categories):
                        groups[category] = groups.get(category, 0) + 1
        return {'source': source, 'day': today.isoformat(), 'total_notes': notes['total'],
                'received_today': count_today, 'needs_review': review_count,
                'groups': [{'name': name, 'count': count} for name, count in sorted(groups.items(), key=lambda item:(-item[1],item[0]))],
                'recent': notes['notes'][:8], 'usage': self.usage(now)}

    def key_path(self, provider):
        if provider != 'deepseek':
            raise ValueError('Chỉ hỗ trợ DeepSeek.')
        return self.private / 'deepseek-key.json'

    def has_key(self, provider):
        return bool(os.environ.get('DEEPSEEK_API_KEY') or self.key_path(provider).exists())

    def runtime_config(self, source):
        config = self.config()
        config['data_dir'] = str(self.root / source)
        key = read_json(self.key_path(config['summary']['provider']), {}).get('key')
        config['_api_key'] = key
        if source == 'demo':
            config['classification_mode'] = 'rules'
            config['summary']['mode'] = 'extractive'
        return config

    def process_pdf(self, data, filename, reprocess=False):
        from .documents import pdf_message
        if not self.run_lock.acquire(blocking=False):
            raise ValueError('Đang có lượt xử lý. Chờ hoàn tất rồi tải PDF.')
        try:
            config = self.runtime_config('pdf')
            from hashlib import sha256
            identifier = 'pdf:' + sha256(data).hexdigest()
            database = Path(config['data_dir']) / 'notes.sqlite3'
            if not reprocess and database.exists():
                with sqlite3.connect(database) as connection:
                    if connection.execute('SELECT 1 FROM notes WHERE id=?', (identifier,)).fetchone():
                        return 0
            if reprocess:
                config['_reprocess_id'] = 'pdf:' + sha256(data).hexdigest()
            document = pdf_message(data, filename, config, id=sha256(data).hexdigest(), sender='PDF tải lên', received_at=datetime.now(timezone.utc).isoformat())
            return process([document], config, 'pdf')
        finally:
            self.run_lock.release()

    def reprocess_note(self, source, identifier):
        from .documents import pdf_message
        if source not in ('gmail', 'pdf'):
            raise ValueError('Chỉ xử lý lại ghi chép có PDF gốc.')
        if not self.run_lock.acquire(blocking=False):
            raise ValueError('Đang có lượt xử lý. Vui lòng chờ.')
        try:
            database = self.root / source / 'notes.sqlite3'
            if not database.exists():
                raise ValueError('Không tìm thấy ghi chép.')
            with sqlite3.connect(database) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute('SELECT * FROM notes WHERE id=?', (identifier,)).fetchone()
            if not row or not row['file_hash']:
                raise ValueError('Ghi chép này không có bản PDF gốc đã lưu.')
            path = database.parent / 'files' / (row['file_hash'] + '.pdf')
            if not path.exists():
                raise ValueError('File PDF gốc đã bị xóa trên máy chủ.')
            config = self.runtime_config(source)
            config['_reprocess_id'] = identifier
            message = pdf_message(path.read_bytes(), row['subject'], config,
                                  id=identifier.split(':', 1)[1], sender=row['sender'],
                                  received_at=row['received_at'], origin_id=row['origin_id'])
            return process([message], config, source)
        finally:
            self.run_lock.release()

    def edit_categories(self, source, identifier, categories):
        if source not in ('demo', 'gmail', 'pdf') or not isinstance(categories, list) or not categories:
            raise ValueError('Chọn ít nhất một nhóm hợp lệ.')
        allowed = {rule['category'] for rule in self.config()['rules']} | {'Cần xem lại'}
        if self.config().get('unmatched_category'):
            allowed.add(self.config()['unmatched_category'])
        if any(not isinstance(item, str) or item not in allowed for item in categories):
            raise ValueError('Nhóm không tồn tại trong cấu hình.')
        with self.run_lock:
            database = self.root / source / 'notes.sqlite3'
            if not database.exists():
                raise ValueError('Không tìm thấy ghi chép.')
            with sqlite3.connect(database) as connection:
                ensure_schema(connection)
                cursor = connection.execute('UPDATE notes SET categories=? WHERE id=?', (json.dumps(list(dict.fromkeys(categories)), ensure_ascii=False), identifier))
                if not cursor.rowcount:
                    raise ValueError('Không tìm thấy ghi chép.')
                connection.commit()
                render_notes(connection, database.parent / 'notebooks', self.config()['timezone'])

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
                config['classification_mode'] = 'rules'
                incoming = read_json(self.base / 'examples/messages.json', [])
            else:
                key = read_json(self.key_path(config['summary']['provider']), {}).get('key')
                config['_api_key'] = key
                if (config['classification_mode'] == 'ai' or config['summary']['mode'] == 'openai') and not self.has_key(config['summary']['provider']):
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
        if source not in ('demo', 'gmail', 'pdf'):
            raise ValueError('Nguồn không hợp lệ.')
        database = self.root / source / 'notes.sqlite3'
        if not database.exists():
            return {'notes': [], 'total': 0, 'categories': [], 'days': []}
        with sqlite3.connect(database) as migration:
            ensure_schema(migration)
        with sqlite3.connect(f'{database.as_uri()}?mode=ro', uri=True) as connection:
            connection.row_factory = sqlite3.Row
            rows = [dict(row) for row in connection.execute('SELECT id,sender,subject,categories,summary,received_at,day,source,origin_id,review_reason,file_hash FROM notes ORDER BY received_at DESC,id')]
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
