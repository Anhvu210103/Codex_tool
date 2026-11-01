"""Run an unpacked extension in Chromium against a synthetic Gmail page.

Uses real Chrome debugger/download/storage APIs and real local Flask endpoints.
Requires a Chromium installation that permits unpacked extensions. No Gmail
account, external provider request, or document from a customer is used.
"""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import traceback
from unittest.mock import patch

from playwright.sync_api import sync_playwright
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from werkzeug.serving import make_server, WSGIRequestHandler

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from mailnotes.admin import private_json
from mailnotes.web import create_app


PAGE='''<!doctype html><meta charset="utf-8"><title>Synthetic Gmail test</title>
<style>body{font:20px Arial;padding:60px}.zA{padding:20px;border:1px solid #777;cursor:pointer}.aZo{display:inline-flex;flex-direction:column;width:220px;margin:24px;padding:16px;border:1px solid #777}.aV3{height:90px}a[role=button]{display:block;width:50px;height:50px;padding:8px;background:#ddd}svg{width:30px;height:30px}</style>
<div id="list"><div class="zA" data-legacy-thread-id="native-thread" data-legacy-message-id="native-message">Office — two PDF attachments for native test</div></div>
<div id="mail" hidden><button id="back" aria-label="Quay lại danh sách">Back</button>
<div class="aZo" data-attachment-id="one"><div class="aV3">native-one.pdf</div><a role="button" data-fixture="one" aria-label="Tải xuống tệp đính kèm native-one.pdf" href="#" download="native-one.pdf"><svg><path d="M15 0v25m-10-10 10 10 10-10" stroke="black" fill="none"/></svg></a></div>
<div class="aZo" data-attachment-id="two"><div class="aV3">native-two.pdf</div><a role="button" data-fixture="two" aria-label="Tải xuống tệp đính kèm native-two.pdf" href="#" download="native-two.pdf"><svg><path d="M15 0v25m-10-10 10 10 10-10" stroke="black" fill="none"/></svg></a></div></div>
<script>const documents=__DOCUMENTS__;for(const link of document.querySelectorAll('[data-fixture]')){const bytes=Uint8Array.from(atob(documents[link.dataset.fixture]),character=>character.charCodeAt(0));link.href=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'}));}document.querySelector('.zA').onclick=()=>{document.querySelector('#list').hidden=true;document.querySelector('#mail').hidden=false;location.hash='search/native/message0000000001';};document.querySelector('#back').onclick=()=>{document.querySelector('#list').hidden=false;document.querySelector('#mail').hidden=true;location.hash='search/native';};</script>'''


class QuietHandler(WSGIRequestHandler):
    def log_request(self,*args,**kwargs):pass


