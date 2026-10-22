"""Exercise production Gmail download selection in a real DOM, without Gmail login."""
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright


def main():
    source=(Path(__file__).resolve().parents[1]/'chrome-extension/content.js').read_text()
    source=source.rstrip()[:-1]+"\nglobalThis.downloadTest={downloadControl,readyDownload};\n}"
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':2000,'height':800})
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.set_content('''<style>body{margin:0}button{position:absolute;width:40px;height:40px}#viewer{position:fixed;inset:0;background:white}#marker{position:absolute;left:400px;top:650px}</style>
          <button aria-label="Tải xuống" style="left:1850px;top:20px">Background attachment</button>
          <div id="viewer" role="dialog"><span id="marker" aria-label="Đang hiển thị người xem">PDF</span><div id="toolbar"></div></div>''')
        page.evaluate("""()=>{window.events=[];window.chrome={runtime:{sendMessage:async value=>{events.push(value);return {};},onMessage:{addListener:()=>{}}}};}""")
        page.add_script_tag(content=source)
        def check(markup,expected):
            page.locator('#toolbar').evaluate('(node,html)=>node.innerHTML=html',markup)
            actual=page.evaluate('()=>downloadTest.downloadControl()?.id||null')
            assert actual==expected,(markup,actual,expected)
        check('<button id="download" aria-label="Tải xuống" style="left:1850px;top:12px"></button>','download')
        # Old code rejected these controls because they are not in the last
        # 160px or their lower edge is below the hard-coded 80px header.
        check('<button id="download" aria-label="Download" style="left:1200px;top:100px"></button>','download')
        check('<button id="download" aria-label="PDF action" style="left:1200px;top:100px"><span data-tooltip="Tải xuống">↓</span></button>','download')
        check('<button id="disabled" aria-label="Download" disabled style="left:1250px;top:100px"></button><button id="download" aria-label="Download" style="left:1200px;top:100px"></button>','download')
        check('<button id="download" aria-label="Download" aria-disabled="true" style="left:1200px;top:100px"></button>',None)
        check('<button id="download" aria-label="Download" style="left:1200px;top:100px"></button><div style="position:absolute;left:1190px;top:90px;width:70px;height:70px;background:red"></div>',None)
        check('<button id="download" aria-label="Download all attachments" style="left:1200px;top:100px"></button>',None)
        check('<button id="download" aria-label="Download" style="left:1200px;top:400px"></button>',None)
        check('<button id="a" aria-label="Download" style="left:1200px;top:100px"></button><button id="b" aria-label="Download" style="left:1250px;top:100px"></button>',None)
        check('<button aria-label="In" style="left:1100px;top:100px"></button><button id="download" style="left:1150px;top:100px"></button><button aria-label="Thêm" style="left:1200px;top:100px"></button>','download')
        check('<button style="left:1100px;top:100px"></button><button id="unknown" style="left:1150px;top:100px"></button><button style="left:1200px;top:100px"></button>',None)
        check('<button id="download" aria-label="Download" disabled style="left:1200px;top:100px"></button>',None)
        page.evaluate("setTimeout(()=>document.querySelector('#download').disabled=false,500)")
        assert page.evaluate('async()=> (await downloadTest.readyDownload(()=>false,1,"sample.pdf"))?.id')=='download'
        assert not errors,errors
        browser.close()
    print('Download DOM selection: OK (12 cases; live Gmail not exercised)')


if __name__=='__main__':
    main()
