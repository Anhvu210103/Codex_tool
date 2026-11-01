import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'),'Node is required for the batch scan test')
class ExtensionBatchTests(unittest.TestCase):
    def exercise(self,retry=False):
        source=(Path(__file__).resolve().parents[1]/'chrome-extension/content.js').read_text(encoding='utf-8')
        function=source[source.index('async function run('):source.index('return {run};')]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const list='https://mail.google.com/mail/u/0/#search/pdf',ledger={},failures=[],attempts=[];
let current=-1,failOnce=true;
const tiles=index=>Array.from({length:3},(_,file)=>({name:`mail-${index}-file-${file}.pdf`,index:file,fileKey:`${index}:${file}`,legacyKey:`old-${index}:${file}`,node:{}}));
const rows=Array.from({length:30},(_,index)=>({key:`mail-${index}`,version:`version-${index}`,text:`Sender ${index}`,index,node:{scrollIntoView(){},click(){current=index;ctx.location.href=`https://mail.google.com/mail/u/0/#all/message-${index}`;}}}));
const ctx={stopped:true,epoch:0,location:{href:list},document:{body:{innerText:''},querySelectorAll:()=>[]},chrome:{runtime:{getManifest:()=>({version:'test'})}},
 trace:async()=>{},progress:async()=>{},mailRows:()=>rows,visible:()=>true,until:async read=>read(),
 stablePdfTiles:async()=>tiles(current),pdfTiles:()=>tiles(current),recorded:(files,tile)=>files.includes(tile.fileKey)||files.includes(tile.legacyKey),viewerOpen:()=>false,
 readyDirectDownload:async()=>({}),
 clickAndWaitDirect:async(button,cancelled,mail,name)=>{attempts.push(name);if(!RETRY&&name==='mail-2-file-1.pdf'&&failOnce){failOnce=false;const error=Error('Temporary backend error');error.downloadStarted=true;throw error;}return {added:1,filename:name};},
 backToList:async()=>{ctx.location.href=list;return true;},nextPageButton:()=>null,
 send:async message=>{
  const row=ledger[message.key]||(ledger[message.key]={files:[],complete:false});
  if(message.type==='mail-state')return {...row,record:'match'};
  if(message.type==='pdf-record')row.files.push(message.fileKey);
  if(message.type==='mail-complete')row.complete=true;
  if(message.type==='mail-incomplete')row.complete=false;
  if(message.type==='pending-failures')return {failures};
  if(message.type==='failure')failures.push(message.failure);
  if(message.type==='clear-failure'){for(let i=failures.length-1;i>=0;i--)if(failures[i].key===message.key&&failures[i].fileKey===message.fileKey)failures.splice(i,1);}
  return {};
 }};
vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
(async()=>{
 if(RETRY){
  await ctx.run(20,[{key:'mail-29',fileIndex:1,name:'mail-29-file-1.pdf',fileKey:'29:1'}],false);
  assert.deepEqual(attempts,['mail-29-file-1.pdf'],'Retry must find a failed mail beyond the first 20 visible rows');
 }else{
  ledger['mail-0']={files:['0:0','0:1','0:2'],complete:true};ledger['mail-1']={files:['1:0'],complete:false};
  await ctx.run(20,[],false);
  assert.equal(attempts.length,56,'A 20-mail run with 3 PDFs each must check every remaining attachment');
  assert.equal(failures.length,1);assert.equal(failures[0].name,'mail-2-file-1.pdf');
  assert(!attempts.some(name=>name.startsWith('mail-20-')),'Manual mode must respect the 20-mail limit');
  const previous=attempts.length;ctx.location.href=list;
  await ctx.run(20,[],false);
  assert.deepEqual(attempts.slice(previous),['mail-2-file-1.pdf'],'A second scan must only retry the file that failed');
  assert.equal(failures.length,0);assert(ledger['mail-2'].complete);
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function)).replace('RETRY','true' if retry else 'false')
        result=subprocess.run([shutil.which('node'),'-e',harness],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_twenty_mails_multiple_pdfs_continue_after_failure_and_retry_only_failed_file(self):
        self.exercise()

    def test_retry_can_find_mail_beyond_first_twenty_visible_rows(self):
        self.exercise(retry=True)
