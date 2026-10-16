'use strict';
const $=id=>document.getElementById(id);
function reportText(events){return (events||[]).map(e=>`${e.time} · ${e.phase} · thư ${e.mail}${e.file?' · '+e.file:''}${e.detail?' · '+e.detail:''}`).join('\n')||'Chưa có báo cáo.';}
async function status(){const data=await chrome.storage.local.get(['base','token','status','report']);$('base').value=data.base||'http://localhost:8080';$('token').value=data.token||'';$('status').textContent=data.status||'Chưa chạy.';$('report').textContent=reportText(data.report);}
async function message(data){const result=await chrome.runtime.sendMessage(data);if(result.error)throw Error(result.error);return result;}
function action(id,fn){$(id).onclick=async()=>{try{await fn();}catch(e){$('status').textContent=e.message;}};}
action('save',async()=>{await message({type:'save',base:$('base').value,token:$('token').value});$('status').textContent='Đã kết nối đúng tool và kiểm tra mã ghép nối.';});
action('start',async()=>{await message({type:'start',limit:20});$('status').textContent='Đang chạy. Bạn có thể đóng cửa sổ nhỏ này để xem Gmail.';});
action('start-one',async()=>{await message({type:'start',limit:1});$('status').textContent='Đang thử 1 thư.';});
action('retry',async()=>{await message({type:'start',retry:true,limit:20});$('status').textContent='Đang thử lại file lỗi trên danh sách Gmail hiện tại.';});
action('stop',async()=>{await message({type:'stop'});$('status').textContent='Đã yêu cầu dừng. Lượt AI đang gửi có thể vẫn phát sinh phí.';});
action('upload',async()=>{const file=$('file').files[0];if(!file)throw Error('Chọn PDF trước.');if(file.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');const bytes=Array.from(new Uint8Array(await file.arrayBuffer()));const result=await message({type:'upload',bytes,name:file.name});$('status').textContent=result.status;});
action('copy-report',async()=>{const data=await chrome.storage.local.get('report');await navigator.clipboard.writeText(reportText(data.report));$('copy-report').textContent='Đã sao chép';});
chrome.storage.onChanged.addListener(changes=>{if(changes.status)$('status').textContent=changes.status.newValue;if(changes.report)$('report').textContent=reportText(changes.report.newValue);});status();
