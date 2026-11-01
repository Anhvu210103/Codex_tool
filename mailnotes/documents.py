"""Bounded PDF extraction with optional page-by-page gateway OCR."""
import hashlib
import base64
import io
import os
import subprocess
import tempfile
import time
import re
import unicodedata
from pathlib import Path
from urllib.error import HTTPError, URLError

MAX_PDF_BYTES = 20 * 1024 * 1024


OCR_INSTRUCTION = ('Chuyển hình ảnh thành văn bản, toàn bộ nội dung trong hình ảnh, '
                   'không bỏ sót chi tiết, không thêm ý kiến cá nhân, không tóm tắt, '
                   'không thêm thông tin ngoài hình ảnh.')


def normalize_document_text(value):
    text = unicodedata.normalize('NFC', str(value or ''))
    text = text.replace('\u00a0', ' ').replace('\u200b', '').replace('\ufeff', '')
    text = ''.join(character for character in text if character in '\n\t' or unicodedata.category(character) != 'Cc')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
    output = []
    blank = True
    for line in lines:
        if not line:
            if output and not blank:output.append('')
            blank = True;continue
        blank = False
        if output and output[-1] and output[-1].endswith('-') and line[:1].islower():
            output[-1] = output[-1][:-1] + line
        else:
            output.append(line)
    while output and not output[-1]:output.pop()
    return '\n'.join(output)


def broken_text_layer(text):
    tokens = re.findall(r'[^\W\d_]+', text, flags=re.UNICODE)
    if len(tokens) < 20:return '\ufffd' in text or any(0xE000 <= ord(character) <= 0xF8FF for character in text)
    singles = sum(len(token) == 1 for token in tokens)
    spaced_runs = len(re.findall(r'(?iu)(?:\b[^\W\d_]\s+){2,}[^\W\d_]\b', text))
    return singles / len(tokens) >= .12 or spaced_runs >= 2 or '\ufffd' in text or any(0xE000 <= ord(character) <= 0xF8FF for character in text)


