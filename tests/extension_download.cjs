const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const local = {base: 'http://localhost:8081', token: 'test-token'};
const session = {}, listeners = {};
let activeTab = 1, item, requests = [], localAvailable = true;
const mouseEvents = [];
const storage = obj => ({
  async get(key) { return Array.isArray(key) ? Object.fromEntries(key.map(k => [k, obj[k]])) : {[key]: obj[key]}; },
  async set(data) { Object.assign(obj, data); },
  async remove(key) { delete obj[key]; },
  async setAccessLevel() {}
});
global.chrome = {
  storage: {local: storage(local), session: storage(session)},
  runtime: {onMessage: {addListener(fn) { listeners.message = fn; }}, onStartup: {addListener(fn) { listeners.startup = fn; }}, onInstalled: {addListener(fn) { listeners.installed = fn; }}},
  alarms: {onAlarm: {addListener(fn) { listeners.alarm = fn; }}, async create(name, options) { listeners.alarmSpec = {name, options}; }, async clear(name) { listeners.clearedAlarm = name; }},
  permissions: {async contains() { return true; }},
  scripting: {async executeScript(options) { listeners.injected = options; }},
  debugger: {onDetach: {addListener(fn) { listeners.detached = fn; }}, async sendCommand(target, method, params) { mouseEvents.push({target, method, params}); }, async attach() {}, async detach() {}},
  tabs: {async query() { return [{id: activeTab,url:listeners.activeURL}]; }, async sendMessage(id, message) { listeners.tabMessage = message; }, async get(id) { return {id, status: 'complete', url: listeners.createdTab?.url || 'https://mail.google.com/'}; }, async create(options) { listeners.createdTab = options; return {id: 33, status: 'complete', url: options.url}; }, async update(id, options) { listeners.updatedTab = options; return {id, status: 'complete', url: options.url}; }, async reload(id) { listeners.reloadedTab = id; }},
  downloads: {
    onCreated: {addListener(fn) { listeners.created = fn; }},
    onChanged: {addListener(fn) { listeners.changed = fn; }},
    async search() { return [item]; }
  }
};
const saved = {added: 1, filename: 'report.pdf', categories: ['Ngân sách'], folder: '/data/ai'};
global.fetch = async (url, options) => {
  requests.push(url);
  if (url.startsWith('https://mail.google.com')) return new Response(new Blob(['%PDF-test'], {type: 'application/pdf'}));
  if (url.endsWith('/extension/ping')) return new Response(JSON.stringify({app:'mailnotes-extension',protocol:1,capabilities:['linux-local-pdf']}),{headers:{'content-type':'application/json'}});
  if (url.endsWith('/extension/automation-state')) return new Response(JSON.stringify(JSON.parse(options.body).action==='load'?{failures:[],scan_cursors:{},auto_enabled_at:null}:{ok:true}),{headers:{'content-type':'application/json'}});
  if (url.endsWith('/extension/import-local')) {
    assert(['/Downloads/report.pdf','/Downloads/first.pdf','/Downloads/second.pdf','/Downloads/wanted.pdf','/Downloads/Itinerary_5RFR45.pdf'].includes(JSON.parse(options.body).path));
    return new Response(JSON.stringify({available: localAvailable, ...saved}), {headers: {'content-type': 'application/json'}});
  }
  assert(url.endsWith('/extension/pdf'));
  assert.equal(options.body.get('file').name, 'report.pdf');
  return new Response(JSON.stringify(saved), {headers: {'content-type': 'application/json'}});
};
vm.runInThisContext(fs.readFileSync('chrome-extension/worker.js', 'utf8'));
function begin(id, capabilities = [], expectedName = 'report.pdf') {
  activeTab = 1; requests = []; local.capabilities = capabilities;
  session.run = {tab: 1, started: Date.now(), pending: {armedAt: Date.now(), downloadId: null, candidates: [], expectedName, result: null, error: null}};
  item = {id, url: 'https://mail.google.com/mail/u/0/?view=att', referrer: '', filename: '', mime: '', state: 'in_progress'};
}
(async () => {
  begin(7);
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, null, 'Do not claim a download before Chrome reports its filename');
  item.filename = '/Downloads/report.pdf';
  await listeners.changed({id: 7, filename: {current: item.filename}});
  assert.equal(session.run.pending.downloadId, 7);
  assert(local.report.some(entry=>entry.phase==='chrome-bat-dau' && entry.detail.includes('lượt 7')));
  assert.equal(requests.length, 0, 'Must wait for the file to finish downloading');
  activeTab = 2; item.state = 'complete';
  await listeners.changed({id: 7, state: {current: 'complete'}});
  assert.equal(requests.length, 2);
  assert(local.status.includes('Ngân sách'));
  assert(session.run.pending.result);

  begin(8, ['linux-local-pdf']);
  activeTab = 2; // Gmail viewer can move focus before Chrome reports the download.
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, 8, 'Gmail download must not be dropped when another tab is active');
  assert.equal(requests.length, 1);
  assert(requests[0].endsWith('/extension/import-local'));
  assert(local.status.includes('/data/ai'));
  assert(session.run.pending.result);

  begin(9, ['linux-local-pdf']); localAvailable = false;
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(requests.length, 3, 'Unsupported local path must fall back to the attachment URL');

  begin(10); item.filename='/Downloads/report.pdf';item.state='in_progress';await listeners.created({...item}); item.state = 'interrupted';
  await listeners.changed({id: 10, state: {current: 'interrupted'}});
  assert.equal(requests.length, 0); assert(session.run.pending.error);
  assert(session.run.pending.error.includes('thất bại'));
  begin(11, ['linux-local-pdf'], 'first.pdf'); localAvailable = true;
  item.filename = '/Downloads/first.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(session.run.pending.result.filename, 'report.pdf');
  session.run.pending = {armedAt: Date.now(), downloadId: null, candidates: [], expectedName:'second.pdf', result: null, error: null};
  activeTab = 2;
  item = {id: 12, url: 'https://mail.google.com/mail/u/0/?view=att', referrer: '', filename: '/Downloads/second.pdf', mime: 'application/pdf', state: 'complete'};
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, 12);
  assert(session.run.pending.result);
  assert(session.run, 'Processing one PDF must keep the run alive for the next PDF');
  begin(14, ['linux-local-pdf'], 'wanted.pdf');
  item.filename='/Downloads/unrelated.pdf';item.state='complete';
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId,null,'A Gmail download with another PDF name must not be attached to this job');
  item={id:15,url:'https://mail.google.com/mail/u/0/?view=att',referrer:'',filename:'/Downloads/wanted.pdf',mime:'application/pdf',state:'complete'};
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId,15);
  assert(session.run.pending.result);
  begin(16,['linux-local-pdf'],'Itinerary_5RFR45 .pdf');
  item={id:16,url:'https://mail.google.com/mail/u/0/?view=att',referrer:'',filename:'/Downloads/Itinerary_5RFR45.pdf',mime:'application/pdf',state:'complete'};
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId,16,'Chrome removing whitespace before .pdf must not hide a real Gmail download');
  assert(session.run.pending.result);
  begin(13);
  activeTab = 2;
  item.url = 'https://example.org/unrelated.pdf'; item.filename = '/Downloads/unrelated.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, null, 'Unrelated downloads must not be imported');
  assert(local.report.some(entry=>entry.phase==='chrome-bo-qua' && entry.detail.includes('nguồn tải không thuộc Gmail')));
  const fromTab = data => new Promise(resolve => listeners.message(data,{tab:{id:1}},resolve));
  let reply=await fromTab({type:'trace',event:{phase:'loi',mail:1,file:'blocked.pdf',detail:'Ô PDF bị che'}});
  assert.deepEqual(reply,{});
  assert(local.report.some(entry=>entry.file==='blocked.pdf' && entry.phase==='loi'));
  reply=await fromTab({type:'failure',failure:{stage:'process-pdf',rowIndex:0,key:'mail-0',text:'Công văn số 1',fileIndex:1,name:'blocked.pdf',error:'Ô PDF bị che'}});
  assert.deepEqual(reply,{});
  assert.equal(local.failures[0].name,'blocked.pdf');
  assert.equal((await fromTab({type:'pending-failures'})).failures.length,1);
  await fromTab({type:'failure',failure:{stage:'open-mail',rowIndex:2,key:'mail-old',text:'Công văn cũ',fileIndex:-1,name:'',error:'Không mở được'}});
  assert.equal((await fromTab({type:'pending-failures'})).failures.length,2,'Failures must remain queued across dates and stages');
  reply=await fromTab({type:'trusted-click',x:150,y:30});
  assert.deepEqual(reply,{});
  assert.deepEqual(mouseEvents.map(event=>event.params.type),['mouseMoved','mousePressed','mouseReleased']);
  assert(mouseEvents.every(event=>event.target.tabId===1 && event.params.x===150 && event.params.y===30));
  reply=await fromTab({type:'trusted-escape'});
  assert.deepEqual(reply,{});
  assert.deepEqual(mouseEvents.slice(-2).map(event=>event.params.type),['keyDown','keyUp']);
  assert(mouseEvents.slice(-2).every(event=>event.params.key==='Escape' && event.target.tabId===1));
  const identity={key:'thread-1',fingerprint:'newest subject'};
  const fileKey=JSON.stringify([0,'first.pdf']);
  assert.deepEqual(await fromTab({type:'mail-state',...identity}),{complete:false,files:[],record:'missing'});
  await fromTab({type:'pdf-record',...identity,fileKey});
  assert.deepEqual(await fromTab({type:'mail-state',...identity}),{complete:false,files:[fileKey],record:'match'});
  await fromTab({type:'mail-complete',...identity});
  assert.equal((await fromTab({type:'mail-state',...identity})).complete,true);
  await fromTab({type:'mail-incomplete',...identity});
  assert.deepEqual(await fromTab({type:'mail-state',...identity}),{complete:false,files:[fileKey],record:'match'});
  assert.deepEqual(await fromTab({type:'mail-state',key:'thread-1',fingerprint:'changed thread'}),{complete:false,files:[],record:'changed'});
  local.processedMails['legacy-thread']={fingerprint:'1234567890abcdef:42',files:['["report.pdf",0]'],complete:true};
  assert.deepEqual(await fromTab({type:'mail-state',key:'legacy-thread',fingerprint:'legacy-thread'}),{complete:true,files:['["report.pdf",0]'],record:'match'});
  assert.equal(local.processedMails['legacy-thread'].fingerprint,'legacy-thread');
  delete session.run;
  listeners.activeURL='https://mail.google.com/mail/u/1/#inbox';
  const fromPopup = data => new Promise(resolve => listeners.message(data,{},resolve));
  assert((await fromPopup({type:'set-filter',filter:{period:'range',start:'2026-10-10',end:'2026-10-01'}})).error);
  assert.deepEqual(await fromPopup({type:'set-filter',filter:{period:'range',start:'2026-10-01',end:'2026-10-05'}}),{filter:{period:'range',start:'2026-10-01',end:'2026-10-05'}});
  assert.deepEqual(await fromPopup({type:'set-auto',enabled:true}),{});
  assert.equal(listeners.alarmSpec.options.periodInMinutes,30);
  assert(listeners.createdTab.url.includes('filename%3Apdf'));
  assert(listeners.createdTab.url.includes('after%3A2026%2F10%2F01'));
  assert(listeners.createdTab.url.includes('before%3A2026%2F10%2F06'));
  assert.equal(listeners.createdTab.active,true,'The first automatic scan must be visible so the user can observe it');
  assert(listeners.createdTab.url.includes('/mail/u/1/'));
  assert.equal(listeners.tabMessage.limit,100);
  assert.equal(session.run.automatic,true);
  assert.equal(local.autoEnabled,true);
  assert(local.autoEnabledAt);
  const scanStartedAt=session.run.scanStartedAt;
  await new Promise(resolve => listeners.message({type:'scan-complete',success:true},{tab:{id:session.run.tab}},resolve));
  assert.equal(local.scanCursors['1'],scanStartedAt,'Only a successful automatic scan advances the catch-up cursor');
  session.run.scanStartedAt=scanStartedAt+60000;
  await new Promise(resolve => listeners.message({type:'scan-complete',success:false},{tab:{id:session.run.tab}},resolve));
  assert.equal(local.scanCursors['1'],scanStartedAt,'A failed automatic scan must be retried from the prior cursor');
  delete session.run;
  await listeners.alarm({name:listeners.alarmSpec.name});
  assert.equal(listeners.reloadedTab,33);
  assert.deepEqual(await fromPopup({type:'set-auto',enabled:false}),{});
  assert.equal(local.autoEnabled,false);
  assert.equal(listeners.clearedAlarm,listeners.alarmSpec.name);
  assert(!decodeURIComponent(searchURL('0',{period:'all'})).includes(' after:'),'All-mail mode must omit date operators');
  console.log('Extension download passed: multiple files per run, persisted error report, local import and interruption');
})().catch(error => { console.error(error); process.exit(1); });
