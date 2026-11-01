"""Exercise the real admin UI and local APIs, with a deterministic AI response."""
import argparse
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading
from unittest.mock import patch

from playwright.sync_api import sync_playwright, expect
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from werkzeug.serving import make_server, WSGIRequestHandler

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from mailnotes.admin import private_json
from mailnotes.web import create_app


class QuietHandler(WSGIRequestHandler):
    def log_request(self, *args, **kwargs):
        pass


def sample_pdf():
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(b'BT /F1 12 Tf 50 700 Td (Submit monthly budget before 30 November.) Tj ET')
    page[NameObject('/Contents')]=writer._add_object(stream)
    output=io.BytesIO();writer.write(output);return output.getvalue()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='mailnotes-ui-') as directory:
        root=Path(directory)
        app=None
        server=make_server('127.0.0.1',0,lambda environ,start_response:app(environ,start_response),threaded=True,request_handler=QuietHandler)
        origin=f'http://127.0.0.1:{server.server_port}'
        app=create_app(data_root=root/'data',public_url=origin)
        admin=app.extensions['admin'];config=admin.config()
        config['rules']=[{'category':name,'description':'Browser fixture','keywords':[]} for name in ('Kinh tế','Công văn')]
        admin.save_settings(config)
        private_json(admin.key_path('vngcloud'),{'key':'synthetic-ui-key'})
        answer={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'categories':['Kinh tế'],'summary':'Nộp báo cáo ngân sách trước ngày 30/11.','confidence':.99,'needs_review':False,'review_reason':''})}}],
                'usage':{'prompt_tokens':100,'completion_tokens':20,'prompt_cache_hit_tokens':0,'total_tokens':120}}
        errors=[]
        with patch('mailnotes.core.request_json',return_value=answer),patch('mailnotes.folder_inbox.inbox_directory',return_value=root/'inbox'):
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with sync_playwright() as playwright:
                    options={'headless':True}
                    if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                    browser=playwright.chromium.launch(**options)
                    context=browser.new_context(viewport={'width':1366,'height':900},accept_downloads=True)
                    page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                    try:
                        page.goto(origin)
                        page.locator('#password').fill('browser-test-password')
                        page.locator('#auth-submit').click()
                        page.locator('#overview-pdf').wait_for(state='visible')
                        expect(page.locator('#dashboard-total')).to_contain_text('Đã lưu')
                        page.locator('[data-tab="rules"]').click()
                        page.locator('#add-preset-groups').click()
                        expect(page.locator('.rule-card').nth(2)).to_be_visible()
                        page.locator('[data-tab="overview"]').click()
                        page.locator('#overview-pdf').click()
                        page.locator('#pdf-file').set_input_files({'name':'Báo cáo 01.pdf','mimeType':'application/pdf','buffer':sample_pdf()})
                        page.locator('#upload-pdf').click()
                        rows=page.locator('#notes-body tr')
                        expect(rows).to_have_count(1)
                        expect(rows.first).to_contain_text('Nộp báo cáo ngân sách')
                        expect(rows.first.locator('td').nth(5)).to_contain_text('.md')
                        assert '.pdf' not in rows.first.locator('td').nth(5).inner_text()
                        rows.first.get_by_role('button',name='Sửa nhóm',exact=True).click()
                        page.locator('#edit-group-options input[value="Kinh tế"]').uncheck()
                        page.locator('#edit-group-options input[value="Công văn"]').check()
                        page.locator('#edit-groups-form button[type="submit"]').click()
                        expect(page.locator('#edit-groups')).not_to_be_visible()
                        expect(rows.first.locator('td').nth(2)).to_contain_text('Công văn')
                        with page.expect_download() as download:
                            rows.first.get_by_role('link',name='Tải Markdown',exact=True).click()
                        assert download.value.suggested_filename=='Báo cáo 01.md'
                        assert Path(download.value.path()).stat().st_size>0
                        page.locator('#notes-search').fill('no-matching-document-xyz')
                        expect(rows).to_have_count(0)
                        page.locator('#notes-search').fill('')
                        expect(rows).to_have_count(1)
                        page.locator('#text-size').select_option('xlarge')
                        for width,height in ((1366,900),(1024,768),(768,900),(390,844)):
                            page.set_viewport_size({'width':width,'height':height})
                            if args.screenshots:
                                args.screenshots.mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(args.screenshots/f'notebook-{width}.png'),full_page=True)
                            overflowing=page.evaluate('()=>[...document.querySelectorAll(".topbar,.topbar-tools,.page-heading,.pdf-upload,.filters,.sidebar")].filter(node=>node.getBoundingClientRect().right>innerWidth+1).map(node=>({node:node.className,right:node.getBoundingClientRect().right}))')
                            assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1'),f'Page overflows at {width}px: {overflowing}'
                        page.set_viewport_size({'width':1366,'height':900})
                        page.reload()
                        expect(page.locator('#text-size')).to_have_value('xlarge')
                        page.locator('[data-tab="notebook"]').click()
                        expect(rows).to_have_count(1)
                        page.once('dialog',lambda dialog:dialog.accept())
                        rows.first.get_by_role('button',name='Xóa',exact=True).click()
                        expect(rows).to_have_count(0)
                        page.locator('[data-tab="overview"]').click()
                        with admin.lock:
                            admin.folder_state.update(last_finished=datetime.now(timezone.utc).isoformat(),last_added=0,error='1 tệp cần thử lại.',errors=[{'file':'scan.pdf','error':'Lỗi OCR cần kiểm tra.'}])
                        expect(page.locator('#run-state')).to_have_text('Cần kiểm tra',timeout=7000)
                        expect(page.locator('#run-error')).to_contain_text('scan.pdf')
                        page.locator('#logout').click()
                        expect(page.locator('#auth')).to_be_visible()
                        assert not errors,errors
                    finally:
                        context.close();browser.close()
            finally:
                server.shutdown();thread.join(timeout=5);server.server_close()
    print('Admin UI passed: setup, PDF -> AI -> Markdown, edit, download, search, large fonts, responsive layout, delete, logout (AI simulated).')


if __name__=='__main__':main()
