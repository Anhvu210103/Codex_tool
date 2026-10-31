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
function viewerMarker() {
 return [...document.querySelectorAll('[aria-label],[role="status"]')].find(node => visible(node) && /đang hiển thị người xem|showing viewer|trang\s*\d+\s*\/\s*\d+|page\s*\d+\s*(?:of|\/)/i.test(label(node)));
}
function viewerOpen() { return !!viewerMarker(); }
function shortHash(value){let hash=2166136261;for(let i=0;i<value.length;i++){hash^=value.charCodeAt(i);hash=Math.imul(hash,16777619);}return (hash>>>0).toString(16).padStart(8,'0');}
function mailNodeIdentity(node){
 const metadata=node.matches('[data-legacy-thread-id],[data-thread-id],[data-legacy-message-id],[data-message-id]')?node:node.querySelector('[data-legacy-thread-id],[data-thread-id],[data-legacy-message-id],[data-message-id]');
 const thread=metadata?.getAttribute('data-legacy-thread-id')||metadata?.getAttribute('data-thread-id')||node.getAttribute('data-legacy-thread-id')||node.getAttribute('data-thread-id')||'';
 const message=metadata?.getAttribute('data-legacy-message-id')||metadata?.getAttribute('data-message-id')||node.getAttribute('data-legacy-message-id')||node.getAttribute('data-message-id')||'';
 if(thread||message)return {key:thread||message,version:message};
 for(const anchor of node.querySelectorAll('a[href]')){const segment=(anchor.getAttribute('href')||'').split('/').pop();if(/^[A-Za-z0-9_-]{12,}$/.test(segment))return {key:'gmail-link:'+segment,version:''};}
 const sender=clean(node.querySelector('.yP[email],.zF[email],[email]')?.getAttribute('email')||node.querySelector('.yP,.zF')?.textContent);
 const subject=clean(node.querySelector('.bog')?.textContent);
 const dateNode=node.querySelector('.xW [title],.xW');const received=clean(dateNode?.getAttribute('title')||dateNode?.textContent);
 if(subject&&(sender||received)){const stable=JSON.stringify([sender,subject,received]);return {key:'gmail-row:'+shortHash(stable)+':'+subject.slice(0,80),version:''};}
 return {key:'',version:''};
}
function mailRows() {
 const nodes = [...document.querySelectorAll('.zA')];
 if (!nodes.length) nodes.push(...document.querySelectorAll('[role="row"][data-thread-id],[role="row"][data-legacy-thread-id],[role="row"][data-legacy-message-id]'));
 // Subjects and snippets can legitimately say "gửi", "forward" or "archive".
 // Reject dangerous controls at click selection, not entire email rows.
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && label(node).length>=8;}).map((node, index) => ({node,...mailNodeIdentity(node),text:label(node),index}));
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
 return nodes.filter(node => {const r=node.getBoundingClientRect(),css=getComputedStyle(node);return /\.pdf\b/i.test(clean(node.textContent)) && r.width>=10 && r.height>=10 && css.visibility!=='hidden' && css.display!=='none' && !/drive/i.test(label(node.closest('[role="button"],button')));}).map((node,index) => {
  const name=clean(node.textContent),occurrence=counts.get(name)||0;counts.set(name,occurrence+1);
  const metadata=node.closest('[data-attachment-id],[data-message-id],[data-id],a[href]');
  const stable=metadata?.getAttribute('data-attachment-id')||metadata?.getAttribute('data-message-id')||metadata?.getAttribute('data-id')||metadata?.getAttribute('href')||'';
  return {node,name,index,legacyKey:JSON.stringify([name,occurrence]),fileKey:stable?'gmail:'+stable:JSON.stringify([name,occurrence])};
 });
}
async function stablePdfTiles(cancelled) {
 let previous='',stable=0;
 for(let attempt=0;attempt<20&&!cancelled();attempt++){
  const tiles=pdfTiles(),signature=tiles.map(item=>item.fileKey+'\u0000'+item.name).join('\u0001');
  if(tiles.length&&signature===previous)stable++;else stable=0;
  if(stable>=2)return tiles;
  previous=signature;await pause(300);
 }
 return null;
}
function recorded(files,item){return files.includes(item.fileKey)||files.includes(item.legacyKey);}
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
function revealTile(node) {
 const r=node.getBoundingClientRect();
 const x=Math.min(innerWidth-1,Math.max(0,r.left+r.width/2));
 const y=Math.min(innerHeight-1,Math.max(0,r.top+r.height/2));
 for(const type of ['mouseover','mouseenter','mousemove'])node.dispatchEvent(new MouseEvent(type,{bubbles:true,view:window,clientX:x,clientY:y}));
}
function directDownloadControl(node,name) {
 if(!node?.isConnected||viewerOpen())return null;
 // .aZo is one Gmail attachment card. Fall back to .aQH for layouts where
 // Gmail wraps the card differently, but never search the whole message.
 const card=node.closest('.aZo')||node.closest('.aQH');
 if(card)revealTile(card);
 const candidates=new Map();
 const scope=card||document;
 for(const item of scope.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"],a')){
  const names=[item.getAttribute('aria-label'),item.getAttribute('data-tooltip'),item.getAttribute('title'),item.innerText].map(clean);
  if(!names.some(value=>downloadName.test(value))||names.some(value=>/drive|tất cả|all attachments/i.test(value)))continue;
  if(!card&&!names.some(value=>value.normalize('NFC').includes(clean(name).normalize('NFC'))))continue;
  const button=item.closest('button,[role="button"],a,[tabindex="0"]')||item;
  if(visible(button)&&!downloadButtonDisabled(button))candidates.set(button,[...(candidates.get(button)||[]),...names]);
 }
 const unique=[...candidates.keys()];
 if(unique.length===1)return unique[0];
 // When Gmail exposes more than one card action, require the filename in its
 // accessible label so the tool cannot download a neighbouring attachment.
 const expected=clean(name).normalize('NFC');
 const named=unique.filter(button=>candidates.get(button).some(value=>value.normalize('NFC').includes(expected)));
 return named.length===1?named[0]:null;
}
async function readyDirectDownload(node,name,cancelled) {
 node.scrollIntoView({block:'center'});
 const card=node.closest('.aZo')||node.closest('.aQH')||node,r=card.getBoundingClientRect();
 await send({type:'trusted-move',x:Math.min(innerWidth-1,Math.max(0,r.left+r.width/2)),y:Math.min(innerHeight-1,Math.max(0,r.top+r.height/2))});
 return await until(()=>{revealTile(node);return directDownloadControl(node,name);},3000,cancelled);
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
function viewerHeaderControl(button) {
 const r=button.getBoundingClientRect();
 // Use the actual viewer/dialog bounds. Browser zoom, window width and Gmail
 // toolbar spacing must not force the download icon into a fixed 160px strip.
 const dialog=viewerMarker()?.closest('[role="dialog"]');
 if(dialog&&!dialog.contains(button))return false;
 const frame=dialog?.getBoundingClientRect();
 const top=frame?.top||0, width=frame?.width||innerWidth;
 return r.width>=10 && r.height>=10 && r.width<=Math.max(240,width*.4) &&
  r.top>=Math.max(0,top) && r.bottom<=Math.max(0,top)+Math.min(220,innerHeight*.35);
}
function downloadCandidates() {
 const found=new Set();
 for(const node of document.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"]')){
  // Check each accessible name: an unrelated aria-label must not hide a
  // correctly named tooltip, and nested icon labels belong to their button.
  const names=[node.getAttribute('aria-label'),node.getAttribute('data-tooltip'),node.getAttribute('title'),node.innerText].map(clean);
  if(!names.some(name=>downloadName.test(name)))continue;
  const button=node.closest('button,[role="button"],a,[tabindex="0"]');
  if(button)found.add(button);
 }
 return [...found];
}
function downloadControl() {
 if(!viewerOpen())return null;
 const safe=button=>!dangerous.test(label(button))&&!/drive|tất cả|all attachments/i.test(label(button));
 const named=downloadCandidates().filter(button=>visible(button)&&viewerHeaderControl(button)&&safe(button)&&!downloadButtonDisabled(button));
 // Fail closed on ambiguity rather than download the wrong attachment.
 if(named.length===1)return named[0];
 if(named.length>1)return null;
 // Icon-only fallback requires semantic Print and More neighbours, never a
 // guessed screen coordinate. Resizing/reordered toolbars stay supported.
 const controls=[...document.querySelectorAll('button,[role="button"],a[tabindex],div[tabindex="0"]')]
  .filter(button=>visible(button)&&viewerHeaderControl(button));
 const prints=controls.filter(button=>/^(print|in)(?:\b|$)/i.test(label(button)));
 const more=controls.filter(button=>/more|thêm|khác/i.test(label(button)));
 const matches=new Set();
 for(const print of prints)for(const end of more){
  const pr=print.getBoundingClientRect(),er=end.getBoundingClientRect();
  if(er.left<=pr.right||Math.abs(er.top-pr.top)>12)continue;
  const between=controls.filter(button=>{
   const r=button.getBoundingClientRect();
   return button!==print&&button!==end&&r.left>=pr.right&&r.right<=er.left&&Math.abs(r.top-pr.top)<=12&&r.width<=80;
  });
  if(between.length===1&&!label(between[0])&&safe(between[0])&&!downloadButtonDisabled(between[0]))matches.add(between[0]);
 }
 return matches.size===1?[...matches][0]:null;
}
async function readyDownload(cancelled,mail,file) {
 const button=await until(()=>{revealToolbar();return downloadControl();},12000,cancelled);
 if(button||cancelled())return button;
 await trace('chan-doan-tai',mail,file,'viewer='+viewerOpen()+' · màn hình '+innerWidth+'x'+innerHeight+' · '+downloadCandidates().length+' nút có nhãn tải');
 for(const node of downloadCandidates().slice(0,6)){
  const r=node.getBoundingClientRect();
  await trace('nut-tai-bi-loai',mail,file,(label(node)||'không nhãn').slice(0,65)+' · x='+Math.round(r.x)+',y='+Math.round(r.y)+',w='+Math.round(r.width)+',h='+Math.round(r.height)+' · thấy='+visible(node)+' · header='+viewerHeaderControl(node)+' · tắt='+downloadButtonDisabled(node));
 }
 if(!downloadCandidates().length){
  const labels=[...document.querySelectorAll('button,[role="button"],[aria-label]')].filter(node=>visible(node)&&viewerHeaderControl(node)).map(label).filter(Boolean);
  await trace('toolbar-pdf',mail,file,labels.slice(0,8).join(' | '));
 }
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
  if (!state.downloadId && Date.now()-started>=30000) throw Error('Chrome chưa bắt đầu tải PDF sau 30 giây. Mở Báo cáo lần chạy để xem nút đã bấm và phản hồi của Chrome.');
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
  await send({type:'arm-download',name:file});
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
   if(state.result){await trace('tai-den-tre',mail,file,'Chrome bắt đầu tải sau thời gian chờ đầu tiên');return state.result;}
   if(state.downloadId){await trace('tai-den-tre',mail,file,'Chrome đang tải sau thời gian chờ đầu tiên');return await waitDownload(cancelled);}
   if(!viewerOpen())throw Error('Trình xem PDF đã đóng trước khi thử tải lại.');
   button=await readyDownload(cancelled,mail,file);
   if(!button)throw Error('Nút tải PDF chưa sẵn sàng để thử lại.');
   await trace('thu-lai-tai',mail,file,'Chrome chưa có lượt tải; thử bấm lại nút đang hiển thị');
  }
 }
}
async function clickAndWaitDirect(button,cancelled,mail,file) {
 const point=clickPoint(button);
 await send({type:'arm-download',name:file});
 await send({type:'trusted-click',...point});
 await trace('bam-tai-truc-tiep',mail,file,'Bấm nút tải trên thẻ đính kèm tại x='+Math.round(point.x)+', y='+Math.round(point.y));
 return await waitDownload(cancelled);
}
async function closeViewer(cancelled,mail,file) {
 if (!viewerOpen()) return;
 const dialog=viewerMarker()?.closest('[role="dialog"]');
 const close = [...new Set([...document.querySelectorAll('[aria-label],[data-tooltip],[title],button,[role="button"]')]
  .filter(node => visible(node) && /^(đóng|close)(?:\b|$)/i.test(label(node)))
  .map(node => node.closest('button,[role="button"],a,[tabindex="0"]') || node))]
  .filter(node => !dialog || dialog.contains(node))
  .sort((left,right) => {
   const a=left.getBoundingClientRect(),b=right.getBoundingClientRect();
   return (a.top+a.left)-(b.top+b.left);
  })[0];
 if (close) {
  try {
   const point=clickPoint(close);
   // Gmail's overlay can ignore a coordinate click while its download bubble
   // owns focus. Invoke the identified Close control first, then use a real
   // Chrome click as fallback.
   close.click();
   if (await until(() => !viewerOpen(),1200,cancelled)) {await trace('dong-pdf',mail,file,'Đã đóng bằng điều khiển Gmail');return;}
   await send({type:'trusted-click',...point});
   await trace('dong-pdf',mail,file,'Đã bấm '+(label(close)||'nút đóng')+' tại x='+Math.round(point.x)+', y='+Math.round(point.y));
   if (await until(() => !viewerOpen(),3500,cancelled)) return;
  } catch (error) {await trace('dong-pdf-loi',mail,file,error.message);}
 }
 if (cancelled()) return;
 await trace('dong-pdf-esc',mail,file,close?'Nút đóng chưa đóng trình xem':'Không thấy nút đóng');
 await send({type:'trusted-escape'});
 if (!await until(() => !viewerOpen(),4000,cancelled)) throw Error('Trình xem PDF chưa đóng sau khi bấm nút Đóng và phím Esc.');
}
async function restoreMailAfterViewer(mailURL,listURL,cancelled,mail,file) {
 if(!viewerOpen())return true;
 try{await closeViewer(cancelled,mail,file);if(!viewerOpen())return true;}
 catch(error){await trace('phuc-hoi-thu',mail,file,error.message+' · mở lại thư đang xử lý');}
 if(cancelled())return false;
 let mailTarget,listTarget;
 try{mailTarget=new URL(mailURL);listTarget=new URL(listURL);}catch{return false;}
 if(mailTarget.origin!==location.origin||mailTarget.pathname!==location.pathname||!mailTarget.hash||!listTarget.hash||mailTarget.hash===listTarget.hash)return false;
 // Gmail sometimes keeps its PDF overlay mounted even after Close and Escape.
 // Bounce through the saved result list, then reopen the exact message route.
 // This resets the overlay without reloading the tab or losing the active run.
 location.hash=listTarget.hash;
 if(!await until(()=>!viewerOpen()&&mailRows().some(item=>visible(item.node)),10000,cancelled))return false;
 location.hash=mailTarget.hash;
 const restored=await until(()=>!viewerOpen()&&pdfTiles().length>0,12000,cancelled);
 if(restored)await trace('da-phuc-hoi-thu',mail,file,'Đã mở lại thư để xử lý PDF tiếp theo');
 return !!restored;
}
async function backToList(listURL,cancelled) {
 if (mailRows().some(item=>visible(item.node))) return true;
 const back = [...document.querySelectorAll('[aria-label],[data-tooltip],[title],[role="button"]')]
  .find(node => visible(node) && /quay lại|\bback\b/i.test(label(node)) && !dangerous.test(label(node)));
 if (back) {
  try {
   await send({type:'trusted-click',...clickPoint(back)});
   if (await until(() => mailRows().some(item=>visible(item.node)),4000,cancelled)) return true;
  } catch (error) {await trace('quay-lai-loi',0,'',error.message);}
 }
 if (cancelled()) return false;
 const target=new URL(listURL);
 // Gmail is a single-page app. Restore the exact saved search route instead
 // of relying only on the viewer's Close button or browser history.
 if(target.origin===location.origin && target.pathname===location.pathname && target.hash && location.hash!==target.hash){
  await trace('quay-lai-danh-sach',0,'','Khôi phục bộ lọc Gmail đã mở');
  location.hash=target.hash;
  if(await until(() => mailRows().some(item=>visible(item.node)),10000,cancelled))return true;
 }
 if(cancelled())return false;
 if(location.href!==listURL){
  history.back();
  if(await until(() => mailRows().some(item=>visible(item.node)),7000,cancelled))return true;
 }
 // Gmail can show the right URL while its message view remains mounted. A
 // short route bounce forces the saved result list to render again.
 if(!cancelled() && target.hash && location.hash===target.hash){
  await trace('tai-lai-danh-sach',0,'','Đúng URL tìm kiếm nhưng Gmail chưa hiện hàng thư; mở lại bộ lọc');
  location.hash='#all';
  await pause(500);
  location.hash=target.hash;
  if(await until(() => mailRows().some(item=>visible(item.node)),12000,cancelled))return true;
 }
 const empty=/không tìm thấy (?:thư|cuộc trò chuyện|cuộc hội thoại) nào|không có (?:kết quả|thư nào|cuộc trò chuyện nào)|no conversations found|no results found|your search did not match/i.test(document.body.innerText);
 await trace('quay-lai-that-bai',0,'','URL: '+location.hash.slice(0,85)+' · .zA: '+document.querySelectorAll('.zA').length+' · tìm kiếm trống: '+empty);
 return false;
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
 let mails=0, files=0, errors=0, duplicateMails=0, scanSucceeded=false; const faults=[];
 const rememberFailure=async(stage,entry,error,file=null)=>{const failure={stage,rowIndex:entry.index,key:entry.key||'',text:entry.text||'',fileIndex:file?.index??-1,name:file?.name||'',fileKey:file?.fileKey,error:error.message||String(error)};await send({type:'failure',failure}).catch(()=>{});};
 try {
  await trace('bat-dau',0,'','Tiện ích '+(chrome.runtime.getManifest?.().version||'không rõ phiên bản')+' · '+(automatic?'lịch tự động':'chạy tay'));
  const pendingFailures=automatic?(await send({type:'pending-failures'})).failures||[]:[];
  let page=0, pageLimitReached=false;
  while(page<20 && !cancelled()){
  const rows = await until(() => {
   const found=mailRows();
   if(found.length)return found;
   return automatic&&/không tìm thấy (?:thư|cuộc trò chuyện|cuộc hội thoại) nào|không có (?:kết quả|thư nào|cuộc trò chuyện nào)|no conversations found|no results found|your search did not match/i.test(document.body.innerText)?[]:null;
  },10000,cancelled);
  if (!rows?.length) {
   if(automatic && rows){
    await trace('hoan-tat',0,'','Không có thư PDF trong khoảng quét');await progress('Đã kiểm tra Gmail: không có thư PDF mới.');scanSucceeded=true;return;
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
   if (!row) {const error=Error('Không tìm lại được thư '+(entry.index+1));errors++;faults.push(error.message);await rememberFailure('open-mail',entry,error);continue;}
   row.node.scrollIntoView({block:'center'});
   if (!visible(row.node)) {const error=Error('Thư '+(entry.index+1)+': không hiển thị sau khi cuộn');errors++;faults.push(error.message);await rememberFailure('open-mail',entry,error);continue;}
   row.node.click(); mails++;await trace('mo-thu',mails,'');
   const mailURL=await until(()=>location.href!==listURL?location.href:null,4000,cancelled)||location.href;
   const key=entry.key||await until(()=>mailRouteKey(listURL),3000,cancelled)||'';
   const identity={key,fingerprint:entry.fingerprint||key};
   const known=key?await send({type:'mail-state',...identity}):{complete:false,files:[],record:'no-id'};
   await trace('kiem-tra-thu',mails,'',(entry.key?'ID từ danh sách':key?'ID từ URL':'Không có ID ổn định')+' · '+(known.record||'không rõ')+' · '+known.files.length+' PDF ghi nhớ');
   const tiles=await stablePdfTiles(cancelled);
   if(!only.length&&key&&known.complete&&tiles&&tiles.every(item=>recorded(known.files,item))){
    for(let index=pendingFailures.length-1;index>=0;index--)if(pendingFailures[index].key===key){const failure=pendingFailures[index];await send({type:'clear-failure',key,fileIndex:failure.fileIndex,name:failure.name,fileKey:failure.fileKey});pendingFailures.splice(index,1);}
    duplicateMails++;
    await trace('thu-da-co',mails,'','Đã kiểm tra đủ PDF; tiếp tục kiểm tra hết kết quả');
    if((automatic||position+1<queue.length)&&!await backToList(listURL,cancelled))throw Error('Không trở lại được danh sách thư sau khi kiểm tra thư đã có.');
    continue;
   }
   if(key&&known.complete)await send({type:'mail-incomplete',...identity});
   let mailFailed=false;
   if (!tiles) {const error=Error('Thư '+mails+': danh sách PDF chưa ổn định hoặc không thấy PDF');errors++;mailFailed=true;faults.push(error.message);await rememberFailure('list-pdf',{...entry,key},error);await trace('loi-danh-sach-pdf',mails,'',error.message);}
   else {
    const attachments=tiles.map(item=>({name:item.name,index:item.index,fileKey:item.fileKey,legacyKey:item.legacyKey})).filter(item=>!only.length||only.some(failed=>(failed.key?failed.key===key:failed.rowIndex===entry.index&&failed.text===entry.text)&&(failed.fileKey?[item.fileKey,item.legacyKey].includes(failed.fileKey):failed.fileIndex===item.index&&failed.name===item.name)));
    const recordedFiles=new Set(known.files);
    if(!attachments.length&&only.length){errors++;mailFailed=true;faults.push('Thư '+mails+': PDF lỗi trước đó không còn trong thư');}
    for (const attachment of attachments) {
     if (cancelled()) return;
     const fileKey=attachment.fileKey;
     if (key && recorded(known.files,attachment)) {await send({type:'clear-failure',key,fileIndex:attachment.index,name:attachment.name,fileKey});await trace('pdf-da-co',mails,attachment.name,'Đã lưu ở lượt trước, không tải lại');recordedFiles.add(fileKey);continue;}
     try {
      const tile=pdfTiles().find(item=>item.fileKey===attachment.fileKey)||pdfTiles().find(item=>item.index===attachment.index && item.name===attachment.name);
      if (!tile) throw Error('Không tìm lại được ô PDF.');
      await progress('Thư '+mails+'/'+queue.length+' · PDF '+(files+1)+' · Tải '+attachment.name);
      let result=null;
      const direct=await readyDirectDownload(tile.node,attachment.name,cancelled);
      if(direct){
       try{result=await clickAndWaitDirect(direct,cancelled,mails,attachment.name);}
       catch(error){await trace('tai-truc-tiep-loi',mails,attachment.name,error.message+' · chuyển sang trình xem PDF');}
      }
      if(!result){
       await trace('mo-pdf',mails,attachment.name,direct?'Tải trực tiếp chưa bắt đầu':'Thẻ đính kèm không có nút tải trực tiếp');
       await openTile(tile.node,cancelled);
       if (!await until(viewerOpen,10000,cancelled)) throw Error('PDF chưa mở trong Gmail.');
       const button=await readyDownload(cancelled,mails,attachment.name);
       if (!button) throw Error('Không thấy nút tải PDF đã sẵn sàng trong trình xem.');
       const point=clickPoint(button);
       await trace('tim-nut-tai',mails,attachment.name,'Nút '+button.tagName.toLowerCase()+' · '+(label(button)||'không có nhãn')+' · x='+Math.round(point.x)+', y='+Math.round(point.y));
       result=await clickAndWaitDownload(button,cancelled,mails,attachment.name);
      }
      if (key) await send({type:'pdf-record',...identity,fileKey});
      await send({type:'clear-failure',key,fileIndex:attachment.index,name:attachment.name,fileKey});
      for(let index=pendingFailures.length-1;index>=0;index--)if(pendingFailures[index].key===key&&(pendingFailures[index].fileKey?pendingFailures[index].fileKey===fileKey:pendingFailures[index].fileIndex===attachment.index&&pendingFailures[index].name===attachment.name))pendingFailures.splice(index,1);
      recordedFiles.add(fileKey);
      files++;await trace('da-luu',mails,attachment.name,result.added===0?'đã có trong sổ':'mới');
      await progress('Đã xử lý '+files+' PDF từ '+mails+' thư. Mới nhất: '+result.filename+(result.added===0?' (đã có trong Sổ ghi chép → AI thao tác, không tạo dòng mới)':' (xem tại Sổ ghi chép → AI thao tác)'));
     } catch (error) {errors++;mailFailed=true;faults.push(attachment.name+': '+error.message);await rememberFailure('process-pdf',{...entry,key},error,attachment);await trace('loi',mails,attachment.name,error.message);await progress('Bỏ qua PDF lỗi, tiếp tục file sau: '+attachment.name+' — '+error.message);}
     if(viewerOpen()&&!await restoreMailAfterViewer(mailURL,listURL,cancelled,mails,attachment.name)){
      const error=Error('Không đóng hoặc khôi phục được thư sau trình xem PDF.');errors++;mailFailed=true;faults.push(attachment.name+': '+error.message);await rememberFailure('close-viewer',{...entry,key},error,attachment);await trace('loi-dong-pdf',mails,attachment.name,error.message);
      break;
     }
    }
    if(key && !mailFailed && tiles.every(item=>recordedFiles.has(item.fileKey)||recordedFiles.has(item.legacyKey))) await send({type:'mail-complete',...identity});
   }
   if (cancelled()) return;
   if ((automatic||position+1<queue.length) && !await backToList(listURL,cancelled)){const error=Error('Không trở lại được danh sách thư. Đã lưu '+files+' PDF.');await rememberFailure('back-to-list',{...entry,key},error);throw error;}
  }
  if(!automatic)break;
  const next=nextPageButton();if(!next)break;
  if(page===19){pageLimitReached=true;break;}
  const previousFirst=rows[0].key||rows[0].text,previousURL=location.href;
  await trace('trang-tiep',mails,'','Đang mở trang Gmail '+(page+2));
  await send({type:'trusted-click',...clickPoint(next)});
  if(!await until(()=>{const first=mailRows()[0];return first&&((first.key||first.text)!==previousFirst||location.href!==previousURL);},10000,cancelled)){const error=Error('Gmail chưa chuyển sang trang thư tiếp theo.');await rememberFailure('next-page',{index:0,key:'page:'+page,text:previousURL},error);throw error;}
  page++;
  }
  if(pageLimitReached){await trace('gioi-han',mails,'','Đã quét 20 trang; còn trang khác cần xem lại');}
  await trace('hoan-tat',mails,'',files+' PDF đã lưu, '+duplicateMails+' thư đã có, '+errors+' lỗi');
  await progress('Hoàn tất: '+mails+' thư mở, '+files+' PDF đã lưu, '+duplicateMails+' thư đã có, '+errors+' lỗi.'+(pageLimitReached?'\nĐã chạm giới hạn 20 trang Gmail; kiểm tra báo cáo.':'')+(faults.length?'\nXem Báo cáo lần chạy trong tiện ích để biết từng file lỗi.':''));
  scanSucceeded=automatic&&errors===0&&!pageLimitReached;
 } catch (error) {await trace('dung',mails,'',error.message);await progress('Đã lưu '+files+' PDF từ '+mails+' thư. Dừng: '+error.message+'\nMở Báo cáo lần chạy trong tiện ích.').catch(()=>{});}
 finally {if(epoch===current){stopped=true;if(automatic)await send({type:'scan-complete',success:scanSucceeded}).catch(()=>{});await send({type:'finish'}).catch(()=>{});}}
}
chrome.runtime.onMessage.addListener(message=>{if(message.type==='run')run(message.limit===1?1:message.limit===100?100:20,message.only||[],message.automatic===true);if(message.type==='stop'){stopped=true;epoch++;}});
}
