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
        chunks = [normalize_document_text(page.extract_text() or '') for page in reader.pages[:100]]
        text = normalize_document_text('\n\n'.join(chunks))
    except Exception:
        return '', 'Không đọc được PDF; kiểm tra file hỏng hoặc mật khẩu.'
    warning = 'PDF vượt 100 trang; chỉ đọc 100 trang đầu.' if pages > 100 else ''
    extracted_text = text[:100000]
    damaged = broken_text_layer(extracted_text)
    if text.strip() and not (ocr and damaged):
        warnings = [warning] if warning else []
        missing = sum(not chunk.strip() for chunk in chunks)
        if missing:
            warnings.append(f'{missing} trang không có lớp chữ; phần scan hoặc trang trắng chưa được đọc.')
        if len(text) > 100000:
            warnings.append('Nội dung vượt 100.000 ký tự; đã giới hạn phần đọc.')
        if damaged:warnings.append('Lớp chữ PDF có dấu hiệu lỗi font hoặc khoảng cách; cần kiểm tra bản gốc.')
        return extracted_text, ' '.join(warnings)
    if not ocr:
        return '', 'PDF không có lớp chữ, có thể là bản scan. Cần xem lại; luồng này không chạy OCR.'
    if not api_key:
        return '', 'OCR qua GreenNode / VNG Cloud cần API key; hãy lưu key trước khi xử lý PDF scan.'
    try:
        deadline = time.monotonic() + 180
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'input.pdf').write_bytes(data)
            subprocess.run(['pdftoppm', '-f', '1', '-l', str(min(pages, 20)), '-scale-to', '1800', '-png', str(root / 'input.pdf'), str(root / 'page')], check=True, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            texts = []
            for image in sorted(root.glob('page-*.png')):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('OCR deadline')
                image_data = base64.b64encode(image.read_bytes()).decode('ascii')
                from .core import request_json
                response = request_json(
                    endpoint,
                    data={
                        'model': model,
                        'temperature': 0,
                        'max_tokens': 4000,
                        'messages': [
                            {'role': 'system', 'content': OCR_INSTRUCTION},
                            {'role': 'user', 'content': [
                                {'type': 'text', 'text': OCR_INSTRUCTION},
                                {'type': 'image_url', 'image_url': {
                                    'url': 'data:image/png;base64,' + image_data
                                }}
                            ]}
                        ]
                    },
                    headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
                if usage_callback:
                    usage_callback(response)
                choices = response.get('choices', [])
                if not choices:
                    raise ValueError('GreenNode / VNG Cloud không trả kết quả OCR.')
                content = choices[0].get('message', {}).get('content')
                if not isinstance(content, str):
                    raise ValueError('GreenNode / VNG Cloud trả kết quả OCR không hợp lệ.')
                texts.append(content.strip())
            text = normalize_document_text('\n\n'.join(texts))
        if len(text.strip()) < 40:
            return '', 'OCR không đọc được đủ nội dung; cần kiểm tra file gốc.'
        return text[:100000], ('Lớp chữ PDF bị lỗi font/khoảng cách nên đã OCR lại qua GreenNode / VNG Cloud; cần đối chiếu bản gốc.' if damaged else 'Nội dung được OCR qua GreenNode / VNG Cloud; cần đối chiếu bản gốc.') + (' Chỉ đọc 20 trang đầu.' if pages > 20 else '')
    except (OSError, subprocess.SubprocessError, TimeoutError, ValueError, HTTPError, URLError):
        if extracted_text.strip():
            return extracted_text, 'Lớp chữ PDF có dấu hiệu lỗi font/khoảng cách và OCR thất bại; cần kiểm tra bản gốc.'
        return '', 'OCR qua GreenNode / VNG Cloud thất bại hoặc quá thời gian; kiểm tra API key, model hỗ trợ hình ảnh và kết nối mạng.'


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
    markdown = save_markdown(config['data_dir'], digest, text)
    return {**metadata, 'subject': filename[:250], 'body': markdown.read_text(encoding='utf-8'), 'review_reason': warning, 'file_hash': digest}
