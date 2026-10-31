#!/usr/bin/env python3
"""Linux source updater. Standard library only; never replaces private data."""
import ast
try:
    import fcntl
except ImportError:  # Windows imports this module in the cross-platform test suite.
    fcntl = None
import io
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
URL = 'https://github.com/Anhvu210103/Codex_tool/archive/refs/heads/codex/admin-web.zip'
DIRECTORIES = {'mailnotes', 'chrome-extension', 'examples', 'packaging', 'deploy', 'tests', '.github'}
FILES = {'config.json', 'README.md', 'requirements.txt', 'requirements-web.txt', 'requirements-build.txt',
         'pyproject.toml', 'requirements-browser.txt', 'Mo-So-Ghi-Chep.sh', 'Mo-So-Ghi-Chep.command', 'Mo-AI-Gmail.sh', 'Cap-Nhat-Tool.py', 'Cap-Nhat-So-Ghi-Chep.sh'}


def unpack(data, destination):
    """Accept only application files, never archive paths into user data."""
    result = []
    seen = set()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if len(archive.infolist()) > 5000 or sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError('Bản tải về quá lớn.')
        for info in archive.infolist():
            path = PurePosixPath(info.filename)
            if path.is_absolute() or '..' in path.parts or '\\' in info.filename or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Bản tải về chứa đường dẫn không an toàn.')
            if info.is_dir() or len(path.parts) < 2:
                continue
            relative = Path(*path.parts[1:])
            if '__pycache__' in relative.parts or any(part.startswith('.') for part in relative.parts[1:]) or relative.suffix == '.pyc':
                continue
            if relative.parts[0] not in DIRECTORIES and str(relative) not in FILES:
                continue
            if relative in seen:
                raise ValueError('Tệp bị trùng trong bản cập nhật.')
            seen.add(relative)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            content = archive.read(info)
            if target.suffix == '.py':
                ast.parse(content, filename=str(relative))
            target.write_bytes(content)
            result.append(relative)
    for required in ('mailnotes/web.py', 'mailnotes/desktop.py', 'requirements-web.txt', 'config.json'):
        if Path(required) not in seen:
            raise ValueError('Bản tải về thiếu tệp của tool.')
    return result


def install(root, stage, files, backup):
    changed = []
    try:
        for relative in files:
            target = root / relative
            # Refuse links inside the installation. Do not inspect ancestors
            # above root: macOS maps /var through /private/var, which is a
            # system link and does not let an archive escape this checkout.
            current = root
            candidates = [root]
            for part in relative.parts:
                current = current / part
                candidates.append(current)
            if any(path.is_symlink() for path in candidates):
                raise ValueError('Thư mục mã nguồn chứa liên kết; dừng để bảo vệ dữ liệu.')
            existed = target.exists()
            if existed:
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
            changed.append((relative, existed))
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage / relative, target)
            if target.suffix == '.sh':
                target.chmod(0o755)
        python = root / '.venv/bin/python'
        requirements = Path('requirements-web.txt')
        old = backup / requirements
        if not old.exists() or old.read_bytes() != (stage / requirements).read_bytes():
            subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(root / requirements)], check=True, timeout=300)
        subprocess.run([str(python), '-c', 'import mailnotes.web, mailnotes.desktop'], cwd=root, check=True, timeout=30)
    except BaseException:
        for relative, existed in reversed(changed):
            if existed:
                shutil.copy2(backup / relative, root / relative)
            else:
                (root / relative).unlink(missing_ok=True)
        raise


def local_servers(root):
    found = []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit() or int(directory.name) == os.getpid():
            continue
        try:
            if (directory / 'cwd').resolve() != root:
                continue
            args = (directory / 'cmdline').read_bytes().split(b'\0')
            if b'mailnotes.web' in args:
                raise RuntimeError('Hãy dừng lệnh mailnotes.web bằng Ctrl+C rồi bấm cập nhật lại. Sau này dùng Mo-So-Ghi-Chep.sh.')
            if b'mailnotes.desktop' in args and b'--serve' in args:
                found.append(int(directory.name))
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue
    return found


def main():
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Bản cập nhật một nút hiện dành cho Linux.')
    if not (ROOT / 'mailnotes/web.py').is_file() or not (ROOT / '.venv/bin/python').exists():
        raise RuntimeError('Đặt tệp cập nhật trong thư mục tool đã cài môi trường .venv.')
    updates = ROOT / '.local/updates'
    updates.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (updates / 'update.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Một lượt cập nhật khác đang chạy.') from None
        print('Đang tải bản mới…', flush=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            data = response.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('Bản tải về quá lớn.')
        with tempfile.TemporaryDirectory(dir=updates) as temporary:
            stage = Path(temporary)
            files = unpack(data, stage)
            pids = local_servers(ROOT)
            for pid in pids:
                os.kill(pid, signal.SIGTERM)
            deadline = time.monotonic() + 45
            while any(Path('/proc', str(pid)).exists() for pid in pids):
                if time.monotonic() > deadline:
                    raise RuntimeError('Tool còn đang xử lý. Chưa thay đổi mã; hãy chờ rồi cập nhật lại.')
                time.sleep(0.25)
            backup = Path(tempfile.mkdtemp(prefix='backup-', dir=updates))
            try:
                install(ROOT, stage, files, backup)
            except BaseException:
                subprocess.Popen([str(ROOT / '.venv/bin/python'), '-m', 'mailnotes.desktop'], cwd=ROOT, start_new_session=True)
                raise
        print('Đã cập nhật. Giữ nguyên key, cài đặt và sổ. Bản sao mã cũ: ' + str(backup), flush=True)
        print('Tiện ích Chrome: nếu nạp trực tiếp từ chrome-extension trong thư mục tool, bấm Reload ở chrome://extensions. Nếu nạp từ thư mục khác, cần thay bằng bản trong thư mục tool một lần.', flush=True)
        subprocess.Popen([str(ROOT / '.venv/bin/python'), '-m', 'mailnotes.desktop'], cwd=ROOT, start_new_session=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Cập nhật chưa hoàn tất: ' + str(error), file=sys.stderr, flush=True)
        sys.exit(1)
