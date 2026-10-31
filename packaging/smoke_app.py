"""Check that the packaged app can start and serve its real web interface."""

import json
import io
import http.cookiejar
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.request
import zipfile

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject


ROOT = Path(__file__).resolve().parent.parent
APP = Path(os.environ['MAILNOTES_SMOKE_APP']) if os.environ.get('MAILNOTES_SMOKE_APP') else (
    ROOT / 'dist' / 'SoGhiChep.app' / 'Contents' / 'MacOS' / 'SoGhiChep'
    if sys.platform == 'darwin' else ROOT / 'dist' / ('SoGhiChep.exe' if sys.platform == 'win32' else 'SoGhiChep'))


def verify_workflow(opener, base, session, data):
    def request(path, payload=None, raw=None, content_type=None, extra_headers=None):
        headers={'X-CSRF-Token':session['csrf']}
        headers.update(extra_headers or {})
        body=raw
        if payload is not None:
            body=json.dumps(payload).encode();content_type='application/json'
        if content_type:headers['Content-Type']=content_type
        with opener.open(urllib.request.Request(base+path,data=body,headers=headers),timeout=15) as response:
            return response.read()
    session.update(json.loads(request('/api/setup',{'password':'packaged-smoke-password'})))
    config=json.loads(request('/api/settings'))
    config['classification_mode']='rules';config['summary']['mode']='extractive'
    config['rules']=[{'category':'Nhóm kiểm thử','description':'Local test','keywords':[],'senders':[]}]
    request('/api/settings',config)
    def upload(text):
        writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
        if text:
            font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
            page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
            stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 50 700 Td ('+text+') Tj ET').encode())
            page[NameObject('/Contents')]=writer._add_object(stream)
        output=io.BytesIO();writer.write(output)
        boundary='mailnotes-smoke-boundary'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="test.pdf"\r\nContent-Type: application/pdf\r\n\r\n'.encode()+output.getvalue()+f'\r\n--{boundary}--\r\n'.encode())
        request('/api/pdf',raw=body,content_type='multipart/form-data; boundary='+boundary)
        return output.getvalue()
    text_pdf=upload('Local Markdown parity test')
    notes=json.loads(request('/api/notes?source=pdf'))['notes']
    if len(notes)!=1 or notes[0]['categories']!=['Nhóm kiểm thử']:
        raise RuntimeError('Packaged PDF classification failed')
    markdown=request('/api/document?source=pdf&format=markdown&id='+notes[0]['id']).decode()
    if 'Local Markdown parity test' not in markdown or not list((data/'pdf/Theo-nhom').rglob('*.md')):
        raise RuntimeError('Packaged Markdown archive missing')
    upload(None)
    if not list((data/'pdf/Can-xem-lai').rglob('*.md')):
        raise RuntimeError('Packaged scan review missing')
    with zipfile.ZipFile(io.BytesIO(request('/api/extension/download'))) as archive:
        manifest=json.loads(archive.read('SoGhiChep-AI-Gmail/manifest.json'))
        if manifest['manifest_version']!=3:
            raise RuntimeError('Packaged extension missing')
    if sys.platform in ('linux', 'darwin', 'win32'):
        downloads=data/'Downloads';downloads.mkdir(exist_ok=True)
        local_pdf=downloads/'browser.pdf';local_pdf.write_bytes(text_pdf)
        token=json.loads(request('/api/extension/pair',{}))['token']
        result=json.loads(request('/extension/import-local',{'path':str(local_pdf)},extra_headers={
            'Origin':'chrome-extension://'+'a'*32,'Authorization':'Bearer '+token}))
        if not result.get('available') or result['categories']!=['Nhóm kiểm thử'] or not list((data/'ai/Theo-nhom').rglob('*.md')):
            raise RuntimeError('Packaged desktop local download import failed')
        print('Packaged desktop PDF download -> AI source -> grouped Markdown passed')
    print('Packaged workflow passed: PDF -> Markdown -> groups, scan review, Chrome extension')


def main():
    if not APP.is_file():
        raise SystemExit(f'Packaged app missing: {APP}')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    with tempfile.TemporaryDirectory(prefix='mailnotes-packaged-smoke-') as directory:
        data = Path(directory)
        environment = os.environ.copy()
        environment['MAILNOTES_DATA_DIR'] = directory
        environment['MAILNOTES_DOWNLOAD_DIR'] = str(data/'Downloads')
        environment.pop('MAILNOTES_ADMIN_PASSWORD', None)
        if sys.platform == 'linux':
            config_dir=data/'config';config_dir.mkdir()
            (config_dir/'user-dirs.dirs').write_text('XDG_DOWNLOAD_DIR="'+str(data/'Downloads')+'"\n')
            environment['XDG_CONFIG_HOME']=str(config_dir)
        with (data / 'app.log').open('wb') as log:
            child = subprocess.Popen([str(APP), '--serve'], env=environment,
                                     stdin=subprocess.DEVNULL, stdout=log, stderr=log)
            base = None
            session = None
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
                        try:
                            verify_workflow(opener, base, session, data)
                        except Exception as error:
                            raise RuntimeError('Packaged functional workflow failed: '+str(error)) from error
                        print(f'Packaged app smoke passed on {sys.platform}')
                        return
                    except (FileNotFoundError, OSError, ValueError, KeyError):
                        time.sleep(.25)
                log.flush()
                detail = (data / 'app.log').read_text(errors='replace')[-4000:]
                raise RuntimeError(f'Packaged app did not become ready (exit={child.poll()}). {detail}')
            except Exception:
                for relative in ('app.log', 'admin/desktop.log', 'admin/errors.log'):
                    path = data / relative
                    if path.is_file():
                        print(f'{relative}: {path.read_text(encoding="utf-8", errors="replace")[-6000:]}', flush=True)
                raise
            finally:
                # The one-file EXE has a bootloader parent and an application
                # child. Terminating only the parent leaves Windows file locks
                # behind, so stop the application through its authenticated API.
                if child.poll() is None and base and session:
                    try:
                        stop = urllib.request.Request(base + '/api/desktop/stop', data=b'{}', headers={
                            'Content-Type': 'application/json', 'X-CSRF-Token': session['csrf']})
                        with opener.open(stop, timeout=5) as response:
                            response.read()
                    except (OSError, ValueError, KeyError):
                        pass
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if sys.platform == 'win32':
                        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                    else:
                        child.terminate()
                    try:
                        child.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=10)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            detail = traceback.format_exc().replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
            print(f'::error title=Packaged app smoke failed::{detail[-12000:]}', flush=True)
        raise
