'use strict';
const $=id=>document.getElementById(id);
let saved={},run=null,pending=false,filterDirty=false;
const filterNames={catchup:'Thư mới từ lần trước',today:'Chỉ hôm nay',days7:'7 ngày gần đây',range:'Khoảng ngày đã chọn',all:'Tất cả thư có PDF'};
const filterHelp={catchup:'Tính từ lần quét thành công trước, lùi thêm một ngày để tránh sót. File đã có không tải lại.',today:'Chỉ kiểm tra thư có PDF của hôm nay. Ngày tự đổi khi chạy lượt tiếp theo.',days7:'Kiểm tra thư có PDF trong 7 ngày gần đây, gồm hôm nay.',range:'Bao gồm cả ngày bắt đầu và ngày kết thúc.',all:'Có thể mất nhiều thời gian. Mỗi lượt tối đa 20 trang Gmail; giới hạn hoặc lỗi sẽ được báo để kiểm tra.'};
function reportText(events){return (events||[]).map(e=>`${e.time} · ${e.phase} · thư ${e.mail}${e.file?' · '+e.file:''}${e.detail?' · '+e.detail:''}`).join('\n')||'Chưa có báo cáo.';}
function selectedFilter(){const period=$('period').value;return period==='range'?{period,start:$('start-date').value,end:$('end-date').value}:{period};}
function validateFilter(){const filter=selectedFilter();if(filter.period==='range'&&(!filter.start||!filter.end||filter.start>filter.end))throw Error('Chọn đủ Từ ngày và Đến hết ngày. Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.');return filter;}
function updateFilter(){
 const period=$('period').value;
 $('date-range').hidden=period!=='range';$('filter-help').textContent=filterHelp[period];
 $('filter-label').textContent=filterNames[(saved.autoFilter||{period:'catchup'}).period]||filterNames.catchup;
 filterDirty=JSON.stringify(selectedFilter())!==JSON.stringify(saved.autoFilter||{period:'catchup'});
 $('filter-unsaved').hidden=!filterDirty;
 $('save-filter').disabled=pending||!saved.token||!filterDirty;
}
function render(){
 const connected=!!saved.token,failures=(saved.failures||[]).length;
 const connection=$('connection-panel'),reportPanel=$('report-panel');
 if(connected&&connection.nextElementSibling!==reportPanel)reportPanel.before(connection);
 $('manual-card').hidden=!!run;
 const text=saved.status||(connected?'Sẵn sàng kiểm tra Gmail.':'Cần ghép nối với Sổ ghi chép một lần trước khi sử dụng.');
 const error=/(?:^|\n)(?:Lỗi|Chưa|Không)|dừng:|từ chối|thất bại|Chrome đã ngắt|^Lịch Gmail:/i.test(text)||failures>0;
 $('status').textContent=text.split('\n').slice(0,3).join('\n').slice(0,360);
 $('full-status').textContent=text;
 $('status-card').dataset.tone=run?'running':error?'error':'ready';
 $('connection-state').textContent=!connected?'Chưa ghép nối':run?'Đang quét':error?'Cần kiểm tra':'Đã ghép nối';
 $('show-report').hidden=!error||!connected;
 $('status-help').textContent=!connected?'Mở mục Kết nối lần đầu bên dưới.':run?'Bạn có thể đóng cửa sổ này. Lượt quét vẫn tiếp tục.':error?'Xem thông báo đầy đủ hoặc sao chép báo cáo để người hỗ trợ kiểm tra.':saved.autoEnabled?'Lịch 30 phút đang bật. Mỗi lượt xong sẽ dừng và chờ lượt sau.':'Lịch tự động đang tắt.';
 $('connected-controls').hidden=!connected;
 $('stop').hidden=!run;$('stop').disabled=!run;
 $('auto').disabled=pending||!connected;
 if(!pending)$('auto').checked=!!saved.autoEnabled;
 $('auto-help').textContent=saved.autoEnabled?'Đang bật. Tắt ô này để ngừng các lượt tự động tiếp theo.':'Bật lên sẽ kiểm tra ngay. Chrome và Sổ ghi chép cần đang mở.';
 for(const id of ['start','start-one','choose-file'])$(id).disabled=pending||!!run||!connected;
 $('upload').disabled=pending||!!run||!connected||!$('file').files[0];
 $('retry').hidden=!failures;$('retry').disabled=pending||!!run||!connected;
 $('failures-help').hidden=!failures;$('failures-help').textContent=`Có ${failures} mục chưa xong. Mở lại danh sách thư có lỗi rồi bấm Thử lại.`;
 for(const id of ['period','start-date','end-date','save'])$(id).disabled=pending;
 $('report').textContent=reportText(saved.report);
 updateFilter();
}
async function refresh(initial=false){
 const [local,session]=await Promise.all([chrome.storage.local.get(['base','token','status','report','autoEnabled','autoFilter','failures']),chrome.storage.session.get('run')]);
 saved=local;run=session.run||null;
 if(initial){
  $('base').value=saved.base||'http://localhost:8080';
  $('token').placeholder=saved.token?'Đã lưu mã. Chỉ nhập nếu cần thay mã.':'Dán mã vừa tạo trong Sổ ghi chép';
  $('connection-panel').open=!saved.token;
  const filter=saved.autoFilter||{period:'catchup'};$('period').value=filter.period;$('start-date').value=filter.start||'';$('end-date').value=filter.end||'';
 }
 render();
}
async function showStatus(text){saved.status=text;render();await chrome.storage.local.set({status:text});$('status-card').scrollIntoView({block:'nearest'});}
function toolURL(value){
 let url;try{url=new URL(value||'http://localhost:8080');}catch{throw Error('Địa chỉ Sổ ghi chép chưa đúng. Kiểm tra trong mục Kết nối lần đầu.');}
 if(url.protocol!=='http:'||!['localhost','127.0.0.1'].includes(url.hostname)||url.username||url.password||url.pathname!=='/'||url.search||url.hash)throw Error('Chỉ dùng địa chỉ Sổ ghi chép localhost trên máy này.');
 return url.origin;
}
async function message(data){
 let result;
 try{result=await chrome.runtime.sendMessage(data);}catch{throw Error('Tiện ích chưa phản hồi. Đóng cửa sổ nhỏ này rồi mở lại để thử.');}
 if(!result)throw Error('Tiện ích chưa phản hồi. Mở lại tiện ích rồi thử.');
 if(result.error)throw Error(result.error);
 return result;
}
function action(id,callback,mutates=true){
 $(id).addEventListener('click',async event=>{
  event.preventDefault();const button=event.currentTarget;if(button.disabled)return;
  if(mutates){pending=true;render();}else button.disabled=true;
  const label=button.textContent;if(mutates)button.textContent=({save:'Đang kết nối…','save-filter':'Đang lưu…',upload:'Đang ghi PDF…',stop:'Đang dừng…'})[id]||'Đang bắt đầu…';
  button.setAttribute('aria-busy','true');
  try{await callback();}catch(error){await showStatus('Lỗi: '+error.message);}
  finally{button.removeAttribute('aria-busy');if(mutates){button.textContent=label;pending=false;await refresh();}else button.disabled=false;}
 });
}
for(const id of ['period','start-date','end-date'])$(id).addEventListener('input',updateFilter);
action('save-filter',async()=>{await message({type:'set-filter',filter:validateFilter(),runNow:false});await showStatus('Đã lưu phạm vi. Lượt kiểm tra tiếp theo sẽ dùng thời gian mới; lượt đang chạy vẫn tiếp tục.');});
$('connection-form').addEventListener('submit',event=>{event.preventDefault();if(!pending)$('save').click();});
action('save',async()=>{
 const token=$('token').value.trim()||saved.token||'';if(!token)throw Error('Trong Sổ ghi chép, tạo mã ghép nối rồi dán vào ô Mã ghép nối.');
 await message({type:'save',base:toolURL($('base').value.trim()),token});
 $('token').value='';$('token').placeholder='Đã lưu mã. Chỉ nhập nếu cần thay mã.';$('connection-panel').open=false;
 await showStatus('Đã kết nối. Mở Gmail rồi bấm Thử 1 thư.');
});
$('auto').addEventListener('change',async()=>{
 const enabled=$('auto').checked;pending=true;render();
 try{
  if(enabled){await message({type:'set-filter',filter:validateFilter(),runNow:false});}
  await message({type:'set-auto',enabled});
  if(!enabled)await showStatus('Đã tắt lịch tự động. Bạn vẫn có thể kiểm tra bằng nút Thử 1 thư hoặc Quét 20 thư.');
 }catch(error){await showStatus('Lỗi: '+error.message);}
 finally{pending=false;await refresh();}
});
action('start',()=>message({type:'start',limit:20}));
action('start-one',()=>message({type:'start',limit:1}));
action('retry',()=>message({type:'start',retry:true,limit:20}));
action('stop',async()=>{await message({type:'stop'});await showStatus(saved.autoEnabled?'Đã dừng lượt này. Lịch 30 phút vẫn bật; tắt ô tự kiểm tra nếu muốn ngừng cả lịch.':'Đã dừng lượt đang chạy.');});
action('choose-file',()=>$('file').click(),false);
$('file').addEventListener('change',()=>{$('file-name').textContent=$('file').files[0]?.name||'Chưa chọn file';render();});
action('upload',async()=>{
 const file=$('file').files[0];if(!file)throw Error('Chọn PDF trước.');if(file.size>20*1024*1024)throw Error('PDF tối đa 20 MB.');
 const bytes=Array.from(new Uint8Array(await file.arrayBuffer()));const result=await message({type:'upload',bytes,name:file.name});
 $('file').value='';$('file-name').textContent='Chưa chọn file';await showStatus(result.status||'Đã gửi PDF vào Sổ ghi chép.');
});
action('open-tool',()=>chrome.tabs.create({url:toolURL($('base').value.trim()||saved.base)}),false);
action('show-report',()=>{$('report-panel').open=true;$('report-panel').scrollIntoView({block:'start'});},false);
action('copy-report',async()=>{
 const report=`Sổ ghi chép Gmail ${chrome.runtime.getManifest().version}\nLịch tự động: ${saved.autoEnabled?'bật':'tắt'}\nPhạm vi: ${JSON.stringify(saved.autoFilter||{period:'catchup'})}\n\n${saved.status||'Chưa chạy.'}\n\n${reportText(saved.report)}`;
 try{await navigator.clipboard.writeText(report);}catch{throw Error('Chưa sao chép được. Bạn có thể chọn nội dung báo cáo bên dưới để sao chép.');}
 $('copy-report').textContent='Đã sao chép báo cáo';
},false);
chrome.storage.onChanged.addListener((changes,area)=>{
 if(area==='session'&&changes.run){run=changes.run.newValue||null;render();return;}
 if(area!=='local')return;
 for(const [key,value] of Object.entries(changes))saved[key]=value.newValue;
 render();
});
$('version').textContent='v'+chrome.runtime.getManifest().version;
refresh(true).catch(()=>{$('status').textContent='Chưa mở được tiện ích. Đóng cửa sổ này rồi mở lại.';});
