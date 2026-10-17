'use strict';
chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'});
function baseURL(value){const url=new URL(value);if(url.protocol!=='http:'||!['localhost','127.0.0.1'].includes(url.hostname)||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Chỉ dùng địa chỉ tool localhost trên máy này.');return url.origin;}
async function api(path,body,override){const config=override||await chrome.storage.local.get(['base','token']);if(!config.token)throw Error('Dán mã ghép nối từ Cài đặt tool trước.');const headers={Authorization:'Bearer '+config.token};if(!(body instanceof FormData))headers['Content-Type']='application/json';const response=await fetch(baseURL(config.base||'http://localhost:8080')+path,{method:'POST',headers,body:body instanceof FormData?body:JSON.stringify(body)});if(!response.headers.get('content-type')?.includes('application/json'))throw Error('Địa chỉ này trả về trang HTML. Kiểm tra đúng cổng tool, tắt hẳn phiên tool cũ và mở bản mới.');let result;try{result=await response.json();}catch{throw Error('Tool trả dữ liệu không hợp lệ. Mở lại tool rồi thử lại.');}if(!response.ok)throw Error(result.error||'Tool từ chối kết nối.');return result;}
function migratedFailures(items){return (items||[]).filter(item=>item&&typeof item==='object').map(item=>({...item,stage:item.stage||'process-pdf',attempts:item.attempts||1,updatedAt:item.updatedAt||item.createdAt||Date.now()}));}
async function mirrorAutomationState(){const saved=await chrome.storage.local.get(['failures','scanCursors','autoEnabledAt']),failures=migratedFailures(saved.failures);await chrome.storage.local.set({failures});await api('/extension/automation-state',{action:'save',failures,scan_cursors:saved.scanCursors||{},auto_enabled_at:saved.autoEnabledAt||null});}
async function restoreAutomationState(config){const remote=await api('/extension/automation-state',{action:'load'},config);const local=await chrome.storage.local.get(['failures','scanCursors','autoEnabledAt']);const failures=[...migratedFailures(remote.failures),...migratedFailures(local.failures)];const unique=[];for(const item of failures){const key=[item.stage,item.key,item.fileKey||'',item.fileIndex,item.name].join('\u0000');if(!unique.some(entry=>entry._key===key))unique.push({...item,_key:key});}const scanCursors={};for(const source of [remote.scan_cursors||{},local.scanCursors||{}])for(const [account,stamp] of Object.entries(source))scanCursors[account]=Math.max(scanCursors[account]||0,stamp);const enabled=[local.autoEnabledAt,remote.auto_enabled_at].filter(Number.isFinite);await chrome.storage.local.set({failures:unique.slice(-100).map(({_key,...item})=>item),scanCursors,autoEnabledAt:enabled.length?Math.min(...enabled):Date.now()});}
async function upload(blob,name){if(blob.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');const head=new TextDecoder().decode(await blob.slice(0,5).arrayBuffer());if(head!=='%PDF-')throw Error('Không tải được PDF hợp lệ. Hãy chọn PDF đã tải trong tiện ích.');const form=new FormData();form.append('file',blob,name);return api('/extension/pdf',form);}
function resultMessage(result){return (result.added===0?'Đã có trong sổ, không tạo dòng mới: ':'Đã lưu mới: ')+(result.filename||'PDF')+'\nXem tại Sổ ghi chép → chọn nguồn AI thao tác.'+'\nNhóm: '+(result.categories?.join(', ')||'Cần xem lại')+(result.review_reason?'\nCần kiểm tra: '+result.review_reason:'')+(result.local_pdf_paths?.length?'\nPDF trên máy:\n'+result.local_pdf_paths.join('\n'):result.folder?'\nThư mục: '+result.folder:'');}
async function detach(tab){if(tab!==undefined)await chrome.debugger.detach({tabId:tab}).catch(()=>{});}
async function stop(){const state=await chrome.storage.session.get('run');await chrome.storage.session.remove('run');if(state.run){await chrome.tabs.sendMessage(state.run.tab,{type:'stop'}).catch(()=>{});await detach(state.run.tab);}}
let reportWrites=Promise.resolve();
function appendReport(event){reportWrites=reportWrites.catch(()=>{}).then(async()=>{const current=(await chrome.storage.local.get('report')).report||[];current.push({time:new Date().toLocaleTimeString('vi-VN'),phase:String(event.phase).slice(0,32),mail:event.mail||0,file:String(event.file||'').slice(0,180),detail:String(event.detail||'').slice(0,180)});await chrome.storage.local.set({report:current.slice(-500)});});return reportWrites;}
const AUTO_ALARM='mailnotes-gmail-30m';
function mailIdentity(message){
 if(typeof message.key!=='string'||!message.key||message.key.length>200||typeof message.fingerprint!=='string'||!message.fingerprint||message.fingerprint.length>2000)throw Error('Định danh thư không hợp lệ.');
 return {key:message.key,fingerprint:message.fingerprint};
}
async function ledger(){return (await chrome.storage.local.get('processedMails')).processedMails||{};}
async function updateLedger(message,complete){
 const {key,fingerprint}=mailIdentity(message),records=await ledger();
 const previous=records[key]?.fingerprint===fingerprint?records[key]:{fingerprint,files:[],complete:false};
 if(!complete){if(typeof message.fileKey!=='string'||message.fileKey.length>400)throw Error('Định danh PDF không hợp lệ.');if(!previous.files.includes(message.fileKey))previous.files.push(message.fileKey);}
 else previous.complete=true;
 previous.touched=Date.now();records[key]=previous;
 const keys=Object.keys(records);
 if(keys.length>5000)for(const old of keys.sort((a,b)=>(records[a].touched||0)-(records[b].touched||0)).slice(0,keys.length-5000))delete records[old];
 await chrome.storage.local.set({processedMails:records});
}
function searchURL(accountIndex='0',since=Date.now()-86400000){
 const today=new Date(),start=new Date(since);start.setDate(start.getDate()-1);const tomorrow=new Date(today);tomorrow.setDate(today.getDate()+1);
 const day=date=>[date.getFullYear(),String(date.getMonth()+1).padStart(2,'0'),String(date.getDate()).padStart(2,'0')].join('/');
 return 'https://mail.google.com/mail/u/'+accountIndex+'/#search/'+encodeURIComponent('has:attachment filename:pdf after:'+day(start)+' before:'+day(tomorrow));
}
async function readyTab(tabId){
 for(let i=0;i<30;i++){const tab=await chrome.tabs.get(tabId);if(tab.status==='complete')return;await new Promise(resolve=>setTimeout(resolve,500));}
 throw Error('Gmail chưa tải xong sau 15 giây.');
}
async function beginRun(tab,limit,only=[],automatic=false,accountIndex='0',scanStartedAt=Date.now()){
 if(!await chrome.permissions.contains({permissions:['debugger']}))throw Error('Chrome chưa cấp quyền điều khiển tab PDF.');
 await chrome.debugger.attach({tabId:tab.id},'1.3');
 try{
  await chrome.storage.session.set({run:{tab:tab.id,started:Date.now(),limit,automatic,accountIndex,scanStartedAt}});
  await chrome.storage.local.set({status:automatic?'Đang tự kiểm tra Gmail từ lần quét thành công gần nhất...':only.length?'Đang thử lại file lỗi...':'Đang tìm thư có PDF...',report:[]});
  await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});
  await chrome.tabs.sendMessage(tab.id,{type:'run',limit,only,automatic});
 }catch(error){await chrome.storage.session.remove('run');await detach(tab.id);throw error;}
}
let autoStarting=false;
async function autoScan(){
 if(autoStarting)return;
 autoStarting=true;
 try {
  const saved=await chrome.storage.local.get(['autoEnabled','autoTabId','autoAccountIndex','autoEnabledAt','scanCursors']);if(!saved.autoEnabled)return;
  const running=(await chrome.storage.session.get('run')).run;
  if(running){
   const tab=await chrome.tabs.get(running.tab).catch(()=>null);
   if(!tab||Date.now()-running.started>3600000)await stop();
   else {await appendReport({phase:'lich-bo-qua',detail:'Lượt trước vẫn đang chạy'});return;}
  }
  const check=await api('/extension/ping',{});await chrome.storage.local.set({capabilities:check.capabilities||[]});
  let tab=saved.autoTabId?await chrome.tabs.get(saved.autoTabId).catch(()=>null):null;
  if(tab && !tab.url?.startsWith('https://mail.google.com/'))tab=null;
  const accountIndex=saved.autoAccountIndex||'0';const scanStartedAt=Date.now();const since=saved.scanCursors?.[accountIndex]||saved.autoEnabledAt||scanStartedAt-86400000;
  const url=searchURL(accountIndex,since);
  if(tab){if(tab.url===url)await chrome.tabs.reload(tab.id);else tab=await chrome.tabs.update(tab.id,{url});}
  else {tab=await chrome.tabs.create({url,active:false});await chrome.storage.local.set({autoTabId:tab.id});}
  await new Promise(resolve=>setTimeout(resolve,500));
  await readyTab(tab.id);
  if(!(await chrome.storage.local.get('autoEnabled')).autoEnabled)return;
  await beginRun(tab,100,[],true,accountIndex,scanStartedAt);
 }catch(error){await chrome.storage.local.set({status:'Lịch Gmail: '+error.message});await appendReport({phase:'lich-loi',detail:error.message});}
 finally{autoStarting=false;}
}
async function setAuto(enabled){
 if(enabled){
  await api('/extension/ping',{});if(!await chrome.permissions.contains({permissions:['debugger']}))throw Error('Chrome chưa cấp quyền điều khiển tab PDF.');
  const [active]=await chrome.tabs.query({active:true,currentWindow:true}),gmailTabs=await chrome.tabs.query({url:'https://mail.google.com/*'});
  const source=active?.url?.startsWith('https://mail.google.com/')?active:gmailTabs[0];
  const accountIndex=source?.url?.match(/^https:\/\/mail\.google\.com\/mail\/u\/(\d+)\//)?.[1]||'0';
  const previous=await chrome.storage.local.get('autoEnabledAt');await chrome.storage.local.set({autoEnabled:true,autoAccountIndex:accountIndex,autoEnabledAt:previous.autoEnabledAt||Date.now()});await mirrorAutomationState();await chrome.alarms.create(AUTO_ALARM,{periodInMinutes:30});await autoScan();
 }
 else {await chrome.storage.local.set({autoEnabled:false});await chrome.alarms.clear(AUTO_ALARM);if((await chrome.storage.session.get('run')).run?.automatic)await stop();}
}
chrome.alarms.onAlarm.addListener(alarm=>{if(alarm.name===AUTO_ALARM)return autoScan();});
async function restoreAlarm(){if((await chrome.storage.local.get('autoEnabled')).autoEnabled)await chrome.alarms.create(AUTO_ALARM,{periodInMinutes:30});}
chrome.runtime.onStartup.addListener(restoreAlarm);
chrome.runtime.onInstalled.addListener(restoreAlarm);

chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 (async()=>{
  if(message.type==='save'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const config={base:baseURL(message.base),token:message.token.trim()};const check=await api('/extension/ping',{},config);if(check.app!=='mailnotes-extension'||check.protocol!==1)throw Error('Phiên bản tool chưa hỗ trợ tiện ích.');await restoreAutomationState(config);await chrome.storage.local.set({...config,capabilities:check.capabilities||[]});await mirrorAutomationState();return {};}
  if(message.type==='set-auto'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');if(typeof message.enabled!=='boolean')throw Error('Lịch quét không hợp lệ.');await setAuto(message.enabled);return {};}
  if(message.type==='start'){
   if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const check=await api('/extension/ping',{});await chrome.storage.local.set({capabilities:check.capabilities||[]});await stop();const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab?.url?.startsWith('https://mail.google.com/'))throw Error('Mở tab Gmail rồi bấm lại.');
   const only=message.retry?((await chrome.storage.local.get('failures')).failures||[]).filter(item=>item.stage==='process-pdf'):[];if(message.retry&&!only.length)throw Error('Chưa có file PDF lỗi để thử lại. Các lỗi thư/trang sẽ được thử ở lượt quét kế tiếp.');
   await beginRun(tab,message.limit===1?1:20,only);return {};
  }
  if(message.type==='stop'){await stop();return {};}
  if(message.type==='upload'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const result=await upload(new Blob([new Uint8Array(message.bytes)],{type:'application/pdf'}),message.name);const status=resultMessage(result);await chrome.storage.local.set({status});return {...result,status};}
  const {run}=await chrome.storage.session.get('run');if(!run||sender.tab?.id!==run.tab||Date.now()-run.started>3600000)throw Error('Lượt thử đã dừng/hết hạn.');
  if(message.type==='mail-state'){
   const {key,fingerprint}=mailIdentity(message),records=await ledger(),row=records[key];
   if(row&&row.fingerprint!==fingerprint&&fingerprint===key&&/^[0-9a-f]{16}:\d+$/.test(row.fingerprint||'')){
    // Older versions hashed the visible row text, which changes when a mail is read.
    // The thread key and the attachment list are stable enough to reuse the record.
    row.fingerprint=key;await chrome.storage.local.set({processedMails:records});
   }
   return row?.fingerprint===fingerprint?{complete:!!row.complete,files:row.files||[],record:'match'}:{complete:false,files:[],record:row?'changed':'missing'};
  }
  if(message.type==='pdf-record'){await updateLedger(message,false);return {};}
  if(message.type==='mail-complete'){await updateLedger(message,true);return {};}
  if(message.type==='mail-incomplete'){const {key,fingerprint}=mailIdentity(message),records=await ledger();if(records[key]?.fingerprint===fingerprint){records[key].complete=false;await chrome.storage.local.set({processedMails:records});}return {};}
  if(message.type==='pending-failures')return {failures:(await chrome.storage.local.get('failures')).failures||[]};
  if(message.type==='clear-failure'){
   const failures=(await chrome.storage.local.get('failures')).failures||[];
   await chrome.storage.local.set({failures:failures.filter(item=>item.key!==message.key||(item.fileKey&&message.fileKey?item.fileKey!==message.fileKey:item.fileIndex!==message.fileIndex||item.name!==message.name))});await mirrorAutomationState();return {};
  }
  if(message.type==='failure'){
   const f=message.failure;if(!f||!Number.isInteger(f.rowIndex)||f.rowIndex<0||f.rowIndex>99||!Number.isInteger(f.fileIndex)||f.fileIndex< -1||f.fileIndex>99||typeof f.key!=='string'||typeof f.text!=='string'||typeof f.name!=='string'||typeof f.stage!=='string'||!f.stage||(f.fileKey!==undefined&&(typeof f.fileKey!=='string'||f.fileKey.length>400)))throw Error('Lỗi hàng đợi không hợp lệ.');
   const current=(await chrome.storage.local.get('failures')).failures||[];
   const existing=current.find(item=>item.stage===f.stage&&item.key===f.key&&(item.fileKey&&f.fileKey?item.fileKey===f.fileKey:item.fileIndex===f.fileIndex&&item.name===f.name));
   if(existing){existing.attempts=(existing.attempts||1)+1;existing.lastError=String(f.error||'').slice(0,240);existing.updatedAt=Date.now();}
   else current.push({rowIndex:f.rowIndex,key:f.key.slice(0,200),text:f.text.slice(0,240),fileIndex:f.fileIndex,name:f.name.slice(0,180),fileKey:f.fileKey,stage:f.stage.slice(0,40),lastError:String(f.error||'').slice(0,240),attempts:1,createdAt:Date.now(),updatedAt:Date.now()});
   await chrome.storage.local.set({failures:current.slice(-100)});await mirrorAutomationState();return {};
  }
  if(message.type==='trace'){
   const event=message.event;if(!event||typeof event.phase!=='string'||typeof event.file!=='string'||typeof event.detail!=='string'||!Number.isInteger(event.mail))throw Error('Báo cáo không hợp lệ.');
   await appendReport(event);return {};
  }
  if(message.type==='trusted-click'){
   if(!Number.isFinite(message.x)||!Number.isFinite(message.y)||message.x<0||message.y<0||message.x>10000||message.y>10000)throw Error('Vị trí bấm không hợp lệ.');
   const target={tabId:run.tab},coords={x:message.x,y:message.y};
   await chrome.debugger.sendCommand(target,'Input.dispatchMouseEvent',{type:'mouseMoved',...coords,button:'none'});
   await chrome.debugger.sendCommand(target,'Input.dispatchMouseEvent',{type:'mousePressed',...coords,button:'left',clickCount:1});
   try{await chrome.debugger.sendCommand(target,'Input.dispatchMouseEvent',{type:'mouseReleased',...coords,button:'left',clickCount:1});}
   catch(error){await chrome.debugger.sendCommand(target,'Input.dispatchMouseEvent',{type:'mouseReleased',...coords,button:'left',clickCount:1}).catch(()=>{});throw error;}
   return {};
  }
  if(message.type==='trusted-escape'){
   const target={tabId:run.tab},key={key:'Escape',code:'Escape',windowsVirtualKeyCode:27,nativeVirtualKeyCode:27};
   await chrome.debugger.sendCommand(target,'Input.dispatchKeyEvent',{type:'keyDown',...key});
   await chrome.debugger.sendCommand(target,'Input.dispatchKeyEvent',{type:'keyUp',...key});
   return {};
  }
  if(message.type==='scan-complete'){
   if(run.automatic&&message.success===true){const saved=await chrome.storage.local.get('scanCursors'),cursors=saved.scanCursors||{};cursors[run.accountIndex||'0']=run.scanStartedAt||run.started;await chrome.storage.local.set({scanCursors:cursors});await mirrorAutomationState();}
   return {};
  }
  if(message.type==='finish'){await chrome.storage.session.remove('run');await detach(run.tab);return {}; }
  if(message.type==='arm-download'){if(typeof message.name!=='string'||!message.name.toLowerCase().endsWith('.pdf'))throw Error('Tên PDF chờ tải không hợp lệ.');await chrome.storage.session.set({run:{...run,pending:{armedAt:Date.now(),downloadId:null,candidates:[],expectedName:message.name,result:null,error:null}}});return {}; }
  if(message.type==='download-state')return run.pending||{};
  if(message.type==='choose')return api('/extension/choose',{kind:message.kind,candidates:message.candidates});
  if(message.type==='progress'){await chrome.storage.local.set({status:message.text});return {};}
  throw Error('Yêu cầu không hợp lệ.');
 })().then(reply).catch(error=>reply({error:error.message}));return true;
});
const claimedDownloads=new Set();
function comparableName(path){return String(path||'').split(/[\\/]/).pop().normalize('NFC').replace(/[\u200e\u200f\u202a-\u202e\u2066-\u2069]/g,'').replace(/\s*\(\d+\)(?=\s*\.pdf$)/i,'').replace(/\s+(?=\.pdf$)/i,'').replace(/\s+/g,' ').trim().toLocaleLowerCase('vi');}
async function handleDownload(item){
 const {run}=await chrome.storage.session.get('run');const pending=run?.pending;
 if(!pending||pending.result||pending.error||Date.now()-run.started>3600000)return;
 if(pending.downloadId!==null&&pending.downloadId!==item.id)return;
 if(pending.downloadId===null&&Date.now()-pending.armedAt>15000)return;
 try{
  const url=new URL(item.url);
  const gmailBlob=item.url.startsWith('blob:https://mail.google.com/');
  // The Gmail viewer may move focus to a download bubble or another Chrome
  // surface. Active-tab checks discard the very downloads this run started.
  // The short armed window and Google download origin bind the event instead.
  if(!gmailBlob&&(url.protocol!=='https:'||!(url.hostname==='mail.google.com'||url.hostname.endsWith('.googleusercontent.com'))))return;
  if(pending.downloadId===null){
   if(!pending.candidates.includes(item.id))pending.candidates.push(item.id);
   if(!item.filename){await chrome.storage.session.set({run:{...run,pending}});return;}
   if(comparableName(item.filename)!==comparableName(pending.expectedName)){const mismatch=comparableName(item.filename);if(pending.lastMismatch!==mismatch){pending.lastMismatch=mismatch;await appendReport({phase:'chrome-ten-khong-khop',file:(item.filename||'').split(/[\\/]/).pop(),detail:'đang chờ '+pending.expectedName});}await chrome.storage.session.set({run:{...run,pending}});return;}
   pending.downloadId=item.id;await chrome.storage.session.set({run:{...run,pending}});await appendReport({phase:'chrome-bat-dau',detail:'lượt '+item.id+' · sau '+Math.round((Date.now()-pending.armedAt)/1000)+' giây · '+url.protocol+' · '+url.hostname+' · '+item.state,file:(item.filename||'').split(/[\\/]/).pop()});
  }
  if(item.state==='interrupted'){pending.error='Chrome báo tải PDF thất bại.';await chrome.storage.session.set({run:{...run,pending}});await appendReport({phase:'chrome-loi',detail:'Lượt tải '+item.id+' bị gián đoạn'});return;}
  if(item.state!=='complete')return;
  if(!/\.pdf(?:$|[?#])/i.test(item.filename||'')&&item.mime!=='application/pdf'){pending.error='Chrome đã tải một tệp không phải PDF.';await chrome.storage.session.set({run:{...run,pending}});return;}
  if(claimedDownloads.has(item.id))return;claimedDownloads.add(item.id);if(claimedDownloads.size>100)claimedDownloads.delete(claimedDownloads.values().next().value);
  await chrome.storage.local.set({status:'Đang chuyển PDF về tool...'});
  const {capabilities}=await chrome.storage.local.get('capabilities');let result;
  if(capabilities?.includes('linux-local-pdf')&&item.filename){result=await api('/extension/import-local',{path:item.filename});if(!result.available)result=null;}
  if(!result){
   if(gmailBlob)throw Error('Chrome lưu PDF dưới dạng blob; hãy chọn file vừa tải trong tiện ích để đưa vào sổ.');
   const response=await fetch(url.href,{credentials:'include'});if(!response.ok)throw Error('Không đọc lại được file tải xuống. Chọn PDF bằng tay trong tiện ích.');
   const length=Number(response.headers.get('content-length'));if(length>20*1024*1024)throw Error('PDF vượt 20 MB.');
   result=await upload(await response.blob(),(item.filename||'Gmail.pdf').split(/[\\/]/).pop());
  }
  const latest=(await chrome.storage.session.get('run')).run;
  if(latest?.pending?.downloadId===item.id){latest.pending.result=result;await chrome.storage.session.set({run:latest});await chrome.storage.local.set({status:resultMessage(result)});await appendReport({phase:'chrome-xong',file:(item.filename||'').split(/[\\/]/).pop(),detail:'Lượt tải '+item.id+' đã nhập vào tool'});}
 }catch(e){
  const latest=(await chrome.storage.session.get('run')).run;
  if(latest?.pending?.downloadId===item.id){latest.pending.error=e.message;await chrome.storage.session.set({run:latest});await chrome.storage.local.set({status:e.message});}
 }
}
chrome.downloads.onCreated.addListener(async item=>{
 const before=(await chrome.storage.session.get('run')).run;
 await handleDownload(item);
 if(!before?.pending||Date.now()-before.pending.armedAt>15000)return;
 try{
  const after=(await chrome.storage.session.get('run')).run;
  const url=new URL(item.url),claimed=after?.pending?.downloadId===item.id;
  if(after?.pending&&!claimed){const google=item.url.startsWith('blob:https://mail.google.com/')||(url.protocol==='https:'&&(url.hostname==='mail.google.com'||url.hostname.endsWith('.googleusercontent.com')));await appendReport({phase:google?'chrome-cho-ten':'chrome-bo-qua',detail:'lượt '+item.id+' · '+url.protocol+' · '+url.hostname+' · '+item.state+' · '+(google?'đang chờ Chrome cung cấp đúng tên '+after.pending.expectedName:'nguồn tải không thuộc Gmail/Google'),file:(item.filename||'').split(/[\\/]/).pop()});}
 }catch{}
});
chrome.downloads.onChanged.addListener(async change=>{if(!change.filename&&!change.mime&&!change.state)return;const {run}=await chrome.storage.session.get('run');const pending=run?.pending;if(!pending)return;if(pending.downloadId!==change.id&&!pending.candidates?.includes(change.id))return;const [item]=await chrome.downloads.search({id:change.id});if(item)await handleDownload(item);});

chrome.debugger.onDetach.addListener(async source=>{const {run}=await chrome.storage.session.get('run');if(run?.tab===source.tabId){await appendReport({phase:'chrome-ngat',detail:'Chrome đã ngắt quyền điều khiển tab'});await chrome.storage.local.set({status:'Chrome đã ngắt quyền điều khiển tab. Thử lại lượt quét.'});await stop();}});
