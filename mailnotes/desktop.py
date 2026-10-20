"""Click-to-open launcher for Linux and macOS; never exposes the server remotely."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser


def resource_root():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))


def data_directory():
    if os.environ.get('MAILNOTES_DATA_DIR'):
        return Path(os.environ['MAILNOTES_DATA_DIR']).expanduser().resolve()
    if not getattr(sys, 'frozen', False):
        # The source launcher keeps the same data as the existing CLI/web install.
        return resource_root() / '.local'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/SoGhiChep'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'so-ghi-chep'


def command():
    if getattr(sys, 'frozen', False):
        return [sys.executable]
    return [sys.executable, '-m', 'mailnotes.desktop']


def state_path(root):
    return root / 'admin' / 'desktop.json'


def running_instance(root):
    try:
        state = json.loads(state_path(root).read_text())
        port = state['port']
        if type(port) is not int or not 1024 <= port <= 65535:
            return None
        # Do not send local health checks through an HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://127.0.0.1:{port}/health', timeout=1) as response:
            health = json.load(response)
        if health.get('app') == 'mailnotes' and health.get('instance') == state.get('instance') and state.get('instance'):
            return f'http://localhost:{port}'
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


@contextlib.contextmanager
def instance_lock(root):
    directory = root / 'admin'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(directory / 'desktop.lock', os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def notify(message):
    try:
        if sys.platform == 'darwin':
            # Fixed AppleScript: message is an argv value, never injected as code.
            subprocess.run(['/usr/bin/osascript', '-e', 'on run argv\ndisplay alert "Sổ ghi chép" message (item 1 of argv)\nend run', message], timeout=30, capture_output=True)
        elif __import__('shutil').which('zenity'):
            subprocess.run(['zenity', '--error', '--title=Sổ ghi chép', '--text=' + message], timeout=60, capture_output=True)
        else:
            import html
            path = data_directory() / 'startup-error.html'
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_text('<meta charset="utf-8"><title>Sổ ghi chép</title><h1>Chưa mở được ứng dụng</h1><p>' + html.escape(message) + '</p>', encoding='utf-8')
            webbrowser.open(path.as_uri())
    except Exception:
        # Keep the original failure visible for source/terminal use as a fallback.
        if sys.stderr:
            print(message, file=sys.stderr)


def install_linux_menu():
    if sys.platform != 'linux':
        return
    def quote(value):
        return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
    directory = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'applications'
    directory.mkdir(parents=True, exist_ok=True)
    lines = ['[Desktop Entry]', 'Type=Application', 'Name=Sổ ghi chép',
             'Comment=Đọc tài liệu, phân nhóm và ghi chép tự động',
             'Exec=' + ' '.join(quote(part) for part in command()),
             'Path=' + str(resource_root() if not getattr(sys, 'frozen', False) else Path.home()),
             'Icon=accessories-text-editor', 'Terminal=false', 'Categories=Office;']
    (directory / 'so-ghi-chep.desktop').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def serve(root):
    if getattr(sys, 'frozen', False):
        import certifi
        # Ship verified public CA roots; preserve explicit user trust configuration.
        os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    from waitress import create_server
    from .admin import private_json
    from .web import create_app
    try:
        with instance_lock(root):
            instance = secrets.token_urlsafe(24)
            # Bind before starting work. Reuse the previous port for OAuth callbacks.
            try:
                preferred = json.loads(state_path(root).read_text())['port']
            except (OSError, ValueError, KeyError):
                preferred = 8080
            candidates = list(dict.fromkeys([preferred, *range(8080, 8091)]))
            for port in candidates:
                if type(port) is not int or not 1024 <= port <= 65535:
                    continue
                app = create_app(base=resource_root(), data_root=root, public_url=f'http://localhost:{port}')
                app.config['DESKTOP_INSTANCE'] = instance
                try:
                    server = create_server(app, host='127.0.0.1', port=port, threads=4)
                    break
                except OSError as error:
                    import errno
                    if error.errno != errno.EADDRINUSE:
                        raise
            else:
                raise RuntimeError('Không tìm thấy cổng trống từ 8080 đến 8090.')
            admin = app.extensions['admin']
            def shutdown(*args):
                admin.stop.set()
                from waitress import wasyncore
                server.close()
                wasyncore.close_all(map=server._map)
            app.extensions['desktop_shutdown'] = shutdown
            signal.signal(signal.SIGTERM, shutdown)
            signal.signal(signal.SIGINT, shutdown)
            private_json(state_path(root), {'port': port, 'instance': instance, 'pid': os.getpid()})
            admin.start_scheduler()
            try:
                server.run()
            finally:
                admin.stop.set()
                # Let an in-flight document commit before exiting.
                with admin.run_lock:
                    pass
                server.close()
                # Keep port preference; health validation detects stale state safely.
    except BlockingIOError:
        # Another click already owns this data directory; the parent reuses it.
        return


def launch(root):
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    existing = running_instance(root)
    if existing:
        webbrowser.open(existing)
        return existing
    log_path = root / 'admin' / 'desktop.log'
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(log_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(descriptor, 'ab', buffering=0) as log:
        environment = os.environ.copy()
        environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
        child = subprocess.Popen(command() + ['--serve'], cwd=str(root if getattr(sys, 'frozen', False) else resource_root()), env=environment,
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        url = running_instance(root)
        if url:
            webbrowser.open(url)
            return url
        if child.poll() is not None:
            # A concurrent click may be creating the manifest; give it a moment.
            if child.returncode:
                raise RuntimeError('Ứng dụng không khởi động được. Nhật ký ở: ' + str(log_path))
        time.sleep(.2)
    raise RuntimeError('Ứng dụng chưa sẵn sàng sau 35 giây. Nhật ký ở: ' + str(log_path))


def main():
    parser = argparse.ArgumentParser(description='Sổ ghi chép — bấm mở ứng dụng')
    parser.add_argument('--serve', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = data_directory()
    if args.serve:
        serve(root)
        return
    try:
        install_linux_menu()
        launch(root)
    except Exception as error:
        notify(str(error))
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
