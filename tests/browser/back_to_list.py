"""A broken Gmail Back control must not stop the remaining mail batch."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    page = browser.new_page()
    page.set_content('<main id="app"></main>')
    page.evaluate('''() => {
      window.report=[];window.opened=[];window.finished=false;
      window.chrome={runtime:{getManifest(){return {version:'test'};},onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
        if(data.type==='trace')report.push(data.event);
        if(data.type==='progress')window.status=data.text;
        if(data.type==='mail-state')return {complete:false,files:[],record:'missing'};
        if(data.type==='finish')finished=true;
        return {};
      }}};
      window.addEventListener('hashchange',()=>{if(location.hash==='#list')showList();});
      window.showList=()=>{
        document.querySelector('#app').innerHTML=[0,1].map(i=>`<div class="zA" data-legacy-thread-id="mail-${i}" style="width:600px;padding:15px">Thư PDF ${i}</div>`).join('');
        document.querySelectorAll('.zA').forEach((row,i)=>row.onclick=()=>{
          opened.push(i);if(!window.stuckOnSameHash)location.hash='#mail-'+i;
          document.querySelector('#app').innerHTML='<p>Gmail đang mở thư, nút quay lại bị thiếu</p>';
        });
      };
      location.hash='#list';showList();
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()))
    page.evaluate("listener({type:'run',limit:20})")
    page.wait_for_function('finished', timeout=45000)
    assert page.evaluate('opened') == [0, 1], page.evaluate('report')
    assert not any(event['phase'] == 'dung' for event in page.evaluate('report'))
    assert any(event['phase'] == 'quay-lai-danh-sach' for event in page.evaluate('report'))
    page.evaluate('''() => {
      opened=[];report=[];finished=false;window.stuckOnSameHash=true;location.hash='#list';showList();
    }''')
    page.wait_for_timeout(300)
    page.evaluate("listener({type:'run',limit:20})")
    page.wait_for_function('finished', timeout=45000)
    assert page.evaluate('opened') == [0, 1], page.evaluate('report')
    assert any(event['phase'] == 'tai-lai-danh-sach' for event in page.evaluate('report')), page.evaluate('report')
    assert not any(event['phase'] == 'dung' for event in page.evaluate('report'))
    browser.close()
    print('Browser passed: missing Back control and blank search view recover the next mail')
