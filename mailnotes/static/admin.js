'use strict';
const $ = id => document.getElementById(id);
let csrf = '', config = null, activeTab = 'overview', polling = null, currentNotes = null;
const titles = {overview:'Tổng quan',notebook:'Sổ ghi chép',usage:'Token & chi phí',rules:'Nhóm tài liệu',settings:'Cài đặt'};
let appBooted=false;
function showStartupError(){
 const panel=$('startup');
 if(panel){panel.hidden=false;const heading=$('startup-title');if(heading)heading.textContent='Chưa mở được giao diện';const message=$('startup-message');if(message)message.textContent='Nếu vừa cập nhật, hãy tắt phiên tool cũ rồi mở lại. Bấm Tải lại trang để thử lại; dữ liệu của bạn vẫn được giữ.';}
 else{document.body.textContent='Chưa mở được giao diện. Hãy tải lại trang (Ctrl+Shift+R). Nếu vừa cập nhật, tắt phiên tool cũ và mở lại.';}
}
window.addEventListener('error',()=>{if(!appBooted)showStartupError();});
function applyTextSize(size){
 const safe=['comfortable','large','xlarge'].includes(size)?size:'comfortable';
 document.documentElement.dataset.textSize=safe;const control=$('text-size');if(control)control.value=safe;
 try{localStorage.setItem('mailnotes.textSize',safe);}catch{}
}
let savedTextSize='comfortable';try{savedTextSize=localStorage.getItem('mailnotes.textSize') || 'comfortable';}catch{}
applyTextSize(savedTextSize);
$('text-size')?.addEventListener('change',()=>applyTextSize($('text-size').value));
async function api(path, options = {}) {
  const response = await fetch(path, {credentials:'same-origin', ...options, headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
  if(!response.headers.get('content-type')?.includes('application/json'))throw new Error(response.status===404?'Tool đang chạy bản cũ hoặc sai địa chỉ/cổng. Tắt hẳn phiên tool cũ rồi mở bản mới trong đúng thư mục.':'Tool trả về trang HTML thay vì dữ liệu. Kiểm tra địa chỉ, tắt phiên cũ và mở lại tool.');
  let data;try{data=await response.json();}catch{throw new Error('Phản hồi từ tool không hợp lệ. Tắt phiên cũ và mở lại tool.');}
  if (!response.ok) {
    if (response.status === 401 && path !== '/api/login') await boot();
    throw new Error(data.error || 'Không thực hiện được yêu cầu.');
  }
  return data;
}
const post = (path, body = {}) => api(path,{method:'POST',body:JSON.stringify(body)});
function notice(message, error = false) {
  $('notice').textContent = message; $('notice').classList.toggle('error', error); $('notice').hidden = false;
  if (error) $('notice').scrollIntoView({behavior:'smooth',block:'nearest'});
}
function action(id, callback) {
  const target=$(id);if(!target)return;
  target.addEventListener('click', async event => {
    event.preventDefault(); const button = event.currentTarget; button.disabled = true;
    try { await callback(); } catch (error) { notice(error.message,true); }
    finally { button.disabled = false; }
  });
}
function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll('.tab').forEach(node => node.hidden = node.id !== tab);
  document.querySelectorAll('[data-tab]').forEach(node => node.classList.toggle('active',node.dataset.tab === tab));
  $('breadcrumb').textContent = 'Không gian / ' + titles[tab];
  if (tab === 'overview') loadOverview().catch(error => notice(error.message,true));
  if (tab === 'usage') loadUsage().catch(error => notice(error.message,true));
  if (tab === 'notebook') loadNotes().catch(error => notice(error.message,true));
}
function rememberSource(source){try{localStorage.setItem('mailnotes.viewSource',source);}catch{}}
async function initialSource(){
 let saved='';try{saved=localStorage.getItem('mailnotes.viewSource')||'';}catch{}
 if(['gmail','pdf','ai','folder'].includes(saved))return saved;
 try{const ai=await api('/api/dashboard?source=ai');return ai.total_notes>0?'ai':config.source==='demo'?'ai':config.source;}
 catch{return config.source==='demo'?'ai':config.source;}
}
function simplifySettings(){
 const titles=['Nguồn & lịch chạy','Kết nối Gmail','Tiện ích Chrome — AI thao tác Gmail','Bảo vệ trang quản trị','Cập nhật tool'];
 for(const title of titles){
  const heading=[...$('settings').querySelectorAll('article h2')].find(node=>node.textContent.trim()===title);
  const card=heading?.closest('article');if(!card||card.dataset.collapsed)continue;
  const details=document.createElement('details');details.className=card.className+' setup-details';details.dataset.collapsed='yes';
  const summary=document.createElement('summary');summary.textContent=title;details.append(summary);
  heading.remove();while(card.firstChild)details.append(card.firstChild);card.replaceWith(details);
 }
}
function addRule(rule = {category:'',description:'',keywords:[],senders:[]}) {
  const card = document.createElement('article'); card.className = 'card rule-card';
  card.innerHTML = '<div class="section-heading"><h2>Nhóm tài liệu</h2><button class="quiet danger remove-rule" type="button">Xóa nhóm</button></div><div class="rule-grid"><label class="rule-description-label">Mô tả nhóm cho AI<textarea class="rule-description" maxlength="1000" placeholder="Tài liệu thuộc nhóm này khi nào? Ví dụ: văn bản yêu cầu thực hiện hoặc có thời hạn."></textarea></label><label>Tên nhóm<input class="rule-category" maxlength="100" placeholder="Ví dụ: Văn bản pháp luật"></label><label class="legacy-rule-field">Từ khóa (cách nhau bằng dấu phẩy)<input class="rule-keywords" placeholder="nghị định, thông tư, quyết định"></label><label class="legacy-rule-field">Người gửi (cách nhau bằng dấu phẩy)<input class="rule-senders" placeholder="@example.gov.vn"></label></div>';
  card.querySelector('.rule-category').value = rule.category;
  card.querySelector('.rule-description').value = rule.description || '';
  card.querySelector('.rule-keywords').value = rule.keywords.join(', ');
  card.querySelector('.rule-senders').value = (rule.senders || []).join(', ');
  card.querySelector('.remove-rule').addEventListener('click',() => card.remove());
  $('rule-list').append(card);
}
function populateSettings() {
  $('pdf-reprocess').checked=true;
  $('source').value=config.source==='demo'?'gmail':config.source; $('gmail-query').value=config.gmail_query;
  const filter=config.gmail_filter || {period:'advanced'};
  $('gmail-period').value=filter.period; $('gmail-start').value=filter.start_date || ''; $('gmail-end').value=filter.end_date || '';
  $('gmail-senders').value=(filter.senders || []).join(', ');$('gmail-label').value=filter.label || '';
  $('gmail-only-pdf').checked=!!filter.pdf_only;$('gmail-spam').checked=!!filter.include_spam_trash;updateGmailFilter(); $('interval').value=config.interval_seconds/60;
  $('timezone').value=config.timezone; $('schedule').checked=config.schedule_enabled;$('folder-inbox-enabled').checked=!!config.folder_inbox_enabled;
  $('summary-mode').value=config.summary.mode; $('max-chars').value=config.summary.max_chars;
  $('max-input').value=config.summary.max_input_chars; $('model').value=config.summary.model;
  $('ai-consent').checked=config.summary.ai_consent || false;
  $('provider').value=config.summary.provider || 'deepseek';
  const prices=config.summary.pricing || {};
  $('price-input').value=prices.input_per_million ?? ''; $('price-cache').value=prices.cached_input_per_million ?? ''; $('price-output').value=prices.output_per_million ?? '';
  $('gmail-pdf').checked=config.gmail_pdf; $('pdf-ocr').checked=config.pdf_ocr;
  $('ai-options').hidden=config.summary.mode !== 'openai';updateProviderUI();
  $('keep-unmatched').checked=!!config.unmatched_category; $('unmatched').value=config.unmatched_category || 'Khác';
  $('unmatched').disabled=!$('keep-unmatched').checked;
  $('rule-list').replaceChildren(); config.rules.forEach(addRule);
}
function readRules() {
  const split = value => value.split(',').map(item=>item.trim()).filter(Boolean);
  return [...document.querySelectorAll('.rule-card')].map(card=>({category:card.querySelector('.rule-category').value.trim(),description:card.querySelector('.rule-description').value.trim(),keywords:split(card.querySelector('.rule-keywords').value),senders:split(card.querySelector('.rule-senders').value)}));
}
async function saveSettings(includeRules = false) {
  const next = structuredClone(config);
  if (includeRules) {
    next.rules=readRules(); next.unmatched_category=$('keep-unmatched').checked ? $('unmatched').value.trim() : null;
  } else {
    const minutes=Number($('interval').value);
    if (!Number.isInteger(minutes) || minutes<1 || minutes>10080) throw new Error('Chu kỳ phải là số nguyên từ 1 đến 10080 phút.');
    next.gmail_filter=readGmailFilter();
    if(next.gmail_filter.pdf_only)next.gmail_pdf=true;
    next.source=$('source').value; next.gmail_query=$('gmail-query').value.trim(); next.interval_seconds=minutes*60;
    next.timezone=$('timezone').value.trim(); next.schedule_enabled=$('schedule').checked;next.folder_inbox_enabled=$('folder-inbox-enabled').checked;
    next.classification_mode=$('summary-mode').value==='openai'?'ai':'rules';
    next.gmail_pdf=$('gmail-pdf').checked || (next.gmail_filter.period!=='advanced' && next.gmail_filter.pdf_only);next.pdf_ocr=$('pdf-ocr').checked;
    next.summary={provider:$('provider').value,mode:$('summary-mode').value,max_chars:Number($('max-chars').value),max_input_chars:Number($('max-input').value),model:$('model').value.trim(),pricing:{input_per_million:priceValue('price-input'),cached_input_per_million:priceValue('price-cache'),output_per_million:priceValue('price-output')},ai_consent:$('ai-consent').checked};
    if (next.summary.mode==='openai' && !next.summary.ai_consent) throw new Error('Hãy xác nhận đồng ý xử lý nội dung qua nhà cung cấp đã chọn trước khi bật AI.');
  }
  const previousSource=config.source;
  config=await post('/api/settings',next);
  if(config.source!==previousSource){$('dashboard-source').value=config.source;$('notes-source').value=config.source;rememberSource(config.source);}
  notice(includeRules?'Đã lưu nhóm tài liệu. Áp dụng cho tài liệu chưa xử lý.':'Đã lưu cài đặt. Lịch chạy và lượt xử lý tiếp theo dùng cấu hình mới.');
  await refreshStatus();
}
function dateText(value) {
  if (!value) return 'Chưa có';
  return new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short',timeZone:config?.timezone || 'Asia/Ho_Chi_Minh'}).format(new Date(typeof value==='number'?value*1000:value));
}
async function refreshStatus() {
  const status=await api('/api/status?provider='+encodeURIComponent($('provider').value || 'deepseek'));
  const folder=status.folder_inbox||{},busy=status.running||folder.running;
  $('stop-app').hidden=!status.desktop_mode;
  $('run-state').textContent=busy?'Đang xử lý':status.error?'Cần kiểm tra':'Sẵn sàng';
  $('run-detail').textContent=status.last_finished?'Hoàn tất: '+dateText(status.last_finished):'Chưa có lượt xử lý';
  $('added-count').textContent=status.last_added ?? '—';
  $('last-source').textContent=status.last_source==='gmail'?'Nguồn Gmail':status.last_source==='demo'?'Lượt kiểm tra cũ':'Chưa có dữ liệu';
  $('schedule-state').textContent=status.schedule_enabled?'Đang bật':'Đang tắt';
  $('next-run').textContent=status.schedule_enabled?(status.running?'Chờ lượt hiện tại hoàn tất':status.next_run?'Lần tới: '+dateText(status.next_run):'Đang chuẩn bị lịch'):'Bạn có thể chạy thủ công';
  const folderErrors=(folder.errors||[]).slice(0,5).map(item=>`\n• ${item.file}: ${item.error}`).join('');$('folder-inbox-status').textContent=folder.running?'Đang đọc PDF...':folder.last_finished?`Lần cuối: ${dateText(folder.last_finished)} · ${folder.last_processed||0} tệp · ${folder.last_added||0} ghi chép mới${folder.error?' · '+folder.error:''}${folderErrors}`:'Chưa quét thư mục.';
  $('run-now').hidden=config.source!=='gmail';$('run-now').disabled=busy;$('run-folder-inbox').disabled=busy;
  $('run-now').textContent='Quét Gmail API ngay';
  $('run-error').hidden=!status.error; $('run-error').textContent=status.error || '';
  $('source-name').textContent=config.source==='gmail'?'Gmail API':'Nguồn tự động';
  $('source-badge').textContent=config.source==='gmail'?(status.gmail_connected?'Đã lưu kết nối':'Cần kết nối'):'Chưa cài đặt';
  $('source-description').textContent=config.source==='gmail'?gmailFilterDescription(config.gmail_filter || {period:'advanced'}):'Chọn Gmail trong Cài đặt để dùng lịch quét tự động.';
  $('summary-state').textContent=config.summary.mode==='openai'?config.summary.provider+' · Phân nhóm + tóm tắt':'Trích đoạn · Không dùng AI';
  $('interval-state').textContent=(config.interval_seconds/60)+' phút';
  $('gmail-badge').textContent=status.gmail_connected?'Đã lưu kết nối':'Chưa kết nối';
  $('client-state').textContent=status.gmail_client_configured?'Đã lưu cấu hình Google. File bí mật không hiển thị lại.':'Chưa có file cấu hình';
  $('ai-key-state').textContent=status.ai_key_configured?'Đã có key. Giá trị không hiển thị lại.':'Chưa có API key';
  $('connect-gmail').disabled=!status.gmail_client_configured || status.running;
  $('dashboard-pdf-state').textContent=config.gmail_pdf?'Tự tải và đọc nội dung':'Chưa bật';
  if($('pdf-processing-description'))$('pdf-processing-description').textContent='PDF có chữ được chuyển sang Markdown rồi gửi chữ cho DeepSeek. Nếu bật OCR, từng trang PDF scan được gửi ảnh qua DeepSeek, ghép thành Markdown rồi mới phân tích.';
  if (activeTab==='overview') await loadOverview();
  if (activeTab==='notebook') await loadNotes();
  if (activeTab==='usage') await loadUsage();
}
function updateOptions(select,values,placeholder) {
  const previous=select.value; select.replaceChildren(new Option(placeholder,''));
  values.forEach(value=>select.add(new Option(value,value)));
  select.value=values.includes(previous)?previous:'';
}
let notesSequence=0;
async function loadNotes() {
  const sequence=++notesSequence;
  const source=$('notes-source').value;
  const params=new URLSearchParams({source,day:$('notes-day').value,category:$('notes-category').value,q:$('notes-search').value});
  const [data,info]=await Promise.all([api('/api/notes?'+params),source==='demo'?Promise.resolve(null):api('/api/archive?'+new URLSearchParams({source}))]);
  if(sequence!==notesSequence) return;
  if($('archive-card')){$('archive-card').hidden=!info;if(info){$('archive-path').textContent=info.path;$('open-archive').hidden=!info.can_open;}}
  currentNotes=data;
  updateOptions($('notes-day'),data.days,'Tất cả ngày'); updateOptions($('notes-category'),data.categories,'Tất cả nhóm');
  $('notes-body').replaceChildren(); $('notes-empty').hidden=data.notes.length>0;
  for (const note of data.notes) {
    const row=document.createElement('tr');
    const time=document.createElement('td');time.textContent=dateText(note.received_at);
    const title=document.createElement('td');const strong=document.createElement('strong');strong.textContent=note.subject;
    const sender=document.createElement('small');sender.textContent=note.sender;title.append(strong,sender);
    const categories=document.createElement('td');note.categories.forEach(category=>{const tag=document.createElement('span');tag.className='badge';tag.textContent=category;categories.append(tag,document.createElement('br'));});
    const edit=document.createElement('button');edit.className='secondary edit-button';edit.textContent='Sửa nhóm';edit.addEventListener('click',()=>openGroupEditor(note));categories.append(edit);
    const content=document.createElement('td');const summary=document.createElement('div');summary.className='summary-text';summary.textContent=note.summary;content.append(summary);if(note.review_reason){const warning=document.createElement('div');warning.className='review-note';warning.textContent=note.review_reason;content.append(warning);}
    const source=document.createElement('td');
    if(note.source==='gmail') {const link=document.createElement('a');link.textContent='Mở email';link.href='https://mail.google.com/mail/u/0/#all/'+encodeURIComponent(note.origin_id || note.id.split(':').slice(1).join(':'));link.target='_blank';link.rel='noopener noreferrer';source.append(link);} else source.textContent=({ai:'AI thao tác',pdf:'PDF tải lên',folder:'Thư mục nhận PDF',demo:'Dữ liệu mẫu'}[note.source] || note.source);
    if(note.file_hash){const pdf=document.createElement('a');pdf.textContent='Tải PDF';pdf.href='/api/document?'+new URLSearchParams({source:note.source,id:note.id});source.append(document.createElement('br'),pdf);const md=document.createElement('a');md.textContent='Tải Markdown';md.href='/api/document?'+new URLSearchParams({source:note.source,id:note.id,format:'markdown'});source.append(document.createElement('br'),md);const again=document.createElement('button');again.className='secondary edit-button';again.textContent='Đọc lại PDF';again.addEventListener('click',async()=>{if(!confirm('Đọc lại PDF theo cấu hình hiện tại? Có thể tốn phí AI và thay nhóm/tóm tắt đã chỉnh tay.'))return;again.disabled=true;try{await post('/api/notes/reprocess',{source:note.source,id:note.id});notice('Đã đọc lại PDF và cập nhật sổ.');await loadNotes();}catch(error){notice(error.message,true);}finally{again.disabled=false;}});source.append(document.createElement('br'),again);}
    const files=document.createElement('td');
    for(const item of note.local_markdown_paths||[]){const entry=document.createElement('div');entry.className='local-file';const group=document.createElement('small');group.textContent=item.category;const path=document.createElement('code');path.textContent=item.path;entry.append(group,path);files.append(entry);}
    if(!files.childNodes.length){files.textContent='Chưa có file Markdown theo nhóm';}
    row.append(time,title,categories,content,source,files);$('notes-body').append(row);
  }
  $('notes-count').textContent=(data.total>500?'Hiển thị 500 / ':'')+data.total+' ghi chép';
  $('export').disabled=!$('notes-day').value;
  $('export').title=$('notes-day').value?'Tải toàn bộ sổ của ngày đã chọn':'Chọn một ngày để tải sổ';
}
async function run(source) {
  await post('/api/run',source?{source}:{});
  notice('Đã bắt đầu xử lý. Trạng thái sẽ tự cập nhật.'); await refreshStatus();
}
async function boot() {
  if (polling) clearInterval(polling);
  const info=await api('/api/session');csrf=info.csrf;
  $('auth').hidden=info.authenticated;$('app').hidden=!info.authenticated;
  if($('startup'))$('startup').hidden=true;
  appBooted=true;
  if(!info.authenticated) {
    $('auth-title').textContent=info.needs_setup?'Tạo mật khẩu quản trị':'Đăng nhập quản trị';
    $('auth-hint').textContent=info.needs_setup?'Thiết lập một lần để bảo vệ email và cấu hình. Mật khẩu cần ít nhất 12 ký tự.':'Quản lý nguồn tài liệu và sổ ghi chép của bạn.';
    $('auth-submit').textContent=info.needs_setup?'Tạo không gian':'Đăng nhập';
    $('password').minLength=info.needs_setup?12:1;$('password').autocomplete=info.needs_setup?'new-password':'current-password';
    $('auth-form').dataset.setup=info.needs_setup?'yes':'no';return;
  }
  for(const id of ['notes-source','dashboard-source']){const select=$(id);if(select&&!select.querySelector('option[value="folder"]')){const option=document.createElement('option');option.value='folder';option.textContent='Thư mục nhận PDF';select.append(option);}}
  config=await api('/api/settings'); populateSettings();simplifySettings();
  const inbox=await api('/api/folder-inbox');$('folder-inbox-path').textContent=inbox.path;$('open-folder-inbox').disabled=!inbox.can_open;
  const viewSource=await initialSource();$('notes-source').value=viewSource;$('dashboard-source').value=viewSource;
  const gmail=await api('/api/gmail/info');$('callback').value=gmail.callback;
  await refreshStatus();setTab(activeTab);
  polling=setInterval(()=>refreshStatus().catch(error=>notice(error.message,true)),4000);
}
$('auth-form').addEventListener('submit',async event=>{
  event.preventDefault();$('auth-submit').disabled=true;$('auth-error').textContent='';
  try {const data=await post($('auth-form').dataset.setup==='yes'?'/api/setup':'/api/login',{password:$('password').value});csrf=data.csrf;$('password').value='';await boot();}
  catch(error){$('auth-error').textContent=error.message;}finally{$('auth-submit').disabled=false;}
});
document.querySelectorAll('[data-tab]').forEach(node=>node.addEventListener('click',()=>setTab(node.dataset.tab)));
document.querySelectorAll('[data-go]').forEach(node=>node.addEventListener('click',()=>setTab(node.dataset.go)));
action('stop-app',async()=>{if(!confirm('Tắt tool và dừng lịch tự động trên máy này?'))return;await post('/api/desktop/stop');if(polling)clearInterval(polling);notice('Đã yêu cầu tắt tool. Bạn có thể đóng trang. Bấm biểu tượng Sổ ghi chép để mở lại.');});
action('logout',async()=>{await post('/api/logout');await boot();});
action('run-now',()=>run());
action('open-archive',async()=>{await post('/api/archive?'+new URLSearchParams({source:$('notes-source').value}));notice('Đã yêu cầu mở thư mục tài liệu trên máy chạy tool.');});
action('open-folder-inbox',async()=>{await post('/api/folder-inbox',{action:'open'});notice('Đã mở thư mục nhận PDF.');});
action('run-folder-inbox',async()=>{await post('/api/folder-inbox',{action:'run'});notice('Đang quét thư mục nhận PDF.');await refreshStatus();});
action('save-settings',()=>saveSettings());action('save-rules',()=>saveSettings(true));
action('pair-extension',async()=>{const data=await post('/api/extension/pair');$('extension-token').value=data.token;notice('Đã tạo mã ghép nối mới. Dán mã vào tiện ích Chrome; mã cũ đã hết hiệu lực. Không gửi mã vào chat.');});
action('add-preset-groups',async()=>{
  const presets=await api('/api/group-presets');
  const existing=new Set([...document.querySelectorAll('.rule-category')].map(node=>node.value.trim().toLocaleLowerCase('vi-VN')));
  let added=0;
  for(const rule of presets){const key=rule.category.toLocaleLowerCase('vi-VN');if(existing.has(key))continue;addRule(rule);existing.add(key);added++;}
  notice(added?`Đã thêm ${added} nhóm mẫu. Xem lại mô tả rồi bấm Lưu nhóm.`:'Bạn đã có đủ các nhóm mẫu.');
});
$('add-rule').addEventListener('click',()=>addRule());
$('keep-unmatched').addEventListener('change',()=>{$('unmatched').disabled=!$('keep-unmatched').checked;});
$('summary-mode').addEventListener('change',()=>{$('ai-options').hidden=$('summary-mode').value!=='openai';updateProviderUI();});
for(const id of ['notes-source','notes-day','notes-category']) $(id).addEventListener('change',()=>{if(id==='notes-source'){$('notes-day').value='';$('notes-category').value='';$('dashboard-source').value=$('notes-source').value;rememberSource($('notes-source').value);}loadNotes().catch(error=>notice(error.message,true));});
let searchTimer;$('notes-search').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadNotes().catch(error=>notice(error.message,true)),250);});
action('export',async()=>{if(!$('notes-day').value)throw new Error('Chọn một ngày để tải sổ.');window.location.assign('/api/export?'+new URLSearchParams({source:$('notes-source').value,day:$('notes-day').value}));});
action('upload-client',async()=>{
  const file=$('oauth-file').files[0];if(!file)throw new Error('Chọn file JSON tải từ Google Cloud.');
  if(file.size>64000)throw new Error('File cấu hình quá lớn.');
  let credentials;try{credentials=JSON.parse(await file.text());}catch{throw new Error('File JSON không hợp lệ.');}
  await post('/api/gmail/client',{credentials});$('oauth-file').value='';notice('Đã lưu cấu hình Google. Bạn có thể kết nối Gmail.');await refreshStatus();
});
action('connect-gmail',async()=>{const data=await post('/api/gmail/connect');window.location.assign(data.url);});
action('disconnect-gmail',async()=>{if(!confirm('Ngắt Gmail và tắt lịch tự động? Ghi chép đã lưu vẫn được giữ.'))return;await post('/api/gmail/disconnect');config=await api('/api/settings');$('schedule').checked=false;notice('Đã xóa token Gmail trên máy chủ và tắt lịch chạy.');await refreshStatus();});
action('save-key',async()=>{if(!$('ai-key').value.trim())throw new Error('Nhập API key trước khi lưu.');await post('/api/ai-key',{provider:$('provider').value,key:$('ai-key').value});$('ai-key').value='';notice('Đã lưu API key riêng. Giá trị không hiển thị lại.');await refreshStatus();});
action('delete-key',async()=>{if(!confirm('Xóa API key lưu trên máy chủ? Nếu bật AI, lượt Gmail tiếp theo sẽ cần key.'))return;await post('/api/ai-key',{provider:$('provider').value,key:''});$('ai-key').value='';notice('Đã xóa key lưu qua web. Key từ biến môi trường, nếu có, vẫn do quản trị viên máy chủ quản lý.');await refreshStatus();});
action('change-password',async()=>{await post('/api/password',{current:$('current-password').value,password:$('new-password').value});$('current-password').value='';$('new-password').value='';await boot();});
function readGmailFilter(){return {period:$('gmail-period').value,start_date:$('gmail-start').value,end_date:$('gmail-end').value,senders:$('gmail-senders').value.split(',').map(value=>value.trim()).filter(Boolean),label:$('gmail-label').value.trim(),pdf_only:$('gmail-only-pdf').checked,include_spam_trash:$('gmail-spam').checked};}
function gmailFilterDescription(filter){
 const periods={today:'Đọc thư của hôm nay, tự cập nhật ngày',week:'Đọc thư trong 7 ngày gần đây, tính cả hôm nay',range:'Đọc thư từ '+(filter.start_date?filter.start_date.split('-').reverse().join('/'):'chưa chọn ngày')+' đến hết '+(filter.end_date?filter.end_date.split('-').reverse().join('/'):'chưa chọn ngày'),all:'Đọc tất cả thư',advanced:'Đang dùng bộ lọc nâng cao đã lưu'};
 if(filter.period==='advanced')return periods.advanced;
 const details=[periods[filter.period]];
 if(filter.senders?.length)details.push('từ '+filter.senders.join(', '));
 if(filter.label)details.push('nhãn “'+filter.label+'”');
 if(filter.pdf_only)details.push('chỉ thư có PDF');
 details.push(filter.include_spam_trash?'gồm cả thư rác và thùng rác':'không lấy thư rác và thùng rác');
 return details.join(' · ');
}
function updateGmailFilter(){
 const filter=readGmailFilter();const advanced=filter.period==='advanced';
 $('gmail-date-range').hidden=filter.period!=='range';$('gmail-all-warning').hidden=filter.period!=='all';
 $('gmail-advanced').open=advanced;$('gmail-query').disabled=!advanced;
 for(const id of ['gmail-senders','gmail-label','gmail-only-pdf','gmail-spam'])$(id).disabled=advanced;
 $('gmail-filter-preview').textContent=gmailFilterDescription(filter);
 if(filter.pdf_only&&!advanced)$('gmail-pdf').checked=true;
}
for(const id of ['gmail-period','gmail-start','gmail-end','gmail-senders','gmail-label','gmail-only-pdf','gmail-spam'])$(id).addEventListener('input',updateGmailFilter);
let overviewSequence=0;
function openNotebook(source,category='',search=''){
 $('notes-source').value=source;$('dashboard-source').value=source;rememberSource(source);$('notes-category').value='';$('notes-day').value='';$('notes-search').value=search;
 if(category){if(![...$('notes-category').options].some(option=>option.value===category))$('notes-category').add(new Option(category,category));$('notes-category').value=category;}
 setTab('notebook');
}
async function loadOverview(){
 const sequence=++overviewSequence;
 const data=await api('/api/dashboard?'+new URLSearchParams({source:$('dashboard-source').value}));
 if(sequence!==overviewSequence)return;
 const today=data.usage.today,total=data.usage.totals;
 $('dashboard-day').textContent='Ngày '+data.day.split('-').reverse().join('/')+' · Theo dõi tiền AI, tài liệu mới và nội dung cần xem lại.';
 $('dashboard-cost').textContent=today.unpriced_calls&&!today.estimated_usd?'Chưa đủ đơn giá':money(today.estimated_usd);
 $('dashboard-cost-detail').textContent=(today.unpriced_calls?today.unpriced_calls+' lượt chưa tính được tiền. ':'')+'Tổng đã biết: '+money(total.estimated_usd)+(total.unpriced_calls?' · chưa đầy đủ':'')+' · tất cả nguồn';
 $('dashboard-tokens').textContent=number(today.total_tokens);
 $('dashboard-token-detail').textContent=number(today.api_calls)+' lượt API hôm nay'+(today.unknown_usage_calls?' · '+today.unknown_usage_calls+' lượt thiếu usage':'')+' · tất cả nguồn';
 $('dashboard-today').textContent=number(data.received_today);$('dashboard-total').textContent='Đã lưu '+number(data.total_notes)+' tài liệu · '+({gmail:'Gmail API',pdf:'PDF tải lên',ai:'Gmail qua tiện ích',folder:'Thư mục nhận PDF',demo:'Dữ liệu mẫu'}[data.source]);
 $('dashboard-review').textContent=number(data.needs_review);
 $('dashboard-groups').replaceChildren();$('dashboard-groups-empty').hidden=data.groups.length>0;
 for(const group of data.groups.slice(0,6)){const row=document.createElement('div');row.className='group-count';const name=document.createElement('button');name.textContent=group.name;name.addEventListener('click',()=>openNotebook(data.source,group.name));const count=document.createElement('strong');count.textContent=number(group.count);row.append(name,count);$('dashboard-groups').append(row);}
 $('dashboard-recent').replaceChildren();$('dashboard-empty').hidden=data.recent.length>0;
 for(const note of data.recent){
  const row=document.createElement('tr');const time=document.createElement('td');time.textContent=dateText(note.received_at);
  const title=document.createElement('td');const name=document.createElement('strong');name.textContent=note.subject;const sender=document.createElement('small');sender.textContent=note.sender;title.append(name,sender);
  const groups=document.createElement('td');for(const category of note.categories){const badge=document.createElement('span');badge.className='badge';badge.textContent=category;groups.append(badge,document.createElement('br'));}
  const summary=document.createElement('td');const text=document.createElement('div');text.className='summary-text';text.textContent=note.summary;summary.append(text);
  if(note.review_reason){const warning=document.createElement('div');warning.className='review-note';warning.textContent=note.review_reason;summary.append(warning);}
  const actions=document.createElement('td');const edit=document.createElement('button');edit.className='secondary';edit.textContent='Sửa nhóm';edit.addEventListener('click',()=>openGroupEditor(note));const view=document.createElement('button');view.className='quiet';view.textContent='Xem trong sổ';view.addEventListener('click',()=>openNotebook(data.source,'',note.subject));actions.append(edit,document.createElement('br'),view);
  row.append(time,title,groups,summary,actions);$('dashboard-recent').append(row);
 }
}
$('dashboard-source').addEventListener('change',()=>{rememberSource($('dashboard-source').value);$('notes-source').value=$('dashboard-source').value;loadOverview().catch(error=>notice(error.message,true));});
for(const id of ['overview-notes','overview-all-notes'])action(id,()=>openNotebook($('dashboard-source').value));
action('overview-review',()=>openNotebook($('dashboard-source').value,'Cần xem lại'));
action('overview-pdf',()=>{openNotebook('pdf');$('pdf-file').scrollIntoView({behavior:'smooth',block:'center'});$('pdf-file').focus();});
function priceValue(id){const value=$(id).value.trim();if(value==='')return null;const price=Number(value);if(!Number.isFinite(price)||price<0)throw new Error('Đơn giá phải là số không âm.');return price;}
function clearPrices(){for(const id of ['price-input','price-cache','price-output'])$(id).value='';}
$('model').addEventListener('input',clearPrices);
const number=value=>value==null?'—':new Intl.NumberFormat('vi-VN').format(value);
const money=value=>value==null?'Chưa đủ dữ liệu':value>0&&value<.000001?'<$0.000001':'$'+Number(value).toFixed(6);
async function loadUsage(){
 const data=await api('/api/usage');const total=data.totals;
 $('usage-tokens').textContent=number(total.total_tokens);
 $('usage-token-detail').textContent=number(total.api_calls)+' lượt API có phản hồi · Vào '+number(total.input_tokens)+' / Ra '+number(total.output_tokens)+(total.unknown_usage_calls?' · '+number(total.unknown_usage_calls)+' lượt thiếu usage':'');
 $('usage-cost').textContent=total.unpriced_calls && !total.estimated_usd?'Chưa đủ đơn giá':money(total.estimated_usd);
 $('usage-cost-detail').textContent=total.unpriced_calls?number(total.unpriced_calls)+' lượt chưa tính được tiền; tổng tiền chưa đầy đủ':'Ước tính theo đơn giá đã lưu, không phải hóa đơn';
 $('usage-cache').textContent=number(total.local_cache_hits);
 $('usage-models').replaceChildren();$('usage-history').replaceChildren();
 function row(parent,values){const tr=document.createElement('tr');values.forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});parent.append(tr);}
 for(const model of data.models)row($('usage-models'),[model.provider+' / '+model.model+(model.unknown_usage_calls?' · '+number(model.unknown_usage_calls)+' lượt thiếu usage':''),number(model.api_calls),number(model.input_tokens),number(model.cached_tokens),number(model.output_tokens),model.unpriced_calls?money(model.estimated_usd)+' (chưa đầy đủ)':money(model.estimated_usd)]);
 for(const item of data.recent)row($('usage-history'),[dateText(item.created_at),item.source+' / '+item.provider+' / '+item.model,item.cache_hit?'Cache nội bộ':'API',number(item.input_tokens)+' / '+number(item.output_tokens),money(item.estimated_usd)]);
 if(!data.models.length)row($('usage-models'),['Chưa có dữ liệu AI từ bản cập nhật này.']);
}
let editingNote=null;
function openGroupEditor(note){
  editingNote=note;$('edit-error').textContent='';$('edit-group-options').replaceChildren();
  const groups=[...new Set([...config.rules.map(rule=>rule.category),'Cần xem lại',...(config.unmatched_category?[config.unmatched_category]:[])])];
  for(const category of groups){const label=document.createElement('label');label.className='check';const input=document.createElement('input');input.type='checkbox';input.value=category;input.checked=note.categories.includes(category);label.append(input,document.createTextNode(category));$('edit-group-options').append(label);}
  $('edit-groups').showModal();
}
$('cancel-edit').addEventListener('click',()=>$('edit-groups').close());
$('edit-groups-form').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.submitter;button.disabled=true;
  try{const categories=[...$('edit-group-options').querySelectorAll('input:checked')].map(input=>input.value);await post('/api/notes/categories',{source:editingNote.source,id:editingNote.id,categories});$('edit-groups').close();notice('Đã sửa nhóm và cập nhật sổ. Không gọi AI lại.');if(activeTab==='overview')await loadOverview();else await loadNotes();}
  catch(error){$('edit-error').textContent=error.message;}finally{button.disabled=false;}
});
function updateProviderUI(){
 if($('local-ocr-label'))$('local-ocr-label').hidden=false;
 if($('pdf-ocr'))$('pdf-ocr').disabled=false;
 if($('pdf-reader-help'))$('pdf-reader-help').textContent='PDF có chữ → Markdown. PDF scan chỉ được OCR qua DeepSeek khi bật tùy chọn này; kết quả OCR cần đối chiếu bản gốc.';
}
action('setup-deepseek',()=>{setTab('settings');$('summary-mode').value='openai';$('ai-options').hidden=false;updateProviderUI();notice('Nhập DeepSeek API key, bấm Lưu key riêng, xác nhận đồng ý gửi chữ tài liệu rồi Lưu cài đặt.');$('ai-key').scrollIntoView({behavior:'smooth',block:'center'});$('ai-key').focus();});
action('upload-pdf',async()=>{
  const file=$('pdf-file').files[0];if(!file)throw new Error('Chọn file PDF trước.');
  if(file.size>20*1024*1024)throw new Error('PDF tối đa 20 MB.');
  const form=new FormData();form.append('file',file);form.append('reprocess',$('pdf-reprocess').checked?'true':'false');
  notice('Đang đọc PDF và xử lý theo cấu hình đã lưu. Vui lòng chờ…');
  const response=await fetch('/api/pdf',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf},body:form});
  const data=await response.json();if(!response.ok)throw new Error(data.error || 'Không xử lý được PDF.');
  $('pdf-file').value='';$('notes-source').value='pdf';$('dashboard-source').value='pdf';rememberSource('pdf');$('notes-day').value='';$('notes-category').value='';
  notice(data.added?'Đã ghi/cập nhật PDF vào sổ.':'PDF này đã xử lý, không gọi AI lại.');await loadNotes();
});
boot().catch(()=>{if($('auth'))$('auth').hidden=true;if($('app'))$('app').hidden=true;showStartupError();});

action('update-tool',async()=>{
 if(!confirm('Cập nhật bản mới và tự mở lại tool? Dữ liệu, key và cài đặt được giữ nguyên.'))return;
 await post('/api/desktop/update');
 const panel=$('update-progress');panel.hidden=false;panel.textContent='Đang tải bản mới. Tool sẽ tự mở lại. Nếu có lỗi, mở Cap-Nhat-So-Ghi-Chep.sh để xem thông báo.';
 $('update-tool').disabled=true;
 let attempts=0;
 const timer=setInterval(async()=>{
  try{const result=await api('/api/desktop/update-log');panel.textContent=result.message||panel.textContent;
   if(result.message.includes('Cập nhật chưa hoàn tất:')||result.message.includes('Đã cập nhật.')){clearInterval(timer);$('update-tool').disabled=false;}
  }catch{/* The server is restarting; its launcher opens the new page. */}
  if(++attempts>=180){clearInterval(timer);$('update-tool').disabled=false;}
 },3000);
});
