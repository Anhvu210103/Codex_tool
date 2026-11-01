import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'),'Node is required for admin request tests')
class AdminAPITests(unittest.TestCase):
    def exercise(self,mode,path='/api/status'):
        source=(Path(__file__).resolve().parents[1]/'mailnotes/static/admin.js').read_text(encoding='utf-8')
        function=source[source.index('async function api('):source.index('const post =')]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const mode=MODE,path=PATH;let fire,duration,cleared=false,request;
const ctx={FormData,AbortController,TypeError,csrf:'csrf-fixture',setTimeout(fn,ms){fire=fn;duration=ms;return 1;},clearTimeout(){cleared=true;},fetch:async(url,options)=>{
 request=options;const stalled=()=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Error('abort'))));
 if(mode==='fetch')return stalled();
 if(mode==='network')throw new TypeError('Failed to fetch');
 return {ok:true,headers:{get:()=> 'application/json'},json:mode==='body'?stalled:async()=>mode==='array'?[{category:'Budget'}]:{ok:true}};
}};
vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
(async()=>{
 const body=mode==='multipart'?new FormData():undefined;
 const pending=ctx.api(path,body?{method:'POST',body}:{});pending.catch(()=>{});
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(duration,path==='/api/pdf'?360000:15000);
 if(mode==='fetch'||mode==='body'){fire();await assert.rejects(pending,error=>/chưa phản hồi|6 phút/.test(error.message));}
 else if(mode==='network')await assert.rejects(pending,error=>error.message.includes('Mất kết nối'));
 else if(mode==='array')assert.equal((await pending)[0].category,'Budget');
 else {assert.equal((await pending).ok,true);assert.equal(request.headers['X-CSRF-Token'],'csrf-fixture');assert.equal(request.headers['Content-Type'],undefined);assert.equal(request.body,body);}
 assert(cleared);
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function)).replace('MODE',json.dumps(mode)).replace('PATH',json.dumps(path))
        result=subprocess.run([shutil.which('node'),'-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_stalled_status_request_times_out(self):self.exercise('fetch')

    def test_stalled_response_body_times_out(self):self.exercise('body')

    def test_pdf_keeps_its_processing_deadline(self):self.exercise('fetch','/api/pdf')

    def test_pdf_upload_preserves_multipart_headers_and_csrf(self):self.exercise('multipart','/api/pdf')

    def test_group_presets_accept_array_response(self):self.exercise('array','/api/group-presets')

    def test_disconnected_server_has_an_actionable_message(self):self.exercise('network')
