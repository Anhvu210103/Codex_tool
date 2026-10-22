"""Run the production scan branch through PDF selection with fake Gmail state."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required for the extension scan test')
class ExtensionScanFlowTests(unittest.TestCase):
    def test_open_pdf_select_download_and_record_result(self):
        source=(Path(__file__).resolve().parents[1]/'chrome-extension/content.js').read_text()
        function=source[source.index('async function run('):source.index('chrome.runtime.onMessage.addListener')]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const events=[],attachment={name:'one.pdf',index:0,fileKey:'gmail:file1',legacyKey:'one'};
const row={key:'thread1',version:'message1',text:'Sender one.pdf',index:0,node:{scrollIntoView(){},click(){events.push('open-mail');}}};
const ctx={stopped:true,epoch:0,chrome:{runtime:{getManifest:()=>({version:'test'})}},location:{href:'https://mail.google.com/mail/u/0/#search/pdf'},document:{querySelectorAll:()=>[]},
 trace:async(phase)=>events.push(phase),progress:async()=>{},mailRows:()=>[row],visible:()=>true,
 stablePdfTiles:async()=>[attachment],pdfTiles:()=>[attachment],recorded:()=>false,
 send:async message=>{events.push(message.type);if(message.type==='mail-state')return {record:'missing',complete:false,files:[]};return {};},
 openTile:async()=>events.push('open-pdf'),until:async get=>get(),viewerOpen:()=>true,
 readyDownload:async(cancelled,mail,file)=>{assert.equal(mail,1);assert.equal(file,'one.pdf');events.push('select-download');return {tagName:'BUTTON'};},
 clickPoint:()=>({x:100,y:30}),label:()=> 'Download',clickAndWaitDownload:async()=>({added:1,filename:'one.pdf'}),
 closeViewer:async()=>events.push('close-pdf'),backToList:async()=>true,nextPageButton:()=>null};
vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
ctx.run(1,[],false).then(()=>{assert(events.includes('select-download'));assert(events.includes('da-luu'));assert(!events.includes('loi'));assert(events.indexOf('select-download')<events.indexOf('close-pdf'));}).catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function))
        subprocess.run([shutil.which('node'),'-e',harness],check=True,capture_output=True,text=True)
