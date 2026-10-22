"""Check popup UI in Chromium with simulated Chrome APIs; does not scan Gmail."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import threading

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from flask import Flask,send_from_directory
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright,expect

# Keep this shim in the test harness. Production popup.js uses real Chrome APIs.
CHROME_SHIM=r'''
(()=>{
 const local={},session={},listeners=[],commands=[],tabs=[];
 const emit=(area,values,removed=false)=>{const store=area==='local'?local:session,changes={};for(const [key,value] of Object.entries(values)){changes[key]={oldValue:store[key],newValue:removed?undefined:structuredClone(value)};if(removed)delete store[key];else store[key]=structuredClone(value);}for(const listener of listeners)listener(changes,area);};
 const area=name=>({get:async keys=>{const store=name==='local'?local:session;return Object.fromEntries((Array.isArray(keys)?keys:[keys]).filter(k=>k in store).map(k=>[k,structuredClone(store[k])]));},set:async values=>emit(name,values),remove:async key=>emit(name,{[key]:null},true)});
 window.chrome={storage:{local:area('local'),session:area('session'),onChanged:{addListener:fn=>listeners.push(fn)}},tabs:{create:async tab=>{tabs.push(tab);return tab;}},runtime:{getManifest:()=>({version:__VERSION__}),sendMessage:async msg=>{
  commands.push(structuredClone(msg));
  if(msg.type==='save'){if(msg.token!=='pair-for-test')return {error:'Mã ghép nối không đúng.'};emit('local',{base:msg.base,token:msg.token});return {};}
  if(msg.type==='set-filter'){emit('local',{autoFilter:msg.filter});return {filter:msg.filter};}
  if(msg.type==='set-auto'){emit('local',{autoEnabled:msg.enabled});if(msg.enabled){emit('session',{run:{tab:1,automatic:true}});emit('local',{status:'Đang tự kiểm tra Gmail theo phạm vi đã chọn...'});}else if(session.run?.automatic)emit('session',{run:null},true);return {};}
  if(msg.type==='start'){emit('session',{run:{tab:1,automatic:false}});emit('local',{status:'Đang tìm thư có PDF...'});return {};}
  if(msg.type==='stop'){emit('session',{run:null},true);return {};}
  if(msg.type==='upload')return {status:'Đã ghi PDF vào sổ. Kiểm tra tài liệu trong Sổ ghi chép.'};
  return {error:'Yêu cầu kiểm thử chưa được hỗ trợ.'};
 }}};
 window.popupTest={local,session,commands,tabs,emit};
})();
'''


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
 extension=Path(__file__).resolve().parents[1]/'chrome-extension'
 version=json.loads((extension/'manifest.json').read_text())['version']
 app=Flask(__name__)
 @app.get('/<path:name>')
 def asset(name):return send_from_directory(extension,name)
 server=make_server('127.0.0.1',0,app,threaded=True)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 def shot(page,name):
  if args.screenshots:
   args.screenshots.mkdir(parents=True,exist_ok=True)
   page.screenshot(path=str(args.screenshots/(name+'.png')),full_page=True)
 errors=[]
 try:
  with sync_playwright() as p:
   options={'headless':True}
   if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
   browser=p.chromium.launch(**options)
   context=browser.new_context(viewport={'width':440,'height':780},permissions=['clipboard-read','clipboard-write'])
   context.add_init_script(CHROME_SHIM.replace('__VERSION__',json.dumps(version)))
   page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
   try:
    page.goto(f'http://127.0.0.1:{server.server_port}/popup.html')
    page.locator('#connection-panel[open]').wait_for(state='visible')
    assert page.locator('#version').inner_text()=='v'+version
    assert page.locator('#connected-controls').is_hidden()
    assert page.locator('#upload').is_disabled()
    shot(page,'first-connection')
    page.locator('#token').fill('pair-for-test');page.locator('#base').fill('https://example.com');page.locator('#save').click()
    assert page.locator('#connected-controls').is_hidden()
    assert page.evaluate('()=>popupTest.commands.length')==0
    page.locator('#base').fill('http://localhost:8080');page.locator('#save').click()
    page.locator('#connected-controls').wait_for(state='visible')
    assert not page.locator('#connection-panel').evaluate('(node)=>node.open')
    assert page.locator('#start-one').bounding_box()['y']+page.locator('#start-one').bounding_box()['height']<600
    shot(page,'ready')
    page.locator('#filter-panel summary').click()
    page.locator('#period').select_option('range')
    page.locator('#start-date').fill('2026-10-22');page.locator('#end-date').fill('2026-10-01')
    page.locator('#save-filter').click()
    assert 'Lỗi:' in page.locator('#status').inner_text()
    assert page.evaluate("()=>popupTest.commands.filter(x=>x.type==='set-filter').length")==0
    page.locator('#end-date').fill('2026-10-25');page.locator('#save-filter').click()
    page.wait_for_timeout(100)
    assert page.evaluate("()=>popupTest.local.autoFilter.end")=='2026-10-25'
    assert page.evaluate("()=>popupTest.commands.filter(x=>x.type==='set-filter').every(x=>x.runNow===false)")
    page.locator('#filter-panel summary').click()
    page.locator('#auto').check()
    page.locator('#stop').wait_for(state='visible')
    assert page.locator('#start').is_disabled() and page.locator('#start-one').is_disabled()
    shot(page,'running')
    page.locator('#filter-panel summary').click();page.locator('#period').select_option('today');page.locator('#save-filter').click()
    assert page.evaluate('()=>popupTest.session.run.automatic') is True
    assert page.evaluate("()=>popupTest.commands.filter(x=>x.type==='set-filter').every(x=>x.runNow===false)")
    page.locator('#filter-panel summary').click()
    page.locator('#stop').click()
    page.locator('#stop').wait_for(state='hidden')
    assert page.locator('#auto').is_checked()
    assert 'vẫn bật' in page.locator('#status').inner_text()
    page.locator('#auto').uncheck();page.wait_for_timeout(100)
    assert not page.evaluate('()=>popupTest.local.autoEnabled')
    page.locator('#start-one').click();page.locator('#stop').wait_for(state='visible')
    assert page.locator('#start').is_disabled()
    page.locator('#stop').click();page.locator('#stop').wait_for(state='hidden')
    page.evaluate("()=>popupTest.emit('local',{status:'Lỗi: Không thấy nút tải PDF.\\nHãy kiểm tra Gmail.\\nChi tiết file.\\nDòng đầy đủ vẫn phải có trong báo cáo.',failures:[{name:'report.pdf'}],report:[{time:'10:00',phase:'loi',mail:1,detail:'Không thấy nút tải'}]})")
    page.locator('#retry').wait_for(state='visible')
    assert page.locator('#status-card').get_attribute('data-tone')=='error'
    assert 'Dòng đầy đủ' not in page.locator('#status').inner_text()
    page.locator('#show-report').click()
    assert 'Dòng đầy đủ' in page.locator('#full-status').inner_text()
    page.locator('#copy-report').click()
    expect(page.locator('#copy-report')).to_have_text('Đã sao chép báo cáo')
    copied=page.evaluate('()=>navigator.clipboard.readText()')
    assert version in copied and 'pair-for-test' not in copied
    shot(page,'error-report')
    page.locator('#upload-panel summary').click()
    page.locator('#file').set_input_files({'name':'report.pdf','mimeType':'application/pdf','buffer':b'%PDF-test'})
    page.locator('#upload').click();page.wait_for_timeout(100)
    assert page.locator('#upload').is_disabled()
    assert 'Chưa chọn file' in page.locator('#file-name').inner_text()
    page.locator('#open-tool').click()
    assert page.evaluate('()=>popupTest.tabs[0].url')=='http://localhost:8080'
    for width in (440,390,360):
     page.set_viewport_size({'width':width,'height':780})
     assert not page.evaluate('()=>document.documentElement.scrollWidth>innerWidth'),f'Popup overflows at {width}'
    assert not errors,errors
   finally:context.close();browser.close()
 finally:server.shutdown();thread.join(timeout=3);server.server_close()
 print('Extension popup UI: OK (simulated Chrome APIs; Gmail not exercised)')


if __name__=='__main__':main()
