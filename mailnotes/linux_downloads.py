"""Read only a selected completed PDF from the desktop Downloads directory."""
import os
from pathlib import Path
import shlex
import stat
import sys

from .documents import MAX_PDF_BYTES


def download_directory():
    configured = os.environ.get('MAILNOTES_DOWNLOAD_DIR')
    if configured:
        return Path(configured).expanduser().resolve()
    home = Path.home()
    if sys.platform in ('win32', 'darwin'):
        return (home / 'Downloads').resolve()
    config = Path(os.environ.get('XDG_CONFIG_HOME', home / '.config')) / 'user-dirs.dirs'
    try:
        for line in config.read_text(encoding='utf-8').splitlines():
            if not line.startswith('XDG_DOWNLOAD_DIR='):
                continue
            values = shlex.split(line.split('=', 1)[1])
            if len(values) == 1:
                value = values[0].replace('${HOME}', str(home)).replace('$HOME', str(home))
                path = Path(value)
                if '$' not in value and path.is_absolute() and path.resolve() != home.resolve():
                    return path.resolve()
    except (OSError, ValueError):
        pass
    return (home / 'Downloads').resolve()


def read_download(value):
    if sys.platform not in ('linux', 'darwin', 'win32') or not isinstance(value, str) or len(value) > 4096:
        return None
    requested = Path(value)
    if not requested.is_absolute() or requested.suffix.lower() != '.pdf':
        return None
    root = download_directory().resolve()
    try:
        path = requested.resolve(strict=True)
        if not path.is_relative_to(root) or path.suffix.lower() != '.pdf':
            return None
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_PDF_BYTES:
                return None
            data = stream.read(MAX_PDF_BYTES + 1)
        if len(data) > MAX_PDF_BYTES or not data.startswith(b'%PDF-'):
            return None
        return data, path.name
    except (OSError, ValueError):
        return None
