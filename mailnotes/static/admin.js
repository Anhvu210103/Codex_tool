'use strict';
const $ = id => document.getElementById(id);
let csrf = '', config = null, activeTab = 'overview', polling = null, currentNotes = null;
const titles = {overview:'Tổng quan',notebook:'Sổ ghi chép',rules:'Nhóm tài liệu',settings:'Cài đặt'};
async function api(path, options = {}) {
  const response = await fetch(path, {credentials:'same-origin', ...options, headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,...options.headers}});
  const data = await response.json();
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
  $(id).addEventListener('click', async event => {
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
  if (tab === 'notebook') loadNotes().catch(error => notice(error.message,true));
}
function addRule(rule = {category:'',description:'',keywords:[],senders:[]}) {
  const card = document.createElement('article'); card.className = 'card rule-card';
  card.innerHTML = '<div class="section-heading"><h2>Nhóm tài liệu</h2><button class="quiet danger remove-rule" type="button">Xóa quy tắc</button></div><div class="rule-grid"><label class="rule-description-label">Mô tả nhóm cho AI<textarea class="rule-description" maxlength="1000" placeholder="Tài liệu thuộc nhóm này khi nào? Ví dụ: văn bản yêu cầu thực hiện hoặc có thời hạn."></textarea></label><label>Tên nhóm<input class="rule-category" maxlength="100" placeholder="Ví dụ: Văn bản pháp luật"></label><label>Từ khóa (cách nhau bằng dấu phẩy)<input class="rule-keywords" placeholder="nghị định, thông tư, quyết định"></label><label>Người gửi (cách nhau bằng dấu phẩy)<input class="rule-senders" placeholder="@example.gov.vn"></label></div><p class="field-help">Để trống người gửi nếu không giới hạn. Khớp chuỗi con, không phân biệt hoa thường, có phân biệt dấu.</p>';
  card.querySelector('.rule-category').value = rule.category;
  card.querySelector('.rule-description').value = rule.description || '';
  card.querySelector('.rule-keywords').value = rule.keywords.join(', ');
  card.querySelector('.rule-senders').value = (rule.senders || []).join(', ');
  card.querySelector('.remove-rule').addEventListener('click',() => card.remove());
  $('rule-list').append(card);
}
function populateSettings() {
  $('source').value=config.source; $('gmail-query').value=config.gmail_query; $('interval').value=config.interval_seconds/60;
  $('timezone').value=config.timezone; $('schedule').checked=config.schedule_enabled;
  $('summary-mode').value=config.summary.mode; $('max-chars').value=config.summary.max_chars;
  $('max-input').value=config.summary.max_input_chars; $('model').value=config.summary.model;
  $('ai-consent').checked=config.summary.ai_consent || false;
  $('provider').value=config.summary.provider || 'deepseek';
  $('gmail-pdf').checked=config.gmail_pdf; $('pdf-ocr').checked=config.pdf_ocr;
  $('ai-options').hidden=config.summary.mode !== 'openai';
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
    next.source=$('source').value; next.gmail_query=$('gmail-query').value.trim(); next.interval_seconds=minutes*60;
    next.timezone=$('timezone').value.trim(); next.schedule_enabled=$('schedule').checked;
    next.classification_mode=$('summary-mode').value==='openai'?'ai':'rules';
    next.gmail_pdf=$('gmail-pdf').checked;next.pdf_ocr=$('pdf-ocr').checked;
    next.summary={provider:$('provider').value,mode:$('summary-mode').value,max_chars:Number($('max-chars').value),max_input_chars:Number($('max-input').value),model:$('model').value.trim(),ai_consent:$('ai-consent').checked};
    if (next.summary.mode==='openai' && !next.summary.ai_consent) throw new Error('Hãy xác nhận đồng ý xử lý nội dung qua nhà cung cấp đã chọn trước khi bật AI.');
  }
  config=await post('/api/settings',next);
  notice(includeRules?'Đã lưu quy tắc. Áp dụng cho email chưa xử lý.':'Đã lưu cài đặt. Lịch chạy và lượt xử lý tiếp theo dùng cấu hình mới.');
  await refreshStatus();
}
function dateText(value) {
  if (!value) return 'Chưa có';
  return new Intl.DateTimeFormat('vi-VN',{dateStyle:'short',timeStyle:'short',timeZone:config?.timezone || 'Asia/Ho_Chi_Minh'}).format(new Date(typeof value==='number'?value*1000:value));
}
async function refreshStatus() {
  const status=await api('/api/status?provider='+encodeURIComponent($('provider').value || 'deepseek'));
  $('run-state').textContent=status.running?'Đang xử lý':status.error?'Cần kiểm tra':'Sẵn sàng';
  $('run-detail').textContent=status.last_finished?'Hoàn tất: '+dateText(status.last_finished):'Chưa có lượt xử lý';
  $('added-count').textContent=status.last_added ?? '—';
  $('last-source').textContent=status.last_source==='gmail'?'Nguồn Gmail':status.last_source==='demo'?'Nguồn dữ liệu mẫu':'Chưa có dữ liệu';
  $('schedule-state').textContent=status.schedule_enabled?'Đang bật':'Đang tắt';
  $('next-run').textContent=status.schedule_enabled?(status.running?'Chờ lượt hiện tại hoàn tất':status.next_run?'Lần tới: '+dateText(status.next_run):'Đang chuẩn bị lịch'):'Bạn có thể chạy thủ công';
  $('run-now').disabled=status.running; $('demo-run').disabled=status.running;
  $('run-error').hidden=!status.error; $('run-error').textContent=status.error || '';
  $('source-name').textContent=config.source==='gmail'?'Gmail':'Dữ liệu mẫu';
  $('source-badge').textContent=config.source==='gmail'?(status.gmail_connected?'Đã lưu kết nối':'Cần kết nối'):'Sẵn sàng thử';
  $('source-description').textContent=config.source==='gmail'?'Đọc email khớp bộ lọc: '+config.gmail_query:'Email giả lập giúp thử quy trình mà không cần tài khoản hay AI.';
  $('summary-state').textContent=config.summary.mode==='openai'?config.summary.provider+' · Phân nhóm + tóm tắt':'Trích đoạn · Không dùng AI';
  $('interval-state').textContent=(config.interval_seconds/60)+' phút';
  $('gmail-badge').textContent=status.gmail_connected?'Đã lưu kết nối':'Chưa kết nối';
  $('client-state').textContent=status.gmail_client_configured?'Đã lưu cấu hình Google. File bí mật không hiển thị lại.':'Chưa có file cấu hình';
  $('ai-key-state').textContent=status.ai_key_configured?'Đã có key. Giá trị không hiển thị lại.':'Chưa có API key';
  $('connect-gmail').disabled=!status.gmail_client_configured || status.running;
  if (activeTab==='notebook') await loadNotes();
}
function updateOptions(select,values,placeholder) {
  const previous=select.value; select.replaceChildren(new Option(placeholder,''));
  values.forEach(value=>select.add(new Option(value,value)));
  select.value=values.includes(previous)?previous:'';
}
let notesSequence=0;
async function loadNotes() {
  const sequence=++notesSequence;
  const params=new URLSearchParams({source:$('notes-source').value,day:$('notes-day').value,category:$('notes-category').value,q:$('notes-search').value});
  const data=await api('/api/notes?'+params);
  if(sequence!==notesSequence) return;
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
    if(note.source==='gmail') {const link=document.createElement('a');link.textContent='Mở email ↗';link.href='https://mail.google.com/mail/u/0/#all/'+encodeURIComponent(note.origin_id || note.id.split(':').slice(1).join(':'));link.target='_blank';link.rel='noopener noreferrer';source.append(link);} else source.textContent=note.source==='pdf'?'PDF tải lên':'Dữ liệu mẫu';
    if(note.file_hash){const pdf=document.createElement('a');pdf.textContent='Tải PDF ↓';pdf.href='/api/document?'+new URLSearchParams({source:note.source,id:note.id});source.append(document.createElement('br'),pdf);}
    row.append(time,title,categories,content,source);$('notes-body').append(row);
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
  if(!info.authenticated) {
    $('auth-title').textContent=info.needs_setup?'Tạo mật khẩu quản trị':'Đăng nhập quản trị';
    $('auth-hint').textContent=info.needs_setup?'Thiết lập một lần để bảo vệ email và cấu hình. Mật khẩu cần ít nhất 12 ký tự.':'Quản lý nguồn tài liệu và sổ ghi chép của bạn.';
    $('auth-submit').textContent=info.needs_setup?'Tạo không gian':'Đăng nhập';
    $('password').minLength=info.needs_setup?12:1;$('password').autocomplete=info.needs_setup?'new-password':'current-password';
    $('auth-form').dataset.setup=info.needs_setup?'yes':'no';return;
  }
  config=await api('/api/settings'); populateSettings();
  $('notes-source').value=config.source;
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
action('logout',async()=>{await post('/api/logout');await boot();});
action('run-now',()=>run());action('demo-run',()=>run('demo'));
action('save-settings',()=>saveSettings());action('save-rules',()=>saveSettings(true));
$('add-rule').addEventListener('click',()=>addRule());
$('keep-unmatched').addEventListener('change',()=>{$('unmatched').disabled=!$('keep-unmatched').checked;});
$('summary-mode').addEventListener('change',()=>{$('ai-options').hidden=$('summary-mode').value!=='openai';});
for(const id of ['notes-source','notes-day','notes-category']) $(id).addEventListener('change',()=>{if(id==='notes-source'){$('notes-day').value='';$('notes-category').value='';}loadNotes().catch(error=>notice(error.message,true));});
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
  try{const categories=[...$('edit-group-options').querySelectorAll('input:checked')].map(input=>input.value);await post('/api/notes/categories',{source:editingNote.source,id:editingNote.id,categories});$('edit-groups').close();notice('Đã sửa nhóm và cập nhật sổ. Không gọi AI lại.');await loadNotes();}
  catch(error){$('edit-error').textContent=error.message;}finally{button.disabled=false;}
});
$('provider').addEventListener('change',()=>{$('model').value=$('provider').value==='deepseek'?'deepseek-chat':'gpt-4o-mini';$('ai-key').value='';refreshStatus().catch(error=>notice(error.message,true));});
action('upload-pdf',async()=>{
  const file=$('pdf-file').files[0];if(!file)throw new Error('Chọn file PDF trước.');
  if(file.size>20*1024*1024)throw new Error('PDF tối đa 20 MB.');
  const form=new FormData();form.append('file',file);form.append('reprocess',$('pdf-reprocess').checked?'true':'false');
  notice('Đang đọc PDF và xử lý theo cấu hình đã lưu. Vui lòng chờ…');
  const response=await fetch('/api/pdf',{method:'POST',credentials:'same-origin',headers:{'X-CSRF-Token':csrf},body:form});
  const data=await response.json();if(!response.ok)throw new Error(data.error || 'Không xử lý được PDF.');
  $('pdf-file').value='';$('notes-source').value='pdf';$('notes-day').value='';$('notes-category').value='';
  notice(data.added?'Đã ghi/cập nhật PDF vào sổ.':'PDF này đã xử lý, không gọi AI lại.');await loadNotes();
});
boot().catch(error=>{document.body.textContent='Không tải được trang quản trị: '+error.message;});
