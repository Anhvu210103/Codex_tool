"""Check that the packaged app can start and serve its real web interface."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request


ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / 'dist' / 'SoGhiChep.app' / 'Contents' / 'MacOS' / 'SoGhiChep'
       if sys.platform == 'darwin' else ROOT / 'dist' / 'SoGhiChep')


def main():
    if not APP.is_file():
        raise SystemExit(f'Packaged app missing: {APP}')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with tempfile.TemporaryDirectory(prefix='mailnotes-packaged-smoke-') as directory:
        data = Path(directory)
        environment = os.environ.copy()
        environment['MAILNOTES_DATA_DIR'] = directory
        with (data / 'app.log').open('wb') as log:
            child = subprocess.Popen([str(APP), '--serve'], env=environment,
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline:
                    if child.poll() is not None:
                        break
                    try:
                        state = json.loads((data / 'admin' / 'desktop.json').read_text())
                        base = f"http://127.0.0.1:{state['port']}"
                        with opener.open(base + '/health', timeout=2) as response:
                            health = json.load(response)
                        if health.get('app') != 'mailnotes' or health.get('instance') != state['instance']:
                            raise RuntimeError('Health endpoint returned another app instance')
                        with opener.open(base + '/', timeout=2) as response:
                            page = response.read().decode('utf-8')
                        if 'Sổ ghi chép' not in page:
                            raise RuntimeError('Packaged app did not serve its web interface')
                        with opener.open(base + '/api/session', timeout=2) as response:
                            session = json.load(response)
                        if not session.get('csrf'):
                            raise RuntimeError('Packaged app did not initialize the session API')
                        print(f'Packaged app smoke passed on {sys.platform}')
                        return
                    except (FileNotFoundError, OSError, ValueError, KeyError):
                        time.sleep(.25)
                log.flush()
                detail = (data / 'app.log').read_text(errors='replace')[-4000:]
                raise RuntimeError(f'Packaged app did not become ready (exit={child.poll()}). {detail}')
            finally:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()


if __name__ == '__main__':
    main()
