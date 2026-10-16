'use strict';
const $=id=>document.getElementById(id);
async function status(){const data=await chrome.storage.local.get(['base','token','status']);$('base').value=data.base||'http://localhost:8080';$('token').value=data.token||'';$('status').textContent=data.status||'Chưa chạy.';}
async function message(data){const result=await chrome.runtime.sendMessage(data);if(result.error)throw Error(result.error);return result;}
function action(id,fn){$(id).onclick=async()=>{try{await fn();}catch(e){$('status').textContent=e.message;}};}
action('save',async()=>{await message({type:'save',base:$('base').value,token:$('token').value});$('status').textContent='Đã kết nối đúng tool và kiểm tra mã ghép nối.';});
action('start',async()=>{await message({type:'start'});$('status').textContent='Đang chạy. Bạn có thể đóng cửa sổ nhỏ này để xem Gmail.';});
action('stop',async()=>{await message({type:'stop'});$('status').textContent='Đã yêu cầu dừng. Lượt AI đang gửi có thể vẫn phát sinh phí.';});
action('upload',async()=>{const file=$('file').files[0];if(!file)throw Error('Chọn PDF trước.');if(file.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');const bytes=Array.from(new Uint8Array(await file.arrayBuffer()));const result=await message({type:'upload',bytes,name:file.name});$('status').textContent=result.status;});
chrome.storage.onChanged.addListener(changes=>{if(changes.status)$('status').textContent=changes.status.newValue;});status();
