"""Exercise content-script cancellation in a real DOM with delayed worker replies."""
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright


def main():
    source=Path(__file__).resolve().parents[1]/'chrome-extension/content.js'
    with sync_playwright() as playwright:
        options={'headless':True}
        if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
        browser=playwright.chromium.launch(**options)
        try:
            page=browser.new_page()
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.set_content('''<style>body{font:20px Arial;padding:40px}.zA{padding:20px}.aZo{display:inline-block;padding:30px}.aV3{padding:20px}button{padding:15px}</style>
            <div id="list"><div class="zA" data-legacy-thread-id="session-thread">Office — monthly report PDF</div></div>
            <div id="mail" hidden><div class="aZo" data-attachment-id="session-pdf"><div class="aV3">report.pdf</div><button aria-label="Tải xuống report.pdf">Download</button></div></div>''')
            page.evaluate('''()=>{
             window.messages=[];window.gates={};window.blocked={};window.legacyRuns=0;
             // A Gmail tab can still contain the pre-update content script.
             window.mailnotesPilotInstalled=true;
             window.chrome={runtime:{getManifest:()=>({version:'session-test'}),onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
              messages.push(data);
              if(gates[data.runId+':'+data.type]){blocked[data.runId]=true;await new Promise(resolve=>{gates[data.runId+':'+data.type]=resolve;});}
              if(data.type==='mail-state')return {record:'missing',complete:false,files:[]};
              if(data.type==='download-state')return {downloadId:0,result:{added:1,filename:'report.pdf'}};
              return {};
             }}};
             document.querySelector('.zA').onclick=()=>{document.querySelector('#list').hidden=true;document.querySelector('#mail').hidden=false;location.hash='mail/longmessage00001';};
             window.showList=()=>{document.querySelector('#list').hidden=false;document.querySelector('#mail').hidden=true;location.hash='search';};
             showList();
            }''')
            page.add_script_tag(path=str(source))
            for phase in ('trace','download-state'):
                page.evaluate('''phase=>{
                 messages=[];gates={};blocked={};showList();
                 gates['old:'+phase]=true;gates['new:trace']=true;
                 listener({type:'run-session',runId:'old',limit:1});
                }''',phase)
                page.wait_for_function('blocked.old',timeout=8000)
                page.evaluate('''()=>{
                 listener({type:'stop',runId:'old'});showList();
                 listener({type:'run-session',runId:'new',limit:1});
                }''')
                page.wait_for_function('blocked.new',timeout=2000)
                old_count=page.evaluate("messages.filter(item=>item.runId==='old').length")
                page.evaluate("phase=>gates['old:'+phase]()",phase)
                page.wait_for_timeout(200)
                assert page.evaluate("messages.filter(item=>item.runId==='old').length")==old_count,'A cancelled scan sent another command after its delayed reply'
                # A delayed Stop from the old run must also leave the new run alive.
                page.evaluate("()=>{listener({type:'stop',runId:'old'});gates['new:trace']();delete gates['new:trace'];}")
                page.wait_for_function("messages.some(item=>item.runId==='new'&&item.type==='finish')",timeout=8000)
                assert page.evaluate("messages.some(item=>item.runId==='new'&&item.type==='pdf-record')"),'The new scan did not save its PDF'
                assert not page.evaluate("messages.some(item=>item.runId==='old'&&['pdf-record','finish','failure'].includes(item.type))"),'A stale run affected the new scan'
            assert not errors,errors
        finally:browser.close()
    print('Content session recovery passed: stop/restart during startup and download processing, stale replies and stale Stop are ignored (synthetic Gmail).')


if __name__=='__main__':main()
