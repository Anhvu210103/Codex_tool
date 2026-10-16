'use strict';
chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'});
function baseURL(value){const url=new URL(value);if(url.protocol!=='http:'||!['localhost','127.0.0.1'].includes(url.hostname)||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Chỉ dùng địa chỉ tool localhost trên máy này.');return url.origin;}
async function api(path,body,override){const config=override||await chrome.storage.local.get(['base','token']);if(!config.token)throw Error('Dán mã ghép nối từ Cài đặt tool trước.');const headers={Authorization:'Bearer '+config.token};if(!(body instanceof FormData))headers['Content-Type']='application/json';const response=await fetch(baseURL(config.base||'http://localhost:8080')+path,{method:'POST',headers,body:body instanceof FormData?body:JSON.stringify(body)});if(!response.headers.get('content-type')?.includes('application/json'))throw Error('Địa chỉ này trả về trang HTML. Kiểm tra đúng cổng tool, tắt hẳn phiên tool cũ và mở bản mới.');let result;try{result=await response.json();}catch{throw Error('Tool trả dữ liệu không hợp lệ. Mở lại tool rồi thử lại.');}if(!response.ok)throw Error(result.error||'Tool từ chối kết nối.');return result;}
async function upload(blob,name){if(blob.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');const head=new TextDecoder().decode(await blob.slice(0,5).arrayBuffer());if(head!=='%PDF-')throw Error('Không tải được PDF hợp lệ. Hãy chọn PDF đã tải trong tiện ích.');const form=new FormData();form.append('file',blob,name);return api('/extension/pdf',form);}
function resultMessage(result){return 'Đã lưu: '+(result.filename||'PDF')+'\nNhóm: '+(result.categories?.join(', ')||'Xem trong sổ AI thao tác')+(result.review_reason?'\nCần kiểm tra: '+result.review_reason:'')+(result.folder?'\nThư mục: '+result.folder:'');}
async function stop(){const state=await chrome.storage.session.get('run');await chrome.storage.session.remove('run');if(state.run)await chrome.tabs.sendMessage(state.run.tab,{type:'stop'}).catch(()=>{});}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 (async()=>{
  if(message.type==='save'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const config={base:baseURL(message.base),token:message.token.trim()};const check=await api('/extension/ping',{},config);if(check.app!=='mailnotes-extension'||check.protocol!==1)throw Error('Phiên bản tool chưa hỗ trợ tiện ích.');await chrome.storage.local.set({...config,capabilities:check.capabilities||[]});return {};}
  if(message.type==='start'){
   if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const check=await api('/extension/ping',{});await chrome.storage.local.set({capabilities:check.capabilities||[]});await stop();const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab?.url?.startsWith('https://mail.google.com/'))throw Error('Mở tab Gmail rồi bấm lại.');
   const only=message.retry?(await chrome.storage.local.get('failures')).failures||[]:[];if(message.retry&&!only.length)throw Error('Chưa có file lỗi để thử lại.');
   await chrome.storage.session.set({run:{tab:tab.id,started:Date.now(),limit:message.limit===1?1:20}});await chrome.storage.local.set({status:message.retry?'Đang thử lại file lỗi...':'Đang tìm thư có PDF...',report:[],failures:[]});await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});await chrome.tabs.sendMessage(tab.id,{type:'run',limit:message.limit===1?1:20,only});return {};
  }
  if(message.type==='stop'){await stop();return {};}
  if(message.type==='upload'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const result=await upload(new Blob([new Uint8Array(message.bytes)],{type:'application/pdf'}),message.name);const status=resultMessage(result);await chrome.storage.local.set({status});return {...result,status};}
  const {run}=await chrome.storage.session.get('run');if(!run||sender.tab?.id!==run.tab||Date.now()-run.started>3600000)throw Error('Lượt thử đã dừng/hết hạn.');
  if(message.type==='failure'){
   const f=message.failure;if(!f||!Number.isInteger(f.rowIndex)||f.rowIndex<0||f.rowIndex>19||!Number.isInteger(f.fileIndex)||f.fileIndex<0||f.fileIndex>99||typeof f.key!=='string'||typeof f.text!=='string'||typeof f.name!=='string')throw Error('File lỗi không hợp lệ.');
   const current=(await chrome.storage.local.get('failures')).failures||[];
   current.push({rowIndex:f.rowIndex,key:f.key.slice(0,200),text:f.text.slice(0,240),fileIndex:f.fileIndex,name:f.name.slice(0,180)});
   await chrome.storage.local.set({failures:current.slice(-100)});return {};
  }
  if(message.type==='trace'){
   const event=message.event;if(!event||typeof event.phase!=='string'||typeof event.file!=='string'||typeof event.detail!=='string'||!Number.isInteger(event.mail))throw Error('Báo cáo không hợp lệ.');
   const current=(await chrome.storage.local.get('report')).report||[];
   current.push({time:new Date().toLocaleTimeString('vi-VN'),phase:event.phase.slice(0,32),mail:event.mail,file:event.file.slice(0,180),detail:event.detail.slice(0,180)});
   await chrome.storage.local.set({report:current.slice(-500)});return {};
  }
  if(message.type==='finish'){await chrome.storage.session.remove('run');return {}; }
  if(message.type==='arm-download'){await chrome.storage.session.set({run:{...run,pending:{armedAt:Date.now(),downloadId:null,result:null,error:null}}});return {}; }
  if(message.type==='download-state')return run.pending||{};
  if(message.type==='choose')return api('/extension/choose',{kind:message.kind,candidates:message.candidates});
  if(message.type==='progress'){await chrome.storage.local.set({status:message.text});return {};}
  throw Error('Yêu cầu không hợp lệ.');
 })().then(reply).catch(error=>reply({error:error.message}));return true;
});
const claimedDownloads=new Set();
async function handleDownload(item){
 const {run}=await chrome.storage.session.get('run');const pending=run?.pending;
 if(!pending||pending.result||pending.error||Date.now()-run.started>3600000)return;
 if(pending.downloadId!==null&&pending.downloadId!==item.id)return;
 if(pending.downloadId===null&&Date.now()-pending.armedAt>15000)return;
 if(pending.downloadId===null){const [active]=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(active?.id!==run.tab)return;}
 try{
  const url=new URL(item.url);const ref=new URL(item.referrer||'https://invalid.example/');
  const gmailBlob=item.url.startsWith('blob:https://mail.google.com/');
  if(item.referrer&&ref.hostname!=='mail.google.com'||!gmailBlob&&(url.protocol!=='https:'||!(url.hostname==='mail.google.com'||url.hostname.endsWith('.googleusercontent.com'))))return;
  if(pending.downloadId===null){pending.downloadId=item.id;await chrome.storage.session.set({run:{...run,pending}});}
  if(item.state==='interrupted'){pending.error='Chrome báo tải PDF thất bại.';await chrome.storage.session.set({run:{...run,pending}});return;}
  if(item.state!=='complete')return;
  if(!/\.pdf(?:$|[?#])/i.test(item.filename||'')&&item.mime!=='application/pdf')return;
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
  if(latest?.pending?.downloadId===item.id){latest.pending.result=result;await chrome.storage.session.set({run:latest});await chrome.storage.local.set({status:resultMessage(result)});}
 }catch(e){
  const latest=(await chrome.storage.session.get('run')).run;
  if(latest?.pending?.downloadId===item.id){latest.pending.error=e.message;await chrome.storage.session.set({run:latest});await chrome.storage.local.set({status:e.message});}
 }
}
chrome.downloads.onCreated.addListener(item=>handleDownload(item));
chrome.downloads.onChanged.addListener(async change=>{if(!change.filename&&!change.mime&&!change.state)return;const {run}=await chrome.storage.session.get('run');if(run?.pending?.downloadId!==change.id)return;const [item]=await chrome.downloads.search({id:change.id});if(item)await handleDownload(item);});