def pdf_text(data, ocr=False, api_key=None, model='deepseek/deepseek-v4.1-flash-thirdparty', usage_callback=None, endpoint=None):
    from pypdf import PdfReader
    if len(data) > MAX_PDF_BYTES:
        return '', 'PDF vượt giới hạn 20 MB; cần xử lý riêng.'
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(''):
            return '', 'PDF có mật khẩu; cần mở khóa trước.'
        pages = len(reader.pages)
        chunks = []
        extraction_errors = []
        for index, page in enumerate(reader.pages[:100]):
            try:
                chunks.append(normalize_document_text(page.extract_text() or ''))
            except Exception:
                chunks.append('')
                extraction_errors.append(index + 1)
    except Exception:
        return '', 'Không đọc được PDF; kiểm tra file hỏng hoặc mật khẩu.'
    if not pages:
        return '', 'PDF không có trang; cần kiểm tra file gốc.'
    warnings = ['PDF vượt 100 trang; chỉ đọc 100 trang đầu.'] if pages > 100 else []
    damaged = {index for index, chunk in enumerate(chunks) if chunk and broken_text_layer(chunk)}
    missing = {index for index, chunk in enumerate(chunks) if not chunk}
    targets = sorted(damaged | missing)
    completed = set()
    failed = []
    truncated = []
    if targets and ocr and api_key:
        deadline = time.monotonic() + 180
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input.pdf').write_bytes(data)
            for index in targets[:20]:
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        failed.extend(page + 1 for page in targets[:20] if page >= index)
                        break
                    prefix = root / f'page-{index + 1}'
                    options = {'creationflags':subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
                    subprocess.run(['pdftoppm', '-f', str(index + 1), '-l', str(index + 1), '-scale-to', '1800', '-png', str(root / 'input.pdf'), str(prefix)], check=True, timeout=min(60, remaining), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                    images = list(root.glob(prefix.name + '-*.png'))
                    if len(images) != 1:
                        raise ValueError('Không tạo được ảnh trang PDF.')
                    image_data = base64.b64encode(images[0].read_bytes()).decode('ascii')
                    images[0].unlink()
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('OCR deadline')
                    from .core import request_json
                    response = request_json(
                        endpoint,
                        data={'model': model, 'temperature': 0, 'max_tokens': 4000,
                              'messages': [
                                  {'role': 'system', 'content': OCR_INSTRUCTION},
                                  {'role': 'user', 'content': [
                                      {'type': 'text', 'text': OCR_INSTRUCTION},
                                      {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + image_data}}
                                  ]}]},
                        headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'},
                        timeout=min(60, remaining))
                    if usage_callback:
                        usage_callback(response)
                    choices = response.get('choices', []) if isinstance(response, dict) else []
                    choice = choices[0] if choices and isinstance(choices[0], dict) else {}
                    message = choice.get('message')
                    content = message.get('content') if isinstance(message, dict) else None
                    if not isinstance(content, str) or not content.strip():
                        raise ValueError('GreenNode / VNG Cloud không trả chữ OCR hợp lệ.')
                    chunks[index] = normalize_document_text(content)
                    completed.add(index)
                    if choice.get('finish_reason') == 'length':
                        truncated.append(index + 1)
                except (OSError, subprocess.SubprocessError, TimeoutError, ValueError, HTTPError, URLError):
                    failed.append(index + 1)
        if completed:
            warnings.append('Nội dung được OCR qua GreenNode / VNG Cloud; cần đối chiếu bản gốc.')
        if len(targets) > 20:
            warnings.append(f'Chỉ OCR tối đa 20 trang mỗi tài liệu; còn {len(targets) - 20} trang cần kiểm tra.')
        if failed:
            warnings.append('OCR qua GreenNode / VNG Cloud thất bại hoặc quá thời gian ở trang ' + ', '.join(map(str, failed)) + '; kiểm tra API key, model hỗ trợ hình ảnh và kết nối mạng.')
        if truncated:
            warnings.append('OCR bị giới hạn đầu ra ở trang ' + ', '.join(map(str, truncated)) + '; nội dung các trang này chưa đầy đủ.')
    elif targets and ocr and not api_key:
        warnings.append('OCR qua GreenNode / VNG Cloud cần API key; hãy lưu key trước khi xử lý PDF scan.')
    remaining_missing = missing - completed
    if remaining_missing:
        warnings.append(f'{len(remaining_missing)} trang không có lớp chữ; phần scan hoặc trang trắng chưa được đọc.')
        if not ocr:
            warnings.append('Luồng này không chạy OCR.')
    if damaged - completed:
        warnings.append('Lớp chữ PDF có dấu hiệu lỗi font hoặc khoảng cách; cần kiểm tra bản gốc.')
    if extraction_errors:
        warnings.append('Lớp chữ không đọc được ở trang ' + ', '.join(map(str, extraction_errors)) + '; cần kiểm tra bản gốc.')
    text = normalize_document_text('\n\n'.join(chunks))
    if len(text) > 100000:
        warnings.append('Nội dung vượt 100.000 ký tự; đã giới hạn phần đọc.')
    return text[:100000], ' '.join(warnings)


def save_pdf(data, root):
    digest = hashlib.sha256(data).hexdigest()
    directory = Path(root) / 'files'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / (digest + '.pdf')
    if not path.exists():
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
    return digest


def pdf_message(data, filename, config, **metadata):
    if len(data) > MAX_PDF_BYTES or not data.startswith(b'%PDF-'):
        raise ValueError('Chọn file PDF hợp lệ, tối đa 20 MB.')
    def record_ocr_response(response):
        from .database import connect
        from .usage import record_usage
        database = Path(config['data_dir']) / 'notes.sqlite3'
        database.parent.mkdir(parents=True, exist_ok=True)
        with connect(database) as connection:
            record_usage(connection, response, config.get('summary', {}).get('provider', 'vngcloud'), config.get('summary', {}).get('model', 'deepseek/deepseek-v4.1-flash-thirdparty'),
                         metadata.get('id'), config.get('summary', {}).get('pricing', {}))

    from .providers import provider
    settings = config.get('summary', {})
    gateway = provider(settings.get('provider', 'vngcloud'))
    text, warning = pdf_text(
        data,
        config.get('pdf_ocr', False) and config.get('summary', {}).get('ai_consent') is True,
        config.get('_api_key') or os.environ.get(gateway['environment']),
        settings.get('model', gateway['model']),
        record_ocr_response, gateway['endpoint'])
    digest = save_pdf(data, config['data_dir'])
    from .archive import save_markdown
    save_markdown(config['data_dir'], digest, text or 'Chưa đọc được chữ từ PDF. Cần kiểm tra file gốc hoặc thử Đọc lại tài liệu.')
    return {**metadata, 'subject': filename[:250], 'body': text, 'review_reason': warning, 'file_hash': digest}
