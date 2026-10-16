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
  runtime: {onMessage: {addListener(fn) { listeners.message = fn; }}},
  debugger: {onDetach: {addListener(fn) { listeners.detached = fn; }}, async sendCommand(target, method, params) { mouseEvents.push({target, method, params}); }, async detach() {}},
  tabs: {async query() { return [{id: activeTab}]; }, async sendMessage() {}},
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
  if (url.endsWith('/extension/import-local')) {
    assert(['/Downloads/report.pdf','/Downloads/first.pdf','/Downloads/second.pdf'].includes(JSON.parse(options.body).path));
    return new Response(JSON.stringify({available: localAvailable, ...saved}), {headers: {'content-type': 'application/json'}});
  }
  assert(url.endsWith('/extension/pdf'));
  assert.equal(options.body.get('file').name, 'report.pdf');
  return new Response(JSON.stringify(saved), {headers: {'content-type': 'application/json'}});
};
vm.runInThisContext(fs.readFileSync('chrome-extension/worker.js', 'utf8'));
function begin(id, capabilities = []) {
  activeTab = 1; requests = []; local.capabilities = capabilities;
  session.run = {tab: 1, started: Date.now(), pending: {armedAt: Date.now(), downloadId: null, result: null, error: null}};
  item = {id, url: 'https://mail.google.com/mail/u/0/?view=att', referrer: '', filename: '', mime: '', state: 'in_progress'};
}
(async () => {
  begin(7);
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, 7);
  assert(local.report.some(entry=>entry.phase==='chrome-bat-dau' && entry.detail.includes('lượt 7')));
  item.filename = '/Downloads/report.pdf';
  await listeners.changed({id: 7, filename: {current: item.filename}});
  assert.equal(requests.length, 0, 'Must wait for the file to finish downloading');
  activeTab = 2; item.state = 'complete';
  await listeners.changed({id: 7, state: {current: 'complete'}});
  assert.equal(requests.length, 2);
  assert(local.status.includes('Ngân sách'));
  assert(session.run.pending.result);

  begin(8, ['linux-local-pdf']);
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(requests.length, 1);
  assert(requests[0].endsWith('/extension/import-local'));
  assert(local.status.includes('/data/ai'));
  assert(session.run.pending.result);

  begin(9, ['linux-local-pdf']); localAvailable = false;
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(requests.length, 3, 'Unsupported local path must fall back to the attachment URL');

  begin(10); await listeners.created({...item}); item.state = 'interrupted';
  await listeners.changed({id: 10, state: {current: 'interrupted'}});
  assert.equal(requests.length, 0); assert(session.run.pending.error);
  assert(session.run.pending.error.includes('thất bại'));
  begin(11, ['linux-local-pdf']); localAvailable = true;
  item.filename = '/Downloads/first.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(session.run.pending.result.filename, 'report.pdf');
  session.run.pending = {armedAt: Date.now(), downloadId: null, result: null, error: null};
  item = {id: 12, url: 'https://mail.google.com/mail/u/0/?view=att', referrer: '', filename: '/Downloads/second.pdf', mime: 'application/pdf', state: 'complete'};
  await listeners.created({...item});
  assert.equal(session.run.pending.downloadId, 12);
  assert(session.run.pending.result);
  assert(session.run, 'Processing one PDF must keep the run alive for the next PDF');
  const fromTab = data => new Promise(resolve => listeners.message(data,{tab:{id:1}},resolve));
  let reply=await fromTab({type:'trace',event:{phase:'loi',mail:1,file:'blocked.pdf',detail:'Ô PDF bị che'}});
  assert.deepEqual(reply,{});
  assert(local.report.some(entry=>entry.file==='blocked.pdf' && entry.phase==='loi'));
  reply=await fromTab({type:'failure',failure:{rowIndex:0,key:'mail-0',text:'Công văn số 1',fileIndex:1,name:'blocked.pdf'}});
  assert.deepEqual(reply,{});
  assert.equal(local.failures[0].name,'blocked.pdf');
  reply=await fromTab({type:'trusted-click',x:150,y:30});
  assert.deepEqual(reply,{});
  assert.deepEqual(mouseEvents.map(event=>event.params.type),['mouseMoved','mousePressed','mouseReleased']);
  assert(mouseEvents.every(event=>event.target.tabId===1 && event.params.x===150 && event.params.y===30));
  reply=await fromTab({type:'trusted-escape'});
  assert.deepEqual(reply,{});
  assert.deepEqual(mouseEvents.slice(-2).map(event=>event.params.type),['keyDown','keyUp']);
  assert(mouseEvents.slice(-2).every(event=>event.params.key==='Escape' && event.target.tabId===1));
  console.log('Extension download passed: multiple files per run, persisted error report, local import and interruption');
})().catch(error => { console.error(error); process.exit(1); });
