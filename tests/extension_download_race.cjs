const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');

function harness(){
 const listeners={},local={base:'http://localhost:8080',token:'test-token',capabilities:['local-download-pdf']},session={};
 let pauseAt=0,reads=0,release,requests=0;
 const storage=obj=>({
  async get(key){const snapshot=structuredClone({[key]:obj[key]});if(obj===session&&key==='run'&&++reads===pauseAt){await new Promise(resolve=>{release=resolve;});}return snapshot;},
  async set(values){Object.assign(obj,structuredClone(values));},async remove(key){delete obj[key];},async setAccessLevel(){}
 });
 const chrome={storage:{local:storage(local),session:storage(session)},
  runtime:{onMessage:{addListener(fn){listeners.message=fn;}},onStartup:{addListener(){}},onInstalled:{addListener(){}}},
  alarms:{onAlarm:{addListener(){}}},permissions:{async contains(){return true;}},
  debugger:{onDetach:{addListener(){}},async detach(){}},tabs:{async sendMessage(){}},
  downloads:{onCreated:{addListener(fn){listeners.created=fn;}},onChanged:{addListener(){}}}};
 const context={chrome,console,URL,Blob,FormData,TextDecoder,Date,AbortController,setTimeout,clearTimeout,
  async fetch(){requests++;return new Response(JSON.stringify({available:true,added:1,filename:'report.pdf'}),{headers:{'content-type':'application/json'}});}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('chrome-extension/worker.js','utf8'),context);
 const run=started=>({tab:1,started,pending:{armedAt:started,expectedName:'report.pdf',downloadId:null,candidates:[],result:null,error:null}});
 return {session,local,listeners,run,pause(at=1){pauseAt=at;},release(){release();},requests:()=>requests,
  send(message){return new Promise(resolve=>listeners.message(message,{},resolve));}};
}

(async()=>{
 for(const pauseAt of [1,2])for(const restart of [false,true]){
  const test=harness(),stamp=Date.now();test.session.run=test.run(stamp);test.pause(pauseAt);
  const pending=test.listeners.created({id:10,url:'https://mail.google.com/mail/u/0/?view=att',filename:'/Downloads/report.pdf',mime:'application/pdf',state:'complete'});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(JSON.stringify(await test.send({type:'stop'})),'{}');
  if(restart)test.session.run=test.run(stamp+1);
  test.release();await pending;
  if(restart){assert.equal(test.session.run.started,stamp+1);assert.equal(test.session.run.pending.downloadId,null);}
  else assert.equal(test.session.run,undefined,'A late Chrome event must not resurrect a stopped scan');
  assert.equal(test.requests(),0,'A stopped scan must not submit a late download to AI');
 }
 console.log('Download cancellation race passed: stale Chrome events cannot revive or replace a scan.');
})().catch(error=>{console.error(error);process.exitCode=1;});
