"""Exercise the customer workflow in a real browser with a fake DeepSeek service.

Run with requirements-web.txt and Playwright installed. No customer keys or data.
Optional: python packaging/smoke_customer_ui.py --screenshots /tmp/customer-ui
"""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from mailnotes.web import create_app


def pdf(text):
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 50 700 Td ('+text+') Tj ET').encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    result=io.BytesIO();writer.write(result);return result.getvalue()


def fake_ai(url, **kwargs):
    assert url == 'https://api.deepseek.com/chat/completions'
    result={'categories':['Kinh tế'],'summary':'Hoàn thành báo cáo kinh tế trước ngày 25/10 và gửi số liệu về văn phòng để rà soát.','confidence':.95,'needs_review':False,'review_reason':''}
    return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}],
            'usage':{'prompt_tokens':250,'completion_tokens':60,'total_tokens':310}}


def exercise(root, url, screenshots):
    errors=[];http_errors=[]
    def screenshot(page, name):
        if screenshots:
            screenshots.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(screenshots/(name+'.png')),full_page=True)
    with sync_playwright() as playwright:
        options={'headless':True}
        if shutil.which('chromium'):
            options['executable_path']=shutil.which('chromium')
        browser=playwright.chromium.launch(**options)
        try:
            page=browser.new_page(viewport={'width':1440,'height':1000})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('response',lambda response:http_errors.append((response.status,response.url)) if response.status>=400 else None)
            page.goto(url)
            page.locator('#auth').wait_for(state='visible')
            page.locator('#show-password').check()
            assert page.locator('#password').get_attribute('type')=='text'
            page.locator('#password').fill('customer-smoke-password')
            page.locator('#auth-submit').click()
            page.locator('#setup-required').wait_for(state='visible')
            assert page.locator('#dashboard-source').input_value()=='all'
            page.locator('#setup-ai').click()
            page.locator('#ai-key').fill('test-only-key-not-real')
            page.locator('#ai-consent').check()
            page.locator('#save-key').click()
            page.locator('#setup-required').wait_for(state='hidden')
            page.locator('[data-tab=overview]').click()
            page.locator('#overview-pdf').click()
            page.locator('#pdf-file').set_input_files(str(root/'upload.pdf'))
            page.locator('#upload-pdf').click()
            page.locator('#notes-body tr').first.wait_for(state='visible')
            assert not page.locator('#pdf-upload-panel').evaluate('(e)=>e.open')
            page.locator('.note-details summary').first.click()
            # The four-second poll must preserve an expanded document and focus.
            page.wait_for_timeout(4300)
            assert page.locator('.note-details').first.evaluate('(e)=>e.open')
            page.locator('[data-tab=overview]').click()
            page.locator('#overview-folder').click()
            page.locator('#folder-help').wait_for(state='visible')
            page.locator('#close-folder-help').click()
            page.locator('#overview-scan').click()
            page.locator('#folder-results').wait_for(state='visible')
            page.locator('#folder-results').click()
            page.locator('#notes-body tr').first.wait_for(state='visible')
            page.locator('#clear-note-filters').click()
            page.locator('#notes-body tr').nth(1).wait_for(state='visible')
            assert page.locator('#notes-source').input_value()=='all'
            page.locator('#notes-body').get_by_role('button',name='Sửa nhóm',exact=True).first.click()
            page.locator('#edit-group-options input').nth(1).check()
            page.locator('#edit-groups-form button[type=submit]').click()
            page.locator('#edit-groups').wait_for(state='hidden')
            page.locator('#notes-search').fill('upload.pdf')
            page.wait_for_timeout(500)
            assert page.locator('#notes-body tr').count()==1
            page.locator('#clear-note-filters').click()
            page.locator('#notes-body tr').nth(1).wait_for(state='visible')
            page.locator('#notes-day').select_option(index=1)
            page.locator('#export').wait_for(state='visible')
            page.wait_for_timeout(300)
            assert page.locator('#export').is_enabled()
            with page.expect_download() as download:
                page.locator('#export').click()
            assert download.value.failure() is None
            page.locator('#clear-note-filters').click()
            for width in (1920,1440,1366,1024,390):
                page.set_viewport_size({'width':width,'height':1000})
                page.evaluate('()=>window.scrollTo(0,0)')
                assert not page.evaluate('()=>document.documentElement.scrollWidth>innerWidth'),f'Page overflow at {width}'
                screenshot(page,'notebook-'+str(width))
            page.set_viewport_size({'width':1440,'height':1000})
            page.locator('[data-tab=overview]').click();screenshot(page,'overview')
            page.locator('[data-tab=settings]').click();screenshot(page,'settings')
            assert not errors,errors
            assert not http_errors,http_errors
        finally:
            browser.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='mailnotes-ui-') as directory:
        root=Path(directory);inbox=root/'inbox';inbox.mkdir()
        (root/'upload.pdf').write_bytes(pdf('Economics report due October 25.'))
        item=inbox/'folder.pdf';item.write_bytes(pdf('Economics statistics submitted by the local office.'));os.utime(item,(1,1))
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        url=f'http://localhost:{port}'
        environment={'MAILNOTES_DOCKER_LOCAL_SETUP':'1','MAILNOTES_INBOX_DIR':str(inbox),
                     'MAILNOTES_INBOX_DISPLAY_PATH':'/Users/Customer/Documents/SoGhiChep/inbox',
                     'MAILNOTES_DATA_DISPLAY_PATH':'/Users/Customer/Documents/SoGhiChep/.local'}
        with patch.dict(os.environ,environment),patch('mailnotes.core.request_json',side_effect=fake_ai):
            app=create_app(data_root=root/'data',public_url=url)
            admin=app.extensions['admin'];config=admin.config()
            config['rules']=[{'category':group,'description':group,'keywords':[],'senders':[]} for group in ('Kinh tế','Hành chính')]
            admin.save_settings(config)
            original_wsgi=app.wsgi_app
            def docker_remote(environ,start_response):
                environ['REMOTE_ADDR']='172.17.0.1'
                return original_wsgi(environ,start_response)
            app.wsgi_app=docker_remote
            server=make_server('127.0.0.1',port,app,threaded=True)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                exercise(root,url,args.screenshots)
            finally:
                with admin.run_lock:pass
                server.shutdown();thread.join(timeout=3);server.server_close()
    print('Customer browser workflow: OK (fake AI, temporary data)')


if __name__=='__main__':main()
