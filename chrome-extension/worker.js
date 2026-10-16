'use strict';
chrome.storage.local.setAccessLevel({accessLevel:'TRUSTED_CONTEXTS'});
function baseURL(value){const url=new URL(value);if(url.protocol!=='http:'||!['localhost','127.0.0.1'].includes(url.hostname)||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Chỉ dùng địa chỉ tool localhost trên máy này.');return url.origin;}
async function api(path,body,override){const config=override||await chrome.storage.local.get(['base','token']);if(!config.token)throw Error('Dán mã ghép nối từ Cài đặt tool trước.');const headers={Authorization:'Bearer '+config.token};if(!(body instanceof FormData))headers['Content-Type']='application/json';const response=await fetch(baseURL(config.base||'http://localhost:8080')+path,{method:'POST',headers,body:body instanceof FormData?body:JSON.stringify(body)});if(!response.headers.get('content-type')?.includes('application/json'))throw Error('Địa chỉ này trả về trang HTML. Kiểm tra đúng cổng tool, tắt hẳn phiên tool cũ và mở bản mới.');let result;try{result=await response.json();}catch{throw Error('Tool trả dữ liệu không hợp lệ. Mở lại tool rồi thử lại.');}if(!response.ok)throw Error(result.error||'Tool từ chối kết nối.');return result;}
async function upload(blob,name){if(blob.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');const head=new TextDecoder().decode(await blob.slice(0,5).arrayBuffer());if(head!=='%PDF-')throw Error('Không tải được PDF hợp lệ. Hãy chọn PDF đã tải trong tiện ích.');const form=new FormData();form.append('file',blob,name);return api('/extension/pdf',form);}
async function stop(){const state=await chrome.storage.session.get('run');await chrome.storage.session.remove('run');if(state.run)await chrome.tabs.sendMessage(state.run.tab,{type:'stop'}).catch(()=>{});}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
 (async()=>{
  if(message.type==='save'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');const config={base:baseURL(message.base),token:message.token.trim()};const check=await api('/extension/ping',{},config);if(check.app!=='mailnotes-extension'||check.protocol!==1)throw Error('Phiên bản tool chưa hỗ trợ tiện ích.');await chrome.storage.local.set(config);return {};}
  if(message.type==='start'){
   if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');await api('/extension/ping',{});await stop();const [tab]=await chrome.tabs.query({active:true,currentWindow:true});if(!tab?.url?.startsWith('https://mail.google.com/'))throw Error('Mở tab Gmail rồi bấm lại.');
   await chrome.storage.session.set({run:{tab:tab.id,started:Date.now()}});await chrome.storage.local.set({status:'Đang tìm thư có PDF...'});await chrome.scripting.executeScript({target:{tabId:tab.id},files:['content.js']});await chrome.tabs.sendMessage(tab.id,{type:'run'});return {};
  }
  if(message.type==='stop'){await stop();return {};}
  if(message.type==='upload'){if(sender.tab)throw Error('Thao tác chỉ từ tiện ích.');return upload(new Blob([new Uint8Array(message.bytes)],{type:'application/pdf'}),message.name);}
  const {run}=await chrome.storage.session.get('run');if(!run||sender.tab?.id!==run.tab||Date.now()-run.started>180000)throw Error('Lượt thử đã dừng/hết hạn.');
  if(message.type==='arm-download'){await chrome.storage.session.set({run:{...run,armedAt:Date.now()}});return {};}
  if(message.type==='choose')return api('/extension/choose',{kind:message.kind,candidates:message.candidates});
  if(message.type==='progress'){await chrome.storage.local.set({status:message.text});return {};}
  throw Error('Yêu cầu không hợp lệ.');
 })().then(reply).catch(error=>reply({error:error.message}));return true;
});
chrome.downloads.onCreated.addListener(async item=>{
 const {run}=await chrome.storage.session.get('run');if(!run||!run.armedAt||Date.now()-run.armedAt>10000)return;
 const [active]=await chrome.tabs.query({active:true,lastFocusedWindow:true});if(active?.id!==run.tab)return;
 try{
  const url=new URL(item.url);const ref=new URL(item.referrer||'https://invalid.example/');
  if(ref.hostname!=='mail.google.com'||url.protocol!=='https:'||!(url.hostname==='mail.google.com'||url.hostname.endsWith('.googleusercontent.com')))return;
  if(!/\.pdf(?:$|[?#])/i.test(item.filename||'')&&item.mime!=='application/pdf')return;
  await stop();await chrome.storage.local.set({status:'Đang chuyển PDF về tool...'});
  const response=await fetch(url.href,{credentials:'include'});if(!response.ok)throw Error('Không đọc lại được file tải xuống. Chọn PDF bằng tay trong tiện ích.');
  const length=Number(response.headers.get('content-length'));if(length>20*1024*1024)throw Error('PDF vượt 20 MB.');
  await upload(await response.blob(),(item.filename||'Gmail.pdf').split(/[\\/]/).pop());await chrome.storage.local.set({status:'Đã ghi PDF vào sổ, nguồn PDF tải lên.'});
 }catch(e){await chrome.storage.local.set({status:e.message});}
});
