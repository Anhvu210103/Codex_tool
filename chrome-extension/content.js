'use strict';
if (!globalThis.mailnotesPilotInstalled) {
globalThis.mailnotesPilotInstalled = true;
let stopped = true, epoch = 0;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
const clean = value => String(value || '').normalize('NFC').trim().replace(/\s+/g, ' ');
const downloadName = /download|tải xuống|tải về/i;
const dangerous = /compose|soạn thư|send|gửi|delete|xóa|archive|lưu trữ|spam|reply|trả lời|forward|chuyển tiếp/i;
async function send(data) { const answer = await chrome.runtime.sendMessage(data); if (answer?.error) throw Error(answer.error); return answer; }
function label(node) { return clean(node?.getAttribute('aria-label') || node?.getAttribute('data-tooltip') || node?.getAttribute('title') || node?.innerText); }
function visible(node) {
 if (!node?.isConnected) return false;
 const r = node.getBoundingClientRect();
 if (r.width < 10 || r.height < 10 || r.bottom <= 0 || r.top >= innerHeight || r.right <= 0 || r.left >= innerWidth || getComputedStyle(node).visibility === 'hidden') return false;
 const top = document.elementFromPoint(Math.min(innerWidth-1, Math.max(0, r.left+r.width/2)), Math.min(innerHeight-1, Math.max(0, r.top+r.height/2)));
 return !!top && (node === top || node.contains(top));
}
function viewerOpen() {
 return [...document.querySelectorAll('[aria-label],[role="status"]')].some(node => visible(node) && /đang hiển thị người xem|showing viewer|trang\s*\d+\s*\/\s*\d+|page\s*\d+\s*(?:of|\/)/i.test(label(node)));
}
function mailRows() {
 const nodes = [...document.querySelectorAll('.zA')];
 if (!nodes.length) nodes.push(...document.querySelectorAll('[role="row"][data-thread-id],[role="row"][data-legacy-thread-id],[role="row"][data-legacy-message-id]'));
 // Subjects and snippets can legitimately say "gửi", "forward" or "archive".
 // Reject dangerous controls at click selection, not entire email rows.
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && label(node).length>=8;}).map((node, index) => ({node, key:node.getAttribute('data-legacy-thread-id') || node.getAttribute('data-thread-id') || node.getAttribute('data-legacy-message-id') || '', text:label(node), index}));
}
function pdfTiles() {
 const nodes = [...document.querySelectorAll('.aV3')];
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return /\.pdf\b/i.test(clean(node.textContent)) && r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && !/drive/i.test(label(node.closest('[role="button"],button')));}).map((node,index) => ({node, name:clean(node.textContent), index}));
}
function tileReady(node) {
 if (!node?.isConnected || viewerOpen()) return {ok:false, reason:'PDF không còn trong thư hoặc đang mở trình xem'};
 const r=node.getBoundingClientRect(),css=getComputedStyle(node);
 if (r.width<10||r.height<10||css.visibility==='hidden'||css.display==='none') return {ok:false,reason:'Ô PDF đang ẩn hoặc chưa nạp'};
 if (r.bottom<=0||r.top>=innerHeight||r.right<=0||r.left>=innerWidth) return {ok:false,reason:'Ô PDF nằm ngoài vùng nhìn thấy sau khi cuộn'};
 const tile=node.closest('.aZo,.aQH');
 const points=[[.5,.5],[.2,.5],[.8,.5],[.5,.2],[.5,.8]];
 let blocking='không xác định';
 for(const [fx,fy] of points){
  const x=Math.min(innerWidth-1,Math.max(0,r.left+r.width*fx)),y=Math.min(innerHeight-1,Math.max(0,r.top+r.height*fy));
  const hit=document.elementFromPoint(x,y);
  if(hit&&(node===hit||node.contains(hit)||tile?.contains(hit)))return {ok:true};
  if(hit)blocking=hit.tagName.toLowerCase()+'.'+String(hit.className?.baseVal||hit.className||'').split(/\s+/).slice(0,2).join('.').slice(0,70);
 }
 return {ok:false,reason:'Ô PDF bị phần tử '+blocking+' che ở mọi điểm kiểm tra'};
}
async function openTile(node,cancelled) {
 let check;
 for(let i=0;i<5&&!cancelled();i++){
  node.scrollIntoView({block:'center'});
  await pause(250);
  check=tileReady(node);
  if(check.ok){node.click();return;}
 }
 throw Error(check?.reason||'Không xác định được ô PDF.');
}
async function trace(phase,mail,file,detail='') {
 await send({type:'trace',event:{phase,mail,file:clean(file).slice(0,180),detail:clean(detail).slice(0,180)}}).catch(()=>{});
}
async function until(get, ms, cancelled) {
 const deadline = Date.now() + ms;
 while (!cancelled()) { const value = get(); if (value) return value; if (Date.now() >= deadline) break; await pause(300); }
 return null;
}
async function progress(text) { await send({type:'progress', text}); }
function revealToolbar() {
 // The viewer may reveal controls only when the pointer moves over its header.
 for (const [x,y] of [[innerWidth/2,innerHeight/2],[innerWidth/2,25],[innerWidth-65,30]]) {
  const node = document.elementFromPoint(x,y); if (!node) continue;
  for (const type of ['mouseover','mousemove']) node.dispatchEvent(new MouseEvent(type,{bubbles:true,view:window,clientX:x,clientY:y}));
 }
}
function controlAt(x,y) {
 let node = document.elementFromPoint(x,y);
 while (node && node !== document.body) {
  if (node.matches('button,[role="button"],a,[tabindex="0"]') && visible(node)) return node;
  node = node.parentElement;
 }
 return null;
}
function downloadControl() {
 if (!viewerOpen()) return null;
 // Gmail can expose other visible "Tải xuống" controls behind the PDF
 // overlay. Only the viewer's compact, top-right toolbar can download
 // the PDF currently open.
 const inViewerHeader = button => {
  const r = button.getBoundingClientRect();
  return r.top >= 0 && r.bottom <= 80 && r.width >= 20 && r.width <= 80 &&
   r.right >= innerWidth - 160 && r.left >= innerWidth - 220;
 };
 const candidates = [...document.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"]')]
  .filter(node => visible(node) && downloadName.test(label(node)) && !/drive|tất cả|all attachments/i.test(label(node)) && !dangerous.test(label(node)));
 if (candidates.length) {
  // A tooltip can carry the text but not the click handler. Prefer its
  // associated button, and never click the tooltip itself.
  for (const node of candidates) {
   const button = node.closest('button,[role="button"],a,[tabindex="0"]');
   if (button && visible(button) && inViewerHeader(button)) return button;
  }
 }
 // Gmail's PDF viewer can render icon-only controls. In its header, the
 // download button sits between Print and More. Verify the Print neighbour.
 const print = controlAt(innerWidth-115,29), target = controlAt(innerWidth-65,29), more = controlAt(innerWidth-19,29);
 const printText = label(print), targetText=label(target);
 const aligned=[print,target,more].every(node=>{if(!node)return false;const r=node.getBoundingClientRect();return r.top>=0&&r.bottom<=65&&r.width>=20&&r.width<=64;});
 // The user's Gmail viewer has three adjacent toolbar buttons at these
 // positions: Print, Download, More. Accept an icon-only Print button only
 // when the whole three-button layout matches; never click More or Print.
 if (aligned && print !== target && target !== more && print !== more &&
     (!printText || /^(print|in)(?:\b|$)/i.test(printText)) &&
     !dangerous.test(targetText) && !/drive|print|^in$|more|thêm|khác/i.test(targetText)) return target;
 return null;
}
async function waitDownload(cancelled) {
 const started=Date.now(), deadline=started+120000;let reported=-1;
 while (!cancelled() && Date.now()<deadline) {
  const elapsed=Math.floor((Date.now()-started)/5000);
  if(elapsed!==reported){reported=elapsed;await progress('Đang chờ Chrome tải PDF và tool lưu vào sổ... '+(elapsed*5)+' giây');}
  const state = await send({type:'download-state'});
  if (state.error) throw Error(state.error);
  if (state.result) return state.result;
  if (!state.downloadId && Date.now()-started>=12000) throw Error('Chrome chưa bắt đầu tải PDF sau 12 giây. Mở Báo cáo lần chạy để xem nút đã bấm và phản hồi của Chrome.');
  await pause(500);
 }
 throw Error('Chưa nhận được PDF từ Chrome trong 2 phút.');
}
function clickPoint(button) {
 const r=button.getBoundingClientRect();
 const x=Math.min(innerWidth-1,Math.max(0,r.left+r.width/2));
 const y=Math.min(innerHeight-1,Math.max(0,r.top+r.height/2));
 const hit=document.elementFromPoint(x,y);
 if (!hit || !(button===hit || button.contains(hit))) throw Error('Nút tải PDF bị che hoặc đã đổi vị trí.');
 return {x,y};
}
async function closeViewer(cancelled,mail,file) {
 if (!viewerOpen()) return;
 const close = [...document.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"]')]
  .find(node => visible(node) && /^(đóng|close)(?:\b|$)/i.test(label(node)));
 if (close) {
  try {
   await send({type:'trusted-click',...clickPoint(close)});
   await trace('dong-pdf',mail,file,'Đã bấm nút đóng bằng chuột Chrome');
   if (await until(() => !viewerOpen(),2000,cancelled)) return;
  } catch (error) {await trace('dong-pdf-loi',mail,file,error.message);}
 }
 if (cancelled()) return;
 await trace('dong-pdf-esc',mail,file,close?'Nút đóng chưa đóng trình xem':'Không thấy nút đóng');
 await send({type:'trusted-escape'});
 if (!await until(() => !viewerOpen(),4000,cancelled)) throw Error('Trình xem PDF chưa đóng sau khi bấm nút Đóng và phím Esc.');
}
async function backToList(listURL,cancelled) {
 if (mailRows().some(item=>visible(item.node))) return true;
 const back = [...document.querySelectorAll('[aria-label],[data-tooltip],[title],[role="button"]')]
  .find(node => visible(node) && /quay lại|\bback\b/i.test(label(node)) && !dangerous.test(label(node)));
 if (back) {
  await send({type:'trusted-click',...clickPoint(back)});
  if (await until(() => mailRows().some(item=>visible(item.node)),4000,cancelled)) return true;
 }
 if (location.href === listURL || cancelled()) return false;
 history.back();
 return !!await until(() => mailRows().some(item=>visible(item.node)),7000,cancelled);
}
async function run(limit,only=[]) {
 stopped=false; const current=++epoch, cancelled=()=>stopped||epoch!==current;
 let mails=0, files=0, errors=0; const faults=[];
 try {
  const rows = await until(() => mailRows().length ? mailRows() : null,10000,cancelled);
  if (!rows) throw Error('Không nhận diện được hàng thư Gmail (Gmail đang có '+document.querySelectorAll('.zA').length+' hàng .zA). Tải lại Gmail và mở danh sách thư trước khi chạy.');
  const listURL=location.href, queue=rows.slice(0, limit).map(row=>({key:row.key,text:row.text,index:row.index})).filter(row=>!only.length||only.some(item=>item.key?item.key===row.key:item.rowIndex===row.index&&item.text===row.text));
  if(!queue.length)throw Error('Không thấy các thư lỗi trên trang Gmail hiện tại. Mở lại danh sách cũ rồi thử lại.');
  await progress('Đã thấy '+queue.length+' thư trên trang. Đang xử lý lần lượt...');
  for (let position=0;position<queue.length;position++) {
   const entry=queue[position];
   if (cancelled()) return;
   const currentRows=mailRows();
   const row=entry.key ? currentRows.find(item=>item.key===entry.key) :
    currentRows.find(item=>item.index===entry.index && item.text===entry.text) || currentRows.find(item=>item.text===entry.text);
   if (!row) { errors++; faults.push('Không tìm lại được thư '+(entry.index+1)); continue; }
   row.node.scrollIntoView({block:'center'});
   if (!visible(row.node)) {errors++;faults.push('Thư '+(entry.index+1)+': không hiển thị sau khi cuộn');continue;}
   row.node.click(); mails++;await trace('mo-thu',mails,'');
   const tiles=await until(() => pdfTiles().length ? pdfTiles() : null,10000,cancelled);
   if (!tiles) {errors++;faults.push('Thư '+mails+': không thấy PDF');}
   else {
    const attachments=tiles.map(item=>({name:item.name,index:item.index})).filter(item=>!only.length||only.some(failed=>(failed.key?failed.key===entry.key:failed.rowIndex===entry.index&&failed.text===entry.text)&&failed.fileIndex===item.index&&failed.name===item.name));
    if(!attachments.length&&only.length){errors++;faults.push('Thư '+mails+': PDF lỗi trước đó không còn trong thư');}
    for (const attachment of attachments) {
     if (cancelled()) return;
     try {
      const tile=pdfTiles().find(item=>item.index===attachment.index && item.name===attachment.name);
      if (!tile) throw Error('Không tìm lại được ô PDF.');
      await progress('Thư '+mails+'/'+queue.length+' · PDF '+(files+1)+' · Mở '+attachment.name);
      await trace('mo-pdf',mails,attachment.name);
      await openTile(tile.node,cancelled);
      if (!await until(viewerOpen,10000,cancelled)) throw Error('PDF chưa mở trong Gmail.');
      let button=null;
      for (let i=0;i<20 && !cancelled();i++) {revealToolbar();button=downloadControl();if(button)break;await pause(300);}
      if (!button) throw Error('Không thấy nút tải trong trình xem PDF.');
      const point=clickPoint(button);
      await trace('tim-nut-tai',mails,attachment.name,'Nút '+button.tagName.toLowerCase()+' · '+(label(button)||'không có nhãn')+' · x='+Math.round(point.x)+', y='+Math.round(point.y));
      await send({type:'arm-download'});
      let clicked=false;
      const observe=event=>{if(event.target===button||button.contains(event.target))clicked=true;};
      document.addEventListener('click',observe,true);
      try {await send({type:'trusted-click',...point});await pause(100);}
      finally {document.removeEventListener('click',observe,true);}
      if (!clicked) throw Error('Chrome đã gửi thao tác chuột nhưng nút tải không nhận sự kiện click.');
      await trace('da-bam-tai',mails,attachment.name,'Gmail đã nhận click tại x='+Math.round(point.x)+', y='+Math.round(point.y));
      const result=await waitDownload(cancelled);
      files++;await trace('da-luu',mails,attachment.name,result.added===0?'đã có trong sổ':'mới');
      await progress('Đã xử lý '+files+' PDF từ '+mails+' thư. Mới nhất: '+result.filename+(result.added===0?' (đã có trong Sổ ghi chép → AI thao tác, không tạo dòng mới)':' (xem tại Sổ ghi chép → AI thao tác)'));
     } catch (error) {errors++;faults.push(attachment.name+': '+error.message);await send({type:'failure',failure:{rowIndex:entry.index,key:entry.key,text:entry.text,fileIndex:attachment.index,name:attachment.name}}).catch(()=>{});await trace('loi',mails,attachment.name,error.message);await progress('Bỏ qua PDF lỗi, tiếp tục file sau: '+attachment.name+' — '+error.message);}
     await closeViewer(cancelled,mails,attachment.name);
    }
   }
   if (cancelled()) return;
   if (position+1<queue.length && !await backToList(listURL,cancelled)) throw Error('Không trở lại được danh sách thư. Đã lưu '+files+' PDF.');
  }
  await trace('hoan-tat',mails,'',files+' PDF đã lưu, '+errors+' lỗi');
  await progress('Hoàn tất: '+mails+' thư, '+files+' PDF đã lưu, '+errors+' lỗi.'+(faults.length?'\nXem Báo cáo lần chạy trong tiện ích để biết từng file lỗi.':''));
 } catch (error) {await trace('dung',mails,'',error.message);await progress('Đã lưu '+files+' PDF từ '+mails+' thư. Dừng: '+error.message+'\nMở Báo cáo lần chạy trong tiện ích.').catch(()=>{});}
 finally {if(epoch===current){stopped=true;await send({type:'finish'}).catch(()=>{});}}
}
chrome.runtime.onMessage.addListener(message=>{if(message.type==='run')run(message.limit===1?1:20,message.only||[]);if(message.type==='stop'){stopped=true;epoch++;}});
}
