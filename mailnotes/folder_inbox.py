"""Safely read completed PDFs from a user-facing inbox folder."""
import hashlib
import os
import stat
import time
from pathlib import Path

from .documents import MAX_PDF_BYTES


def inbox_directory():
    configured = os.environ.get('MAILNOTES_INBOX_DIR')
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / 'Downloads' / 'So-Ghi-Chep-Inbox').resolve()


def iter_ready_pdfs(root=None, minimum_age=3, now=None, errors=None):
    root = Path(root or inbox_directory()).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = time.time() if now is None else now
    errors = [] if errors is None else errors
    for path in sorted(root.glob('*'), key=lambda item: item.name.casefold()):
        if path.suffix.lower() != '.pdf' or path.is_symlink():
            continue
        try:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_size == 0 or current - before.st_mtime < minimum_age:
                continue
            if before.st_size > MAX_PDF_BYTES:
                errors.append({'file':path.name, 'error':'PDF vượt 20 MB; cần chia nhỏ trước khi quét lại.'})
                continue
            flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
            descriptor = os.open(path, flags)
            with os.fdopen(descriptor, 'rb') as stream:
                opened = os.fstat(stream.fileno())
                if opened.st_ino != before.st_ino or opened.st_size != before.st_size or not stat.S_ISREG(opened.st_mode):
                    continue
                data = stream.read(MAX_PDF_BYTES + 1)
            after = path.stat()
            if after.st_ino != before.st_ino or after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns:
                continue
            if len(data) > MAX_PDF_BYTES or not data.startswith(b'%PDF-'):
                errors.append({'file':path.name, 'error':'Tệp có đuôi PDF nhưng nội dung không phải PDF hợp lệ.'})
                continue
            yield path, data, hashlib.sha256(data).hexdigest()
        except OSError:
            errors.append({'file':path.name, 'error':'Chưa đọc được tệp; sẽ thử lại ở lượt sau.'})


def ready_pdfs(root=None, minimum_age=3, now=None):
    # Compatibility for callers that need a snapshot. The importer streams PDFs.
    errors = []
    return list(iter_ready_pdfs(root, minimum_age, now, errors)), errors


def archive_processed(path, digest, root=None):
    root = Path(root or inbox_directory()).resolve()
    path = Path(path)
    if path.parent.resolve() != root or path.is_symlink():
        raise ValueError('PDF không còn nằm trực tiếp trong thư mục nhận.')
    path = path.resolve(strict=True)
    flags = os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, 'rb') as stream:
        current = stream.read(MAX_PDF_BYTES + 1)
    if len(current) > MAX_PDF_BYTES or hashlib.sha256(current).hexdigest() != digest:
        raise ValueError('PDF đã thay đổi trong lúc xử lý; sẽ đọc lại ở lượt sau.')
    destination = root / 'Da-xu-ly'
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = destination / f'{digest[:12]}-{path.name}'
    counter = 1
    while target.exists():
        target = destination / f'{digest[:12]}-{counter}-{path.name}'
        counter += 1
    path.replace(target)
    return target
