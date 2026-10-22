"""A failed setup must not show the automatic schedule as enabled."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required for the extension schedule test')
class ExtensionScheduleTests(unittest.TestCase):
    def test_schedule_is_enabled_only_after_connection_state_and_alarm_are_ready(self):
        worker=(Path(__file__).resolve().parents[1]/'chrome-extension/worker.js').read_text()
        function=worker[worker.index('async function setAuto('):worker.index('chrome.alarms.onAlarm.addListener')]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
async function exercise(failMirror){
 const stored={autoEnabled:false},calls=[];
 const ctx={Date,AUTO_ALARM:'test-alarm',api:async()=>({}),mirrorAutomationState:async()=>{if(failMirror)throw Error('offline');},autoScan:async()=>{assert.equal(stored.autoEnabled,true);calls.push('scan');},stop:async()=>calls.push('stop'),chrome:{permissions:{contains:async()=>true},tabs:{query:async()=>[{url:'https://mail.google.com/mail/u/1/'}]},storage:{local:{get:async()=>({...stored}),set:async value=>Object.assign(stored,value)},session:{get:async()=>({})}},alarms:{create:async()=>calls.push('alarm'),clear:async()=>calls.push('clear')}}};
 vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
 if(failMirror){await assert.rejects(ctx.setAuto(true));assert.equal(stored.autoEnabled,false);assert.deepEqual(calls,[]);}
 else{await ctx.setAuto(true);assert.equal(stored.autoEnabled,true);assert.deepEqual(calls,['alarm','scan']);await ctx.setAuto(false);assert.equal(stored.autoEnabled,false);assert.deepEqual(calls,['alarm','scan','clear']);}
}
(async()=>{await exercise(true);await exercise(false);})().catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function))
        subprocess.run([shutil.which('node'),'-e',harness],check=True,capture_output=True,text=True)
