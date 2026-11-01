import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'),'Node is required for API timeout tests')
class ExtensionAPITimeoutTests(unittest.TestCase):
    def exercise(self,mode,path,timeout):
        source=(Path(__file__).resolve().parents[1]/'chrome-extension/worker.js').read_text(encoding='utf-8')
        functions=source[source.index('function baseURL('):source.index('async function syncHistoryGeneration(')]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let fire,duration,cleared=false;const mode=MODE;
const ctx={URL,FormData,AbortController,setTimeout(fn,ms){fire=fn;duration=ms;return 42;},clearTimeout(id){assert.equal(id,42);cleared=true;},chrome:{storage:{local:{get:async()=>({base:'http://localhost:8080',token:'test-token'})}}},
 fetch:async(url,options)=>{
  const pending=()=>new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(Error('aborted'))));
  if(mode==='fetch')return pending();
  return {ok:true,headers:{get:()=> 'application/json'},json:mode==='body'?pending:async()=>mode==='invalid'?null:{ok:true}};
 }};
vm.createContext(ctx);vm.runInContext(FUNCTIONS,ctx);
(async()=>{
 const pending=ctx.api(PATH,{});pending.catch(()=>{});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(duration,TIMEOUT);
 if(mode==='fetch'||mode==='body'){fire();await assert.rejects(pending,error=>/chưa phản hồi|6 phút/.test(error.message));}
 else if(mode==='invalid')await assert.rejects(pending,error=>error.message.includes('không hợp lệ'));
 else assert.equal((await pending).ok,true);
 assert(cleared,'Every outcome must cancel its timer');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTIONS',json.dumps(functions)).replace('MODE',json.dumps(mode)).replace('PATH',json.dumps(path)).replace('TIMEOUT',str(timeout))
        result=subprocess.run([shutil.which('node'),'-e',script],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_control_request_times_out_while_waiting_for_headers(self):
        self.exercise('fetch','/extension/ping',15000)

    def test_timeout_covers_reading_the_response_body(self):
        self.exercise('body','/extension/automation-state',15000)

    def test_pdf_processing_keeps_its_longer_deadline(self):
        self.exercise('fetch','/extension/import-local',360000)

    def test_success_releases_the_timeout_timer(self):
        self.exercise('success','/extension/ping',15000)

    def test_invalid_json_envelope_has_an_actionable_error(self):
        self.exercise('invalid','/extension/ping',15000)
