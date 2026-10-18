"""Safely read completed PDFs from a user-facing inbox folder."""
import hashlib
import os
import stat
import time
from pathlib import Path

from .documents import MAX_PDF_BYTES


def inbox_directory():
    return (Path.home() / 'Downloads' / 'So-Ghi-Chep-Inbox').resolve()


def ready_pdfs(root=None, minimum_age=3, now=None):
    root = Path(root or inbox_directory()).resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    current = time.time() if now is None else now
    ready, errors = [], []
    for path in sorted(root.glob('*'), key=lambda item: item.name.casefold()):
        if path.suffix.lower() != '.pdf' or path.is_symlink():
            continue
        try:
            before = path.stat()
            if not stat.S_ISREG(before.st_mode) or before.st_size == 0 or before.st_size > MAX_PDF_BYTES or current - before.st_mtime < minimum_age:
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
            ready.append((path, data, hashlib.sha256(data).hexdigest()))
        except OSError:
            errors.append({'file':path.name, 'error':'Chưa đọc được tệp; sẽ thử lại ở lượt sau.'})
    return ready, errors


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
