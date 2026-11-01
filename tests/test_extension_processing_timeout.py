import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'),'Node is required for download timing tests')
class ExtensionProcessingTimeoutTests(unittest.TestCase):
    def exercise(self,mode):
        source=(Path(__file__).resolve().parents[1]/'chrome-extension/content.js').read_text(encoding='utf-8')
        function=source[source.index('async function waitDownload('):source.index('function clickPoint(')]
        script=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
let now=0;const mode=MODE;
const ctx={Date:{now:()=>now},progress:async()=>{},pause:async delay=>{now+=delay;},send:async()=>({downloadId:mode==='no-start'?null:0,result:mode==='slow-ocr'&&now>=150000?{added:1}:null})};
vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
(async()=>{
 if(mode==='slow-ocr'){const result=await ctx.waitDownload(()=>false);assert.equal(result.added,1);assert.equal(now,150000);}
 else if(mode==='timeout'){await assert.rejects(ctx.waitDownload(()=>false),error=>error.downloadStarted===true&&error.message.includes('6 phút'));}
 else {await assert.rejects(ctx.waitDownload(()=>false),error=>error.message.includes('chưa bắt đầu tải'));assert.equal(now,30000);}
})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function)).replace('MODE',json.dumps(mode))
        result=subprocess.run([shutil.which('node'),'-e',script],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_waits_for_ocr_longer_than_two_minutes_without_redownloading(self):
        self.exercise('slow-ocr')

    def test_processing_timeout_preserves_download_started_flag(self):
        self.exercise('timeout')

    def test_no_download_still_times_out_after_thirty_seconds(self):
        self.exercise('no-start')
