from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
    page=browser.new_page();page.set_content('<div role="row" id="mail">Văn phòng · Hồ sơ mẫu.pdf</div>')
    page.evaluate('''() => {
      window.actions=[];window.listener=null;
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){if(data.type==='choose')return {choice:data.candidates[0]};return {};}}};
      document.getElementById('mail').onclick=()=>{
        actions.push('mail');document.body.innerHTML='<button id="preview" aria-label="Preview document.pdf">PDF</button>';
        document.getElementById('preview').onclick=()=>{
          actions.push('preview');document.body.innerHTML='<button aria-label="Preview document.pdf">PDF</button><div id="download" data-tooltip="Download" style="width:120px;height:60px">↓</div>';
          document.getElementById('download').onclick=()=>{actions.push('download');listener({type:'stop'});};
        };
      };
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()));page.evaluate("listener({type:'run'})")
    page.wait_for_function('actions.length===3',timeout=15000)
    assert page.evaluate('actions')==['mail','preview','download']
    print('Browser passed: mail -> PDF preview -> tooltip-only Download, then stop')
    # Gmail attachment tile with filename only on a child and a competing
    # inline download button. The tile has no role=link/button.
    page=browser.new_page()
    page.set_content('''<div class="aQH"><span class="aZo" tabindex="0" aria-label="Preview attachment" style="display:inline-block;padding:30px"><span class="aV3">Quyet-dinh.pdf</span><button aria-label="Download attachment Quyet-dinh.pdf">↓</button></span></div>''')
    page.evaluate('''() => {
      window.actions=[];window.listener=null;window.selections=[];
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
        if(data.type==='choose'){selections.push(data.candidates);return {choice:data.candidates[0]};}return {};
      }}};
      document.querySelector('.aZo').onclick=event=>{
        if(event.target.closest('button')){actions.push('wrong-inline-download');return;}
        actions.push('preview');
        const overlay=document.createElement('div');overlay.style='position:fixed;inset:0;background:white;z-index:9999';
        overlay.innerHTML='<button data-tooltip="Download" style="width:120px;height:60px">↓</button>';
        document.body.append(overlay);
        overlay.querySelector('button').onclick=()=>{actions.push('download');listener({type:'stop'});};
      };
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()));page.evaluate("listener({type:'run'})")
    page.wait_for_function('actions.length>=2',timeout=15000)
    assert page.evaluate('actions')==['preview','download']
    assert page.evaluate('selections[0][0].label')=='Mở PDF đính kèm: Quyet-dinh.pdf'
    print('Browser passed: Gmail attachment tile -> overlay -> Download; inline icon skipped')
    # Reported layout: only the Drive button had a recognized role. The
    # filename's preview wrapper has neither the old class nor an ARIA role.
    page=browser.new_page()
    page.set_content('''<div style="padding:30px"><span id="open-pdf" style="display:inline-block;padding:20px"><span class="aV3">01.Thư ngỏ ChaTask.pdf</span></span><button aria-label="Thêm tệp đính kèm vào Drive 01.Thư ngỏ ChaTask.pdf">Drive</button></div>''')
    page.evaluate('''() => {
      window.actions=[];window.listener=null;window.selections=[];
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
        if(data.type==='choose'){selections.push(data.candidates);return {choice:data.candidates[0]};}return {};
      }}};
      document.querySelector('button').onclick=()=>actions.push('WRONG-DRIVE');
      document.getElementById('open-pdf').onclick=()=>{
        actions.push('preview');document.body.innerHTML='<button data-tooltip="Tải xuống" style="padding:30px">↓</button>';
        document.querySelector('button').onclick=()=>{actions.push('download');listener({type:'stop'});};
      };
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()));page.evaluate("listener({type:'run'})")
    page.wait_for_function('actions.length>=2',timeout=15000)
    assert page.evaluate('actions')==['preview','download']
    assert page.evaluate('selections[0].length')==1
    assert 'Mở PDF đính kèm:' in page.evaluate('selections[0][0].label')
    assert 'Drive' not in page.evaluate('JSON.stringify(selections)')
    print('Browser passed: reported Vietnamese Drive control excluded; filename opens PDF')
    # Some viewer toolbars label a clickable div without role/data-tooltip.
    page=browser.new_page()
    page.set_content('<div aria-label="Tải về" style="width:120px;height:60px">↓</div>')
    page.evaluate('''() => {
      window.actions=[];window.listener=null;
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){if(data.type==='choose')return {choice:data.candidates[0]};return {};}}};
      document.querySelector('div').onclick=()=>{actions.push('download');listener({type:'stop'});};
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()));page.evaluate("listener({type:'run'})")
    page.wait_for_function('actions.length===1',timeout=15000)
    assert page.evaluate('actions')==['download']
    print('Browser passed: aria-label-only viewer download control')
    browser.close()
