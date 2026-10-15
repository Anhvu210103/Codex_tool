"""Bounded local PDF extraction. Scan-only documents are never silently summarized."""
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

MAX_PDF_BYTES = 20 * 1024 * 1024


def pdf_text(data, ocr=False):
    from pypdf import PdfReader
    if len(data) > MAX_PDF_BYTES:
        return '', 'PDF vượt giới hạn 20 MB; cần xử lý riêng.'
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted and not reader.decrypt(''):
            return '', 'PDF có mật khẩu; cần mở khóa trước.'
        pages = len(reader.pages)
        text = '\n\n'.join((page.extract_text() or '') for page in reader.pages[:100])
    except Exception:
        return '', 'Không đọc được PDF; kiểm tra file hỏng hoặc mật khẩu.'
    warning = 'PDF vượt 100 trang; chỉ đọc 100 trang đầu.' if pages > 100 else ''
    if len(text.strip()) >= 40:
        return text[:100000], warning or ('Nội dung vượt 100.000 ký tự; đã giới hạn phần đọc.' if len(text) > 100000 else '')
    if not ocr:
        return '', 'PDF có thể là bản scan. Bật OCR hoặc dùng PDF có lớp văn bản.'
    if not shutil.which('pdftoppm') or not shutil.which('tesseract'):
        return '', 'OCR chưa được cài trên máy chủ (cần Poppler, Tesseract và dữ liệu tiếng Việt).'
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
                result = subprocess.run(['tesseract', str(image), 'stdout', '-l', 'vie+eng'], check=True, timeout=min(60, remaining), capture_output=True)
                texts.append(result.stdout.decode('utf-8', errors='replace'))
            text = '\n\n'.join(texts)
        if len(text.strip()) < 40:
            return '', 'OCR không đọc được đủ nội dung; cần kiểm tra file gốc.'
        return text[:100000], 'Nội dung được đọc bằng OCR; cần đối chiếu bản gốc.' + (' Chỉ đọc 20 trang đầu.' if pages > 20 else '')
    except (OSError, subprocess.SubprocessError):
        return '', 'OCR thất bại hoặc quá thời gian; kiểm tra Tesseract với ngôn ngữ vie+eng.'


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
    cloud_pdf = config.get('summary', {}).get('provider') == 'gemini' and (config.get('classification_mode') == 'ai' or config.get('summary', {}).get('mode') == 'openai')
    text, warning = ('', '') if cloud_pdf else pdf_text(data, config.get('pdf_ocr', False))
    digest = save_pdf(data, config['data_dir'])
    return {**metadata, 'subject': filename[:250], 'body': text, 'review_reason': warning, 'file_hash': digest}
