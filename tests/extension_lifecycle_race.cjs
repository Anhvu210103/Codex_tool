const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');

function deferred(){let release;const promise=new Promise(resolve=>{release=resolve;});return {promise,release};}
function harness(pause){
 const local={base:'http://localhost:8080',token:'test-token',autoEnabled:pause!=='mirror',autoFilter:{period:'all'}},session={},events=[];let onDetach;
 const reached=deferred(),gate=deferred();let hold=true,attached=false;
 const storage=obj=>({async get(keys){return structuredClone(Array.isArray(keys)?Object.fromEntries(keys.map(key=>[key,obj[key]])):{[keys]:obj[keys]});},async set(value){Object.assign(obj,structuredClone(value));},async remove(key){for(const item of [].concat(key))delete obj[item];},async setAccessLevel(){}});
 const chrome={storage:{local:storage(local),session:storage(session)},
  runtime:{onMessage:{addListener(){}},onStartup:{addListener(){}},onInstalled:{addListener(){}}},
  alarms:{onAlarm:{addListener(){}},async create(){events.push('alarm');},async clear(){events.push('clear');}},
  permissions:{async contains(){return true;}},
  tabs:{async query(){return [{id:1,url:'https://mail.google.com/mail/u/0/#inbox'}];},async get(id){return {id,status:'complete',url:'https://mail.google.com/mail/u/0/#inbox'};},async create(value){events.push('new-tab');return {id:1,status:'complete',...value};},async update(id,value){return {id,status:'complete',...value};},async reload(){},async sendMessage(id,message){events.push(message.type);}},
  scripting:{async executeScript(){events.push('inject');}},
  debugger:{onDetach:{addListener(listener){onDetach=listener;}},async attach(){if(attached)throw Error('Already attached to the tab');attached=true;if(pause==='attach'&&hold){hold=false;reached.release();await gate.promise;}events.push('attach');},async detach(){attached=false;events.push('detach');}},
  downloads:{onCreated:{addListener(){}},onChanged:{addListener(){}}}};
 const context={chrome,console,URL,Blob,FormData,Response,TextDecoder,Date,AbortController,setTimeout,clearTimeout,
  async fetch(url,options){const payload=JSON.parse(options.body);if(pause==='mirror'&&url.endsWith('/extension/automation-state')&&payload.action==='save'&&hold){hold=false;reached.release();await gate.promise;}return new Response(JSON.stringify(url.endsWith('/extension/ping')?{app:'mailnotes-extension',protocol:1,capabilities:[]}:{ok:true}),{headers:{'content-type':'application/json'}});}};
 vm.createContext(context);vm.runInContext(fs.readFileSync('chrome-extension/worker.js','utf8'),context);
 return {context,local,session,events,reached:reached.promise,release:gate.release,restore(){attached=true;session.run={tab:1,started:Date.now(),generation:500};},attached:()=>attached,detachEvent:source=>onDetach(source)};
}

(async()=>{
 for(const automatic of [false,true]){
  const test=harness('attach');
  const starting=automatic?test.context.autoScan(true):test.context.beginRun({id:1},20);
  await test.reached;
  if(automatic)await test.context.setAuto(false);else await test.context.stop();
  test.release();await starting.catch(()=>{});
  assert(!test.session.run,`${automatic?'Automatic':'Manual'} scan must not start after it was stopped during Chrome attachment`);
  assert(!test.events.includes('run'),'Cancelled startup must not send a run command to Gmail');
 }
 const test=harness('mirror'),enabling=test.context.setAuto(true);
 await test.reached;await test.context.setAuto(false);test.release();await enabling;
 assert.equal(test.local.autoEnabled,false,'An older enable operation must not override the newer disable action');
 assert(!test.events.includes('run'));
 const restarting=harness('attach'),first=restarting.context.beginRun({id:1},20);
 await restarting.reached;await restarting.context.stop();
 const second=restarting.context.beginRun({id:1},20);const secondOutcome=second.then(()=>null,error=>error);
 restarting.release();await first.catch(()=>{});assert.equal(await secondOutcome,null);
 assert(restarting.session.run,'A new start must recover after cancelling a pending Chrome attachment');
 assert.equal(restarting.events.filter(event=>event==='run').length,1);
 await restarting.context.stop();assert.equal(restarting.attached(),false);
 const restored=harness('none');restored.restore();await restored.context.stop();
 assert.equal(restored.attached(),false,'Stop must detach Chrome after the service worker restores a persisted run');
 for(const action of ['disable','detach']){
  const changed=harness('none');changed.restore();changed.session.run.automatic=true;
  const reached=deferred(),gate=deferred(),get=changed.context.chrome.storage.session.get;let hold=true;
  changed.context.chrome.storage.session.get=async keys=>{const snapshot=await get(keys);if(keys==='run'&&hold){hold=false;reached.release();await gate.promise;}return snapshot;};
  const pending=action==='disable'?changed.context.setAuto(false):changed.detachEvent({tabId:1});
  await reached.promise;
  const manual={tab:2,started:Date.now()+1,generation:501,automatic:false};
  const saving=changed.context.changeRun(()=>manual);await new Promise(resolve=>setImmediate(resolve));
  gate.release();await Promise.all([pending,saving]);
  assert.equal(changed.session.run?.generation,501,`An old ${action} action must not stop a newer manual scan`);
 }
 console.log('Extension lifecycle races passed: stop during Chrome attachment, disable during schedule setup.');
})().catch(error=>{console.error(error);process.exitCode=1;});
