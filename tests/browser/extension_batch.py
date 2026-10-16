"""Exercise the entire content-script batch loop in a real browser with Gmail-like DOM."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    page = browser.new_page()
    page.set_content('<main id="app"></main>')
    page.evaluate('''() => {
      window.events=[];window.finished=false;window.status='';window.listener=null;window.pending={};
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
        if(data.type==='progress'){window.status=data.text;return {};}
        if(data.type==='arm-download'){window.pending={};return {};}
        if(data.type==='download-state')return window.pending;
        if(data.type==='finish'){window.finished=true;return {};}
        return {};
      }}};
      window.showList=()=>{
        document.getElementById('app').innerHTML=Array.from({length:20},(_,i)=>
          `<div class="zA" data-legacy-thread-id="mail-${i}" style="padding:14px;width:600px">Công văn số ${i+1} · PDF đính kèm</div>`).join('');
        document.querySelectorAll('.zA').forEach((row,i)=>row.onclick=()=>showMail(i));
      };
      window.showMail=i=>{
        events.push('open-mail-'+i);
        const names=i===0?['One.pdf','Two.pdf']:[`Mail-${i}.pdf`];
        document.getElementById('app').innerHTML='<button aria-label="Quay lại" style="padding:15px">Trở về</button>'+
          names.map((name,j)=>`<span class="aV3" data-index="${j}" style="display:inline-block;padding:20px">${name}</span>`).join('');
        document.querySelector('button').onclick=showList;
        document.querySelectorAll('.aV3').forEach((tile,j)=>tile.onclick=()=>showViewer(names[j]));
      };
      window.showViewer=name=>{
        events.push('open-pdf-'+name);
        const viewer=document.createElement('div');viewer.id='viewer';
        viewer.style='position:fixed;inset:0;background:white;z-index:100';
        viewer.innerHTML='<div aria-label="Đang hiển thị người xem." style="padding:20px">PDF</div><button aria-label="Đóng" style="padding:15px">Đóng</button>'+
          (name==='Two.pdf'?'<button style="position:fixed;right:95px;top:9px;width:40px;height:40px"><svg width="20" height="20"></svg></button><button id="download" style="position:fixed;right:45px;top:9px;width:40px;height:40px">↓</button><button aria-label="Tùy chọn khác" style="position:fixed;right:0;top:9px;width:38px;height:40px">⋮</button>':'<button id="download" aria-label="Tải xuống" style="padding:15px">↓</button>');
        document.body.append(viewer);
        viewer.querySelector('[aria-label="Đóng"]').onclick=()=>viewer.remove();
        viewer.querySelector('#download').onclick=()=>{
          events.push('download-'+name);pending={result:{filename:name,added:1}};
        };
      };
      showList();
    }''')
    page.add_script_tag(path=str(Path('chrome-extension/content.js').resolve()))
    page.evaluate("listener({type:'run',limit:20})")
    page.wait_for_function('finished', timeout=90000)
    events=page.evaluate('events')
    assert sum(item.startswith('open-mail-') for item in events)==20, events
    assert sum(item.startswith('download-') for item in events)==21, events
    assert events.index('download-One.pdf')<events.index('open-pdf-Two.pdf')
    assert page.evaluate('status').startswith('Hoàn tất: 20 thư, 21 PDF đã lưu, 0 lỗi.'), page.evaluate('status')
    print('Browser passed: 20 mails, 21 PDFs including two in one mail, each download acknowledged before next')
    browser.close()
