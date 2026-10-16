"""Chrome user input events activate downloads that HTMLElement.click cannot."""
from playwright.sync_api import sync_playwright

with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True)
    context=browser.new_context(accept_downloads=True)
    page=context.new_page()
    page.set_content('''<button id="download" style="position:absolute;left:80px;top:40px;width:140px;height:45px">Tải xuống</button>
<button id="close" style="position:absolute;left:240px;top:40px;width:120px;height:45px">Đóng</button>
<script>
window.events=[];window.viewerClosed=false;
document.querySelector('button').addEventListener('click', event=>{
 events.push(event.isTrusted);
 if(!event.isTrusted)return;
 const blob=new Blob(['%PDF-test'],{type:'application/pdf'});
 const url=URL.createObjectURL(blob),link=document.createElement('a');
 link.href=url;link.download='test.pdf';document.body.append(link);link.click();link.remove();
});
document.querySelector('#close').addEventListener('click',event=>{if(event.isTrusted)viewerClosed=true;});
</script>''')
    page.evaluate("document.querySelector('button').click()")
    assert page.evaluate('events')==[False]
    session=context.new_cdp_session(page)
    with page.expect_download(timeout=10000) as download:
        session.send('Input.dispatchMouseEvent',{'type':'mouseMoved','x':150,'y':62,'button':'none'})
        session.send('Input.dispatchMouseEvent',{'type':'mousePressed','x':150,'y':62,'button':'left','clickCount':1})
        session.send('Input.dispatchMouseEvent',{'type':'mouseReleased','x':150,'y':62,'button':'left','clickCount':1})
    assert download.value.suggested_filename=='test.pdf'
    assert page.evaluate('events')==[False,True]
    page.evaluate("document.querySelector('#close').click()")
    assert not page.evaluate('viewerClosed')
    session.send('Input.dispatchMouseEvent',{'type':'mouseMoved','x':300,'y':62,'button':'none'})
    session.send('Input.dispatchMouseEvent',{'type':'mousePressed','x':300,'y':62,'button':'left','clickCount':1})
    session.send('Input.dispatchMouseEvent',{'type':'mouseReleased','x':300,'y':62,'button':'left','clickCount':1})
    assert page.evaluate('viewerClosed')
    print('Browser passed: trusted Chrome input triggers Download and Close when synthetic .click is ignored')
    browser.close()
