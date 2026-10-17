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
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && label(node).length>=8;}).map((node, index) => ({node, key:node.getAttribute('data-legacy-thread-id') || node.getAttribute('data-thread-id') || node.getAttribute('data-legacy-message-id') || '', text:label(node), version:node.getAttribute('data-legacy-message-id') || node.getAttribute('data-message-id') || '', index}));
}
function mailRouteKey(listURL) {
 if(location.href===listURL)return '';
 const segment=location.hash.split('/').pop()||'';
 if(!/^[A-Za-z0-9_-]{12,}$/.test(segment))return '';
 const account=location.pathname.match(/\/mail\/u\/(\d+)\//)?.[1]||'0';
 return 'gmail-route:'+account+':'+segment;
}
function pdfTiles() {
 const nodes = [...document.querySelectorAll('.aV3')];
 const counts=new Map();
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return /\.pdf\b/i.test(clean(node.textContent)) && r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && !/drive/i.test(label(node.closest('[role="button"],button')));}).map((node,index) => {const name=clean(node.textContent),occurrence=counts.get(name)||0;counts.set(name,occurrence+1);return {node,name,index,fileKey:JSON.stringify([name,occurrence])};});
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
function downloadButtonDisabled(button) {
 return !button.isConnected||button.hasAttribute('disabled')||button.getAttribute('aria-disabled')==='true'||getComputedStyle(button).pointerEvents==='none';
}
async function clickAndWaitDownload(button,cancelled,mail,file) {
 for(let attempt=1;attempt<=2;attempt++){
  if(cancelled())throw Error('Đã dừng lượt quét.');
  const point=clickPoint(button);
  await send({type:'arm-download'});
  let clicked=false,trusted=false;
  const observe=event=>{if(event.target===button||button.contains(event.target)){clicked=true;trusted=event.isTrusted;}};
  document.addEventListener('click',observe,true);
  try{await send({type:'trusted-click',...point});await pause(100);}
  finally{document.removeEventListener('click',observe,true);}
  if(!clicked)throw Error('Chrome đã gửi thao tác chuột nhưng nút tải không nhận sự kiện click.');
  await trace(attempt===1?'da-bam-tai':'da-bam-lai',mail,file,'Nút nhận click '+(trusted?'thật':'chưa xác nhận')+' tại x='+Math.round(point.x)+', y='+Math.round(point.y));
  try{return await waitDownload(cancelled);}
  catch(error){
   if(attempt===2){
    if(error.message.startsWith('Chrome chưa bắt đầu tải PDF'))throw Error('Chrome chưa bắt đầu tải PDF sau 2 lần bấm. Mở Báo cáo lần chạy để xem từng lần thử.');
    throw error;
   }
   if(!error.message.startsWith('Chrome chưa bắt đầu tải PDF'))throw error;
   await trace('tai-chua-bat-dau',mail,file,'Trình xem '+(viewerOpen()?'còn mở':'đã đóng')+' · nút '+(downloadButtonDisabled(button)?'chưa sẵn sàng':'đang bật'));
   // Let a late Chrome event arrive before trying the same PDF again.
   await pause(3200);
   const state=await send({type:'download-state'});
   if(state.error)throw Error(state.error);
   if(state.result){await trace('tai-den-tre',mail,file,'Chrome bắt đầu tải sau 12 giây');return state.result;}
   if(state.downloadId){await trace('tai-den-tre',mail,file,'Chrome đang tải sau 12 giây');return await waitDownload(cancelled);}
   if(!viewerOpen())throw Error('Trình xem PDF đã đóng trước khi thử tải lại.');
   button=await until(()=>{revealToolbar();const found=downloadControl();return found&&!downloadButtonDisabled(found)?found:null;},6000,cancelled);
   if(!button)throw Error('Nút tải PDF chưa sẵn sàng để thử lại.');
   await trace('thu-lai-tai',mail,file,'Chrome chưa có lượt tải; thử bấm lại nút đang hiển thị');
  }
 }
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
function nextPageButton(){
 for(const node of document.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"]')){
  if(!/^(cũ hơn|thư cũ hơn|older|next page)$/i.test(label(node)))continue;
  const button=node.closest('button,[role="button"],a,[tabindex="0"]');
  if(button&&visible(button)&&!button.disabled&&button.getAttribute('aria-disabled')!=='true')return button;
 }
 return null;
}
async function run(limit,only=[],automatic=false) {
 stopped=false; const current=++epoch, cancelled=()=>stopped||epoch!==current;
 let mails=0, files=0, errors=0, duplicateMails=0, duplicateStreak=0; const faults=[];
 try {
  await trace('bat-dau',0,'','Tiện ích '+(chrome.runtime.getManifest?.().version||'không rõ phiên bản')+' · '+(automatic?'lịch tự động':'chạy tay'));
  const pendingFailures=automatic?(await send({type:'pending-failures'})).failures||[]:[];
  const unvisitedFailureKeys=new Set(pendingFailures.map(item=>item.key));
  let stoppedOnDuplicates=false, page=0, pageLimitReached=false;
  while(page<20 && !cancelled()){
  const rows = await until(() => {
   const found=mailRows();
   if(found.length)return found;
   return automatic&&/không tìm thấy (?:thư|cuộc trò chuyện|cuộc hội thoại) nào|không có (?:kết quả|thư nào|cuộc trò chuyện nào)|no conversations found|no results found|your search did not match/i.test(document.body.innerText)?[]:null;
  },10000,cancelled);
  if (!rows?.length) {
   if(automatic && rows){
    await trace('hoan-tat',0,'','Không có thư PDF trong kết quả tìm kiếm hôm nay');await progress('Đã kiểm tra Gmail hôm nay: không có thư PDF mới.');return;
   }
   throw Error('Không nhận diện được hàng thư Gmail (Gmail đang có '+document.querySelectorAll('.zA').length+' hàng .zA). Tải lại Gmail và mở danh sách thư trước khi chạy.');
  }
  // Row text changes after reading; use a message ID when Gmail exposes it,
  // otherwise the stable thread ID. The PDF tile list still detects additions.
  const listURL=location.href, queue=rows.slice(0, limit).map(row=>({key:row.key,text:row.text,fingerprint:row.version||row.key,index:row.index})).filter(row=>!only.length||only.some(item=>item.key&&row.key?item.key===row.key:item.rowIndex===row.index&&item.text===row.text));
  if(!queue.length)throw Error('Không thấy các thư lỗi trên trang Gmail hiện tại. Mở lại danh sách cũ rồi thử lại.');
  await progress('Đã thấy '+queue.length+' thư ở trang '+(page+1)+'. Đang xử lý lần lượt...');
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
   const key=entry.key||await until(()=>mailRouteKey(listURL),3000,cancelled)||'';
   const identity={key,fingerprint:entry.fingerprint||key};
   unvisitedFailureKeys.delete(key);
   const known=key?await send({type:'mail-state',...identity}):{complete:false,files:[],record:'no-id'};
   await trace('kiem-tra-thu',mails,'',(entry.key?'ID từ danh sách':key?'ID từ URL':'Không có ID ổn định')+' · '+(known.record||'không rõ')+' · '+known.files.length+' PDF ghi nhớ');
   const tiles=await until(() => pdfTiles().length ? pdfTiles() : null,10000,cancelled);
   if(!only.length&&key&&known.complete&&tiles&&tiles.every(item=>known.files.includes(item.fileKey))){
    for(let index=pendingFailures.length-1;index>=0;index--)if(pendingFailures[index].key===key){const failure=pendingFailures[index];await send({type:'clear-failure',key,fileIndex:failure.fileIndex,name:failure.name,fileKey:failure.fileKey});pendingFailures.splice(index,1);}
    duplicateMails++;duplicateStreak++;
    await trace('thu-da-co',mails,'','Đã kiểm tra đủ PDF; liên tiếp '+duplicateStreak+'/2');
    const laterFailure=automatic&&unvisitedFailureKeys.size>0;
    if(duplicateStreak===2&&!laterFailure){await trace('dung-trung',mails,'','Gặp 2 thư đã xử lý liên tiếp');stoppedOnDuplicates=true;}
    else if(duplicateStreak===2){await trace('tiep-file-loi',mails,'','Còn PDF lỗi ở thư phía sau');duplicateStreak=0;}
    if((automatic||position+1<queue.length)&&!await backToList(listURL,cancelled))throw Error('Không trở lại được danh sách thư sau khi kiểm tra thư đã có.');
    if(stoppedOnDuplicates)break;
    continue;
   }
   duplicateStreak=0;
   if(key&&known.complete)await send({type:'mail-incomplete',...identity});
   let mailFailed=false;
   if (!tiles) {errors++;mailFailed=true;faults.push('Thư '+mails+': không thấy PDF');}
   else {
    const attachments=tiles.map(item=>({name:item.name,index:item.index,fileKey:item.fileKey})).filter(item=>!only.length||only.some(failed=>(failed.key?failed.key===key:failed.rowIndex===entry.index&&failed.text===entry.text)&&(failed.fileKey?failed.fileKey===item.fileKey:failed.fileIndex===item.index&&failed.name===item.name)));
    const recordedFiles=new Set(known.files);
    if(!attachments.length&&only.length){errors++;mailFailed=true;faults.push('Thư '+mails+': PDF lỗi trước đó không còn trong thư');}
    for (const attachment of attachments) {
     if (cancelled()) return;
     const fileKey=attachment.fileKey;
     if (key && known.files.includes(fileKey)) {await send({type:'clear-failure',key,fileIndex:attachment.index,name:attachment.name,fileKey});await trace('pdf-da-co',mails,attachment.name,'Đã lưu ở lượt trước, không tải lại');continue;}
     try {
      const tile=pdfTiles().find(item=>item.index===attachment.index && item.name===attachment.name);
      if (!tile) throw Error('Không tìm lại được ô PDF.');
      await progress('Thư '+mails+'/'+queue.length+' · PDF '+(files+1)+' · Mở '+attachment.name);
      await trace('mo-pdf',mails,attachment.name);
      await openTile(tile.node,cancelled);
      if (!await until(viewerOpen,10000,cancelled)) throw Error('PDF chưa mở trong Gmail.');
      const button=await until(()=>{revealToolbar();const found=downloadControl();return found&&!downloadButtonDisabled(found)?found:null;},6000,cancelled);
      if (!button) throw Error('Không thấy nút tải PDF đã sẵn sàng trong trình xem.');
      const point=clickPoint(button);
      await trace('tim-nut-tai',mails,attachment.name,'Nút '+button.tagName.toLowerCase()+' · '+(label(button)||'không có nhãn')+' · x='+Math.round(point.x)+', y='+Math.round(point.y));
      const result=await clickAndWaitDownload(button,cancelled,mails,attachment.name);
      if (key) await send({type:'pdf-record',...identity,fileKey});
      await send({type:'clear-failure',key,fileIndex:attachment.index,name:attachment.name,fileKey});
      for(let index=pendingFailures.length-1;index>=0;index--)if(pendingFailures[index].key===key&&(pendingFailures[index].fileKey?pendingFailures[index].fileKey===fileKey:pendingFailures[index].fileIndex===attachment.index&&pendingFailures[index].name===attachment.name))pendingFailures.splice(index,1);
      recordedFiles.add(fileKey);
      files++;await trace('da-luu',mails,attachment.name,result.added===0?'đã có trong sổ':'mới');
      await progress('Đã xử lý '+files+' PDF từ '+mails+' thư. Mới nhất: '+result.filename+(result.added===0?' (đã có trong Sổ ghi chép → AI thao tác, không tạo dòng mới)':' (xem tại Sổ ghi chép → AI thao tác)'));
     } catch (error) {errors++;mailFailed=true;faults.push(attachment.name+': '+error.message);await send({type:'failure',failure:{rowIndex:entry.index,key,text:entry.text,fileIndex:attachment.index,name:attachment.name,fileKey}}).catch(()=>{});await trace('loi',mails,attachment.name,error.message);await progress('Bỏ qua PDF lỗi, tiếp tục file sau: '+attachment.name+' — '+error.message);}
     await closeViewer(cancelled,mails,attachment.name);
    }
    if(key && !mailFailed && tiles.every(item=>recordedFiles.has(item.fileKey))) await send({type:'mail-complete',...identity});
   }
   if (cancelled()) return;
   if ((automatic||position+1<queue.length) && !await backToList(listURL,cancelled)) throw Error('Không trở lại được danh sách thư. Đã lưu '+files+' PDF.');
  }
  if(stoppedOnDuplicates||!automatic)break;
  const next=nextPageButton();if(!next)break;
  if(page===19){pageLimitReached=true;break;}
  const previousFirst=rows[0].key||rows[0].text,previousURL=location.href;
  await trace('trang-tiep',mails,'','Đang mở trang Gmail '+(page+2));
  await send({type:'trusted-click',...clickPoint(next)});
  if(!await until(()=>{const first=mailRows()[0];return first&&((first.key||first.text)!==previousFirst||location.href!==previousURL);},10000,cancelled))throw Error('Gmail chưa chuyển sang trang thư tiếp theo.');
  page++;
  }
  if(pageLimitReached){await trace('gioi-han',mails,'','Đã quét 20 trang; còn trang khác cần xem lại');}
  await trace('hoan-tat',mails,'',files+' PDF đã lưu, '+duplicateMails+' thư đã có, '+errors+' lỗi');
  await progress('Hoàn tất: '+mails+' thư mở, '+files+' PDF đã lưu, '+duplicateMails+' thư đã có, '+errors+' lỗi.'+(pageLimitReached?'\nĐã chạm giới hạn 20 trang Gmail; kiểm tra báo cáo.':'')+(faults.length?'\nXem Báo cáo lần chạy trong tiện ích để biết từng file lỗi.':''));
 } catch (error) {await trace('dung',mails,'',error.message);await progress('Đã lưu '+files+' PDF từ '+mails+' thư. Dừng: '+error.message+'\nMở Báo cáo lần chạy trong tiện ích.').catch(()=>{});}
 finally {if(epoch===current){stopped=true;await send({type:'finish'}).catch(()=>{});}}
}
chrome.runtime.onMessage.addListener(message=>{if(message.type==='run')run(message.limit===1?1:message.limit===100?100:20,message.only||[],message.automatic===true);if(message.type==='stop'){stopped=true;epoch++;}});
}