def pdf(name):
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(f'BT /F1 12 Tf 50 700 Td (Native document {name}, submit before 30 November.) Tj ET'.encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--chromium',type=Path);args=parser.parse_args()
    extension=Path(__file__).resolve().parents[1]/'chrome-extension'
    with tempfile.TemporaryDirectory(prefix='mailnotes-native-') as directory:
        root=Path(directory);downloads=root/'Downloads';downloads.mkdir()
        app=None
        server=make_server('127.0.0.1',0,lambda environ,start_response:app(environ,start_response),threaded=True,request_handler=QuietHandler)
        origin=f'http://127.0.0.1:{server.server_port}'
        app=create_app(data_root=root/'data',public_url=origin);admin=app.extensions['admin']
        config=admin.config();config.update(classification_mode='rules',rules=[{'category':'Native test','keywords':[]}]);config['summary']['mode']='extractive';admin.save_settings(config)
        token='native-test-pair';private_json(admin.private/'extension-token.json',{'hash':hashlib.sha256(token.encode()).hexdigest()})
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('mailnotes.linux_downloads.download_directory',return_value=downloads),patch('mailnotes.core.request_json',side_effect=AssertionError('Native extension test must not call AI')),sync_playwright() as playwright:
                binary=args.chromium or Path(playwright.chromium.executable_path)
                if not binary.is_file():
                    raise RuntimeError('Install Playwright Chromium or pass --chromium with a browser that permits unpacked extensions.')
                context=playwright.chromium.launch_persistent_context(root/'chrome-profile',headless=True,executable_path=str(binary),ignore_default_args=['--disable-extensions'],accept_downloads=True,args=[f'--disable-extensions-except={extension}',f'--load-extension={extension}'])
                try:
                    worker=context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker',timeout=15000)
                    assert worker.url.endswith('/worker.js'),worker.url
                    keeper=context.pages[0] if context.pages else context.new_page()
                    worker.evaluate('(config)=>chrome.storage.local.set(config)',{'base':origin,'token':token,'capabilities':['local-download-pdf']})
                    requests=[]
                    def route(request):
                        requests.append(request.request.url)
                        payload={name:base64.b64encode(pdf(name)).decode('ascii') for name in ('one','two')}
                        request.fulfill(status=200,content_type='text/html',body=PAGE.replace('__DOCUMENTS__',json.dumps(payload)))
                    context.route('https://mail.google.com/**',route)
                    page=context.new_page();page.goto('https://mail.google.com/mail/u/0/#search/native');page.bring_to_front()
                    assert page.locator('a[download]').evaluate_all("links=>links.every(link=>link.href.startsWith('blob:https://mail.google.com/'))")
                    cdp=context.new_cdp_session(page)
                    cdp.send('Browser.setDownloadBehavior',{'behavior':'allow','downloadPath':str(downloads),'eventsEnabled':True})
                    tab=worker.evaluate("async()=>{const tabs=await chrome.tabs.query({url:'https://mail.google.com/*'});return tabs[0].id;}")
                    def wait_done(timeout=25):
                        deadline=time.monotonic()+timeout
                        while time.monotonic()<deadline:
                            saved=worker.evaluate("async()=>({run:(await chrome.storage.session.get('run')).run,local:await chrome.storage.local.get(['status','report'])})")
                            if not saved.get('run'):return saved['local']
                            page.wait_for_timeout(100)
                        diagnostics={'state':saved,'page_url':page.url,'requests':requests,'files':[path.name for path in downloads.iterdir()],
                                     'chrome_downloads':worker.evaluate('()=>chrome.downloads.search({})'),
                                     'targets':worker.evaluate('()=>chrome.debugger.getTargets()')}
                        raise RuntimeError('Native extension did not finish: '+json.dumps(diagnostics,ensure_ascii=False))
                    worker.evaluate('(tab)=>beginRun({id:tab},1)',tab)
                    result=wait_done()
                    assert admin.notes('ai')['total']==2,result
                    assert sorted(path.name for path in downloads.glob('*.pdf'))==['native-one.pdf','native-two.pdf'],result
                    assert len(list((admin.root/'ai/Theo-nhom').rglob('*.md')))==2
                    assert not any(event['phase'] in ('loi','dung') for event in result.get('report',[])),result
                    page.locator('#back').click()
                    worker.evaluate('(tab)=>beginRun({id:tab},1)',tab)
                    duplicate=wait_done()
                    assert admin.notes('ai')['total']==2,duplicate
                    assert len(list(downloads.glob('*.pdf')))==2,'A duplicate run downloaded the same attachments again'
                    detached=worker.evaluate("async tab=>{try{await chrome.debugger.sendCommand({tabId:tab},'Runtime.evaluate',{expression:'1'});return false;}catch{return true;}}",tab)
                    assert detached,'The extension still owns the debugger after finishing'
                    worker.evaluate('(tab)=>beginRun({id:tab},1)',tab)
                    page.close()
                    deadline=time.monotonic()+5
                    while time.monotonic()<deadline and worker.evaluate("async()=>!!(await chrome.storage.session.get('run')).run"):
                        keeper.wait_for_timeout(100)
                    assert not worker.evaluate("async()=>!!(await chrome.storage.session.get('run')).run"),'Closing the tab did not release scan state'
                finally:context.close()
        finally:server.shutdown();thread.join(timeout=5);server.server_close()
    print('Native Chrome extension passed: debugger clicks, two PDF downloads -> local import -> Markdown, duplicate skip, detach and tab-close recovery (synthetic Gmail, no AI request).')


if __name__=='__main__':
    try:main()
    except Exception:
        if os.environ.get('GITHUB_ACTIONS')=='true':
            detail=traceback.format_exc().replace('%','%25').replace('\r','%0D').replace('\n','%0A')
            print(f'::error title=Native extension test failed::{detail[-12000:]}',flush=True)
        raise
