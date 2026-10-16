'use strict';
if(!globalThis.mailnotesPilotInstalled){
globalThis.mailnotesPilotInstalled=true;
let stopped=true,activeRun=0;
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const forbidden=/compose|soạn thư|send|gửi|delete|xóa|archive|lưu trữ|spam|reply|trả lời|forward|chuyển tiếp|settings|cài đặt/i;
async function send(data){const result=await chrome.runtime.sendMessage(data);if(result.error)throw Error(result.error);return result;}
function controls(kind,attempted=new Set()){
 const nodes=[];const selector=kind==='mail'?'[role="row"],.zA':'[role="button"],button,a,[role="link"],[data-tooltip],.aQH .aZo,.aQH [tabindex="0"]';
 for(const node of document.querySelectorAll(selector)){
  const rect=node.getBoundingClientRect();if(rect.width<12||rect.height<12||rect.bottom<0||rect.top>innerHeight||getComputedStyle(node).visibility==='hidden')continue;
  const x=Math.min(innerWidth-1,Math.max(0,rect.left+rect.width/2)),y=Math.min(innerHeight-1,Math.max(0,rect.top+rect.height/2));
  const top=document.elementFromPoint(x,y);if(!top||!(node===top||node.contains(top)))continue;
  const raw=(node.getAttribute('aria-label')||node.getAttribute('title')||node.getAttribute('data-tooltip')||node.innerText||'').trim().replace(/\s+/g,' ');
  const attachment=node.closest('.aZo');
  const filename=attachment?.querySelector('.aV3')?.textContent?.trim()||'';
  const isDownload=/download|tải xuống/i.test(raw);
  // Gmail may put only 'Preview attachment' on the clickable tile and the
  // filename on a child. Keep the PDF filename visible to the AI.
  const previewTile=attachment&&(node===attachment||/preview|xem trước/i.test(raw));
  const label=(kind==='pdf'&&!isDownload&&previewTile&&/\.pdf\b/i.test(filename)?'Mở PDF đính kèm: '+filename:raw).slice(0,240);
  if(!label||forbidden.test(label)||attempted.has(label))continue;
  if(kind==='mail'&&(label.length<8||node.closest('[role="row"]')&&node.closest('[role="row"]')!==node))continue;
  if(kind==='pdf'&&!/\.pdf\b|download|tải xuống|preview|xem trước/i.test(label))continue;
  if(node.getAttribute('href')){const url=new URL(node.getAttribute('href'),location.href);if(url.protocol!=='https:'||!(url.hostname==='mail.google.com'||kind==='pdf'&&url.hostname.endsWith('.googleusercontent.com')))continue;}
  if(nodes.some(item=>item.label===label&&(item.node.contains(node)||node.contains(item.node))))continue;
  nodes.push({node,label});if(nodes.length>=70)break;
 }
 // Open the PDF tile before considering inline download icons. Once the
 // preview covers the tile, the visibility check leaves its Download button.
 const previews=kind==='pdf'?nodes.filter(item=>item.node.closest('.aZo')&&/\.pdf\b/i.test(item.label)&&!/download|tải xuống/i.test(item.label)):[];
 const downloads=kind==='pdf'?nodes.filter(item=>/download|tải xuống/i.test(item.label)&&!/download all|tải xuống tất cả/i.test(item.label)):[];
 return previews.length?previews:downloads.length?downloads:nodes;
}
async function run(){
 stopped=false;const epoch=++activeRun;const cancelled=()=>stopped||activeRun!==epoch;let kind=controls('mail').length?'mail':'pdf';const attempted=new Set();
 try{
  for(let step=0;step<9&&!cancelled();step++){
   let options=controls(kind,attempted);for(let i=0;i<12&&!options.length&&!cancelled();i++){await pause(500);options=controls(kind,attempted);}
   if(cancelled())return;if(!options.length)throw Error('Không thấy hàng thư/nút PDF. Mở danh sách thư có PDF hoặc thử mở thư bằng tay.');
   const result=await send({type:'choose',kind,candidates:options.map((item,index)=>({index,label:item.label,role:item.node.getAttribute('role')||item.node.tagName.toLowerCase()}))});
   if(cancelled())return;if(!result.choice)throw Error((kind==='mail'?'DeepSeek chưa chọn được hàng thư.':'DeepSeek chưa chọn được nút tải/xem PDF.')+' Tiện ích đọc được: '+options.slice(0,4).map(item=>item.label).join(' | ')+'. Hãy gửi dòng trạng thái này để kiểm tra.');
   const target=options[result.choice.index];if(!target||!target.node.isConnected||forbidden.test(target.label))throw Error('Trang đã đổi; dừng để tránh bấm nhầm.');
   await send({type:'progress',text:'AI chọn: '+target.label});if(kind==='pdf')await send({type:'arm-download'});if(cancelled())return;target.node.click();if(kind==='pdf')attempted.add(target.label);kind='pdf';await pause(2200);
  }
  if(!cancelled())await send({type:'progress',text:'Đã kết thúc lượt thử. Nếu PDF đã tải nhưng chưa vào sổ, chọn file trong tiện ích để ghi vào sổ.'});
 }catch(e){await send({type:'progress',text:e.message}).catch(()=>{});}finally{if(activeRun===epoch)stopped=true;}
}
chrome.runtime.onMessage.addListener(message=>{if(message.type==='run')run();if(message.type==='stop'){stopped=true;activeRun++;}});
}
