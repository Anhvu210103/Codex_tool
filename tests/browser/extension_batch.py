"""Exercise the entire content-script batch loop in a real browser with Gmail-like DOM."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True)
    page = browser.new_page()
    page.set_content('<main id="app"></main>')
    page.evaluate('''() => {
      window.events=[];window.report=[];window.failures=[];window.finished=false;window.status='';window.listener=null;window.pending={};
      window.chrome={runtime:{onMessage:{addListener(fn){window.listener=fn;}},async sendMessage(data){
        if(data.type==='progress'){window.status=data.text;return {};}
        if(data.type==='trace'){window.report.push(data.event);return {};}
        if(data.type==='failure'){window.failures.push(data.failure);return {};}
        if(data.type==='arm-download'){window.pending={};return {};}
        if(data.type==='trusted-click'){
          let target=document.elementFromPoint(data.x,data.y);
          while(target && !target.onclick)target=target.parentElement;
          if(window.suppressClick===window.openPdfName && target?.id==='download'){
            events.push('missed-download-'+window.openPdfName);return {};
          }
          if(target){const handler=target.onclick;target.onclick=null;target.dispatchEvent(new MouseEvent('click',{bubbles:true}));target.onclick=handler;handler({isTrusted:true});}
          return {};
        }
        if(data.type==='trusted-escape'){
          events.push('escape-'+(window.openPdfName||''));document.querySelector('#viewer')?.remove();return {};
        }
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
          names.map((name,j)=>i===0&&j===0?`<div class="aZo" style="display:inline-block;position:relative"><span class="aV3" data-index="${j}" style="display:inline-block;padding:20px">${name}</span><button id="drive-cover" style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:48px;height:32px">Drive</button></div>`:`<span class="aV3" data-index="${j}" style="display:inline-block;padding:20px">${name}</span>`).join('');
        document.querySelector('button').onclick=event=>{if(event.isTrusted)showList();};
        document.querySelectorAll('.aV3').forEach((tile,j)=>tile.onclick=()=>showViewer(names[j]));
        document.querySelector('#drive-cover')?.addEventListener('click',event=>{event.stopPropagation();events.push('wrong-drive');});
      };
      window.showViewer=name=>{
        events.push('open-pdf-'+name);window.openPdfName=name;
        const viewer=document.createElement('div');viewer.id='viewer';
        viewer.style='position:fixed;inset:0;background:white;z-index:100';
        viewer.innerHTML='<div aria-label="Đang hiển thị người xem." style="padding:20px">PDF</div><button aria-label="Đóng" style="padding:15px">Đóng</button>'+
          (name==='Two.pdf'?'<button style="position:fixed;right:95px;top:9px;width:40px;height:40px"><svg width="20" height="20"></svg></button><button id="download" style="position:fixed;right:45px;top:9px;width:40px;height:40px">↓</button><button aria-label="Tùy chọn khác" style="position:fixed;right:0;top:9px;width:38px;height:40px">⋮</button>':'<button id="download" aria-label="Tải xuống" style="padding:15px">↓</button>');
        document.body.append(viewer);
        viewer.querySelector('[aria-label="Đóng"]').onclick=event=>{
          if(event.isTrusted && window.blockClose!==name)viewer.remove();
        };
        viewer.querySelector('#download').onclick=()=>{
          if(window.suppressDownload===name){events.push('ignored-download-'+name);return;}
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
    assert 'wrong-drive' not in events
    assert len(page.evaluate('report'))>=20
    assert page.evaluate('status').startswith('Hoàn tất: 20 thư, 21 PDF đã lưu, 0 lỗi.'), page.evaluate('status')
    print('Browser passed: 20 mails, 21 PDFs including a PDF obscured by its own Drive button')
    page.evaluate('''() => {
      events=[];report=[];finished=false;showList();
      window.originalShowMail=showMail;const previous=showMail;
      showMail=i=>{
        previous(i);
        if(i===0){
          const r=document.querySelector('.aV3').getBoundingClientRect();
          const blocker=document.createElement('div');blocker.id='external-blocker';
          blocker.style=`position:fixed;left:${r.left}px;top:${r.top}px;width:${r.width}px;height:${r.height}px;z-index:90;background:#ccc`;
          document.body.append(blocker);
        }
      };
      document.querySelectorAll('.zA').forEach((row,i)=>row.onclick=()=>showMail(i));
      listener({type:'run',limit:1});
    }''')
    page.wait_for_function('finished', timeout=30000)
    assert 'download-One.pdf' not in page.evaluate('events')
    assert 'download-Two.pdf' in page.evaluate('events')
    assert page.evaluate('status').startswith('Hoàn tất: 1 thư, 1 PDF đã lưu, 1 lỗi.'), page.evaluate('status')
    assert any(e['phase']=='loi' and e['file']=='One.pdf' for e in page.evaluate('report'))
    assert len(page.evaluate('failures'))==1
    print('Browser passed: blocked first PDF logged and skipped; second PDF still saved')
    page.evaluate('''() => {
      const retry=[...failures];events=[];report=[];finished=false;
      document.querySelector('#external-blocker')?.remove();
      showMail=originalShowMail;showList();
      listener({type:'run',limit:20,only:retry});
    }''')
    page.wait_for_function('finished', timeout=30000)
    assert 'download-One.pdf' in page.evaluate('events')
    assert 'download-Two.pdf' not in page.evaluate('events')
    assert page.evaluate('status').startswith('Hoàn tất: 1 thư, 1 PDF đã lưu, 0 lỗi.'), page.evaluate('status')
    print('Browser passed: retry processed only the failed PDF')
    page.evaluate('''() => {
      suppressDownload='One.pdf';blockClose='One.pdf';events=[];report=[];finished=false;showList();
      listener({type:'run',limit:1});
    }''')
    page.wait_for_function('finished', timeout=30000)
    assert 'ignored-download-One.pdf' in page.evaluate('events')
    assert 'download-Two.pdf' in page.evaluate('events')
    assert 'escape-One.pdf' in page.evaluate('events')
    assert page.evaluate('status').startswith('Hoàn tất: 1 thư, 1 PDF đã lưu, 1 lỗi.'), page.evaluate('status')
    assert any(e['phase']=='loi' and 'Chrome chưa bắt đầu tải' in e['detail'] for e in page.evaluate('report'))
    print('Browser passed: click without Chrome download and ignored Close fall back to Esc, then next PDF continues')
    page.evaluate('''() => {
      suppressDownload=null;blockClose=null;suppressClick='One.pdf';
      events=[];report=[];finished=false;showList();listener({type:'run',limit:1});
    }''')
    page.wait_for_function('finished', timeout=30000)
    assert 'missed-download-One.pdf' in page.evaluate('events')
    assert 'download-Two.pdf' in page.evaluate('events')
    assert page.evaluate('status').startswith('Hoàn tất: 1 thư, 1 PDF đã lưu, 1 lỗi.'), page.evaluate('status')
    assert any(e['phase']=='loi' and 'không nhận sự kiện click' in e['detail'] for e in page.evaluate('report'))
    print('Browser passed: missing click is reported immediately and next PDF continues')
    browser.close()
