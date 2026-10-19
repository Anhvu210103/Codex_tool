"""Bounded local PDF extraction. Scan-only documents are never silently summarized."""
import hashlib
import io
import os
from pathlib import Path

MAX_PDF_BYTES = 20 * 1024 * 1024


def pdf_text(data):
    from pypdf import PdfReader
    if len(data) > MAX_PDF_BYTES:
        return '', 'PDF vượt giới hạn 20 MB; cần xử lý riêng.'
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(''):
            return '', 'PDF có mật khẩu; cần mở khóa trước.'
        pages = len(reader.pages)
        chunks = [(page.extract_text() or '') for page in reader.pages[:100]]
        text = '\n\n'.join(chunks)
    except Exception:
        return '', 'Không đọc được PDF; kiểm tra file hỏng hoặc mật khẩu.'
    warning = 'PDF vượt 100 trang; chỉ đọc 100 trang đầu.' if pages > 100 else ''
    if text.strip():
        warnings = [warning] if warning else []
        missing = sum(not chunk.strip() for chunk in chunks)
        if missing:
            warnings.append(f'{missing} trang không có lớp chữ; phần scan hoặc trang trắng chưa được đọc.')
        if len(text) > 100000:
            warnings.append('Nội dung vượt 100.000 ký tự; đã giới hạn phần đọc.')
        return text[:100000], ' '.join(warnings)
    return '', 'PDF scan không có lớp chữ. DeepSeek API chỉ nhận văn bản nên không thể OCR ảnh PDF; hãy dùng bản PDF đã OCR hoặc có lớp chữ để tool tự phân loại và tóm tắt.'


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
    text, warning = pdf_text(data)
    digest = save_pdf(data, config['data_dir'])
    from .archive import save_markdown
    markdown = save_markdown(config['data_dir'], digest, text)
    return {**metadata, 'subject': filename[:250], 'body': markdown.read_text(encoding='utf-8'), 'review_reason': warning, 'file_hash': digest}
