const fs = require('fs');
const vm = require('vm');
const assert = require('node:assert/strict');
const local = {base: 'http://localhost:8081', token: 'test-token'};
const session = {}, listeners = {};
let activeTab = 1, item, requests = [], localAvailable = true;
const storage = obj => ({
  async get(key) { return Array.isArray(key) ? Object.fromEntries(key.map(k => [k, obj[k]])) : {[key]: obj[key]}; },
  async set(data) { Object.assign(obj, data); },
  async remove(key) { delete obj[key]; },
  async setAccessLevel() {}
});
global.chrome = {
  storage: {local: storage(local), session: storage(session)},
  runtime: {onMessage: {addListener(fn) { listeners.message = fn; }}},
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
    assert.equal(JSON.parse(options.body).path, '/Downloads/report.pdf');
    return new Response(JSON.stringify({available: localAvailable, ...saved}), {headers: {'content-type': 'application/json'}});
  }
  assert(url.endsWith('/extension/pdf'));
  assert.equal(options.body.get('file').name, 'report.pdf');
  return new Response(JSON.stringify(saved), {headers: {'content-type': 'application/json'}});
};
vm.runInThisContext(fs.readFileSync('chrome-extension/worker.js', 'utf8'));
function begin(id, capabilities = []) {
  activeTab = 1; requests = []; local.capabilities = capabilities;
  session.run = {tab: 1, started: Date.now(), armedAt: Date.now()};
  item = {id, url: 'https://mail.google.com/mail/u/0/?view=att', referrer: '', filename: '', mime: '', state: 'in_progress'};
}
(async () => {
  begin(7);
  await listeners.created({...item});
  assert.equal(session.run.downloadId, 7);
  item.filename = '/Downloads/report.pdf';
  await listeners.changed({id: 7, filename: {current: item.filename}});
  assert.equal(requests.length, 0, 'Must wait for the file to finish downloading');
  activeTab = 2; item.state = 'complete';
  await listeners.changed({id: 7, state: {current: 'complete'}});
  assert.equal(requests.length, 2);
  assert(local.status.includes('Ngân sách'));
  assert(!session.run);

  begin(8, ['linux-local-pdf']);
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(requests.length, 1);
  assert(requests[0].endsWith('/extension/import-local'));
  assert(local.status.includes('/data/ai'));

  begin(9, ['linux-local-pdf']); localAvailable = false;
  item.filename = '/Downloads/report.pdf'; item.state = 'complete';
  await listeners.created({...item});
  assert.equal(requests.length, 3, 'Unsupported local path must fall back to the attachment URL');

  begin(10); await listeners.created({...item}); item.state = 'interrupted';
  await listeners.changed({id: 10, state: {current: 'interrupted'}});
  assert.equal(requests.length, 0); assert(!session.run);
  assert(local.status.includes('chưa tải xong'));
  console.log('Extension download passed: completion, local import, URL fallback, interrupted file and result groups');
})().catch(error => { console.error(error); process.exit(1); });
