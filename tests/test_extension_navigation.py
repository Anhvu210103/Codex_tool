"""Regression test for recovering the Gmail list after a stuck PDF viewer."""
from pathlib import Path
import json
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'Node is required for the extension navigation test')
class ExtensionNavigationTests(unittest.TestCase):
    def test_saved_search_route_recovers_when_close_and_back_are_unavailable(self):
        source=(Path(__file__).resolve().parents[1]/'chrome-extension/content.js').read_text()
        function=source[source.index('async function backToList('):source.index('function nextPageButton',source.index('async function backToList('))]
        harness=r'''
const vm=require('node:vm'),assert=require('node:assert/strict');
const target='#search/has%3Aattachment',events=[];
const location={origin:'https://mail.google.com',pathname:'/mail/u/0/',href:'https://mail.google.com/mail/u/0/#inbox',hash:'#inbox'};
const ctx={URL,location,history:{back(){events.push('history');}},dangerous:/x/,label:()=>'',visible:()=>true,
 document:{body:{innerText:''},querySelectorAll:()=>[]},send:async()=>{},clickPoint:()=>({x:0,y:0}),
 trace:async phase=>events.push(phase),pause:async()=>{},
 mailRows:()=>location.hash===target?[{node:{}}]:[],until:async get=>get()};
vm.createContext(ctx);vm.runInContext(FUNCTION,ctx);
ctx.backToList('https://mail.google.com/mail/u/0/'+target,()=>false).then(result=>{
 assert.equal(result,true);assert.equal(location.hash,target);assert(events.includes('quay-lai-danh-sach'));
}).catch(error=>{console.error(error);process.exitCode=1;});
'''.replace('FUNCTION',json.dumps(function))
        subprocess.run([shutil.which('node'),'-e',harness],check=True,capture_output=True,text=True)
