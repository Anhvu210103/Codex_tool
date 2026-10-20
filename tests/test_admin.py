import copy
import json
import io
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
#
from urllib.error import HTTPError

from mailnotes.admin import Admin, error_message
from mailnotes.web import create_app

BASE = Path(__file__).resolve().parent.parent


class AdminTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.app = create_app(BASE, self.root)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.admin = self.app.extensions['admin']
        self.csrf = self.client.get('/api/session').get_json()['csrf']

    def tearDown(self):
        self.admin.stop.set()
        with self.admin.run_lock:
            pass
        if self.admin.scheduler:
            self.admin.scheduler.join(3)
        self.temporary.cleanup()

    def post(self, path, data, client=None, csrf=None):
        return (client or self.client).post(path, json=data, headers={'X-CSRF-Token': csrf or self.csrf})

    def setup_login(self):
        result = self.post('/api/setup', {'password': 'correct-private-password'})
        self.assertEqual(result.status_code, 200)
        self.csrf = result.get_json()['csrf']

    def wait_run(self):
        with self.admin.run_lock:
            pass

    def test_authentication_csrf_and_password_change_revoke_sessions(self):
        self.assertEqual(self.client.get('/api/notes').status_code, 401)
        self.assertEqual(self.client.post('/api/setup', json={'password':'long-enough-password'}).status_code, 403)
        self.setup_login()
        self.assertEqual(self.post('/api/setup', {'password':'another-long-password'}).status_code, 409)
        other = self.app.test_client()
        token = other.get('/api/session').get_json()['csrf']
        login = self.post('/api/login', {'password':'correct-private-password'}, other, token)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(other.get('/api/settings').status_code, 200)
        changed = self.post('/api/password', {'current':'correct-private-password','password':'replacement-password'})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(other.get('/api/settings').status_code, 401)
        self.assertEqual(self.client.get('/api/settings').status_code, 401)

    def test_settings_persist_reject_invalid_and_preserve_default_file(self):
        self.setup_login()
        original = (BASE / 'config.json').read_bytes()
        config = self.client.get('/api/settings').get_json()
        config.update(interval_seconds=600, timezone='UTC', source='gmail')
        self.assertEqual(self.post('/api/settings', config).status_code, 200)
        self.assertEqual(Admin(BASE, self.root).config()['interval_seconds'], 600)
        bad = copy.deepcopy(config); bad['interval_seconds']=0
        self.assertEqual(self.post('/api/settings',bad).status_code, 400)
        bad=copy.deepcopy(config);bad['timezone']='../../bad'
        self.assertEqual(self.post('/api/settings',bad).status_code, 400)
        self.assertEqual(self.admin.config()['summary']['mode'], 'openai')
        self.assertEqual(self.admin.config()['interval_seconds'],600)
        self.assertEqual((BASE / 'config.json').read_bytes(),original)

    def test_demo_search_export_and_repeat_without_ai(self):
        self.setup_login()
        self.assertEqual(self.post('/api/run', {'source':'demo'}).status_code,202)
        self.wait_run()
        self.assertEqual(self.client.get('/api/status').get_json()['last_added'],2)
        notes=self.client.get('/api/notes?source=demo&q=báo%20cáo').get_json()
        self.assertEqual(notes['total'],1)
        export=self.client.get('/api/export?source=demo&day=2026-10-13')
        self.assertEqual(export.status_code,200)
        self.assertIn('Sổ ghi chép',export.get_data(as_text=True))
        self.assertIn('| Giờ nhận |',export.get_data(as_text=True))
        self.assertIn('attachment',export.headers['Content-Disposition'])
        self.assertEqual(self.client.get('/api/export?source=../../&day=2026-10-13').status_code,400)
        self.assertEqual(self.post('/api/run',{'source':'demo'}).status_code,202)
        self.wait_run()
        self.assertEqual(self.client.get('/api/status').get_json()['last_added'],0)
        self.assertEqual(self.client.get('/api/notes?source=gmail').get_json()['total'],0)

    def test_run_lock_and_scheduler(self):
        self.setup_login()
        self.assertEqual(self.admin.config()['source'],'gmail')
        self.admin.run_lock.acquire()
        try:
            self.assertEqual(self.post('/api/run', {'source':'demo'}).status_code,409)
        finally:
            self.admin.run_lock.release()
        config=self.admin.config();config['source']='demo';config['schedule_enabled']=True
        self.admin.save_settings(config)
        self.admin.start_scheduler()
        with self.admin.lock:
            self.admin.next_due=time.time()-1
        deadline=time.monotonic()+4
        while time.monotonic()<deadline:
            if self.admin.status()['last_finished']:
                break
            self.admin.stop.wait(.05)
        self.assertEqual(self.admin.status()['last_added'],2)
        self.assertGreater(self.admin.status()['next_run'],time.time())
        config['schedule_enabled']=False
        self.admin.save_settings(config)
        self.assertIsNone(self.admin.status()['next_run'])

    def test_old_sample_source_is_not_started_automatically(self):
        from mailnotes.admin import Admin
        config=self.admin.config();config['source']='demo';config['schedule_enabled']=True
        self.admin.save_settings(config)
        reopened=Admin(BASE,self.root)
        self.assertEqual(reopened.config()['source'],'gmail')
        self.assertFalse(reopened.config()['schedule_enabled'])

    def test_docker_local_setup_requires_explicit_mode(self):
        remote={'REMOTE_ADDR':'172.18.0.1'}
        data={'password':'correct-private-password'}
        denied=self.client.post('/api/setup',json=data,headers={'X-CSRF-Token':self.csrf},environ_overrides=remote)
        self.assertEqual(denied.status_code,403)
        with patch.dict(os.environ,{'MAILNOTES_DOCKER_LOCAL_SETUP':'1'}):
            app=create_app(BASE,self.root,public_url='http://localhost:8080')
        client=app.test_client()
        csrf=client.get('/api/session').get_json()['csrf']
        accepted=client.post('/api/setup',json=data,headers={'X-CSRF-Token':csrf},environ_overrides=remote)
        self.assertEqual(accepted.status_code,200)

    def test_secrets_are_private_and_never_returned(self):
        self.setup_login()
        config=self.admin.config();config['summary']['provider']='deepseek';self.admin.save_settings(config)
        key='test-secret-do-not-return'
        self.assertEqual(self.post('/api/ai-key',{'key':key}).status_code,200)
        self.assertEqual((self.admin.private/'deepseek-key.json').stat().st_mode & 0o777,0o600)
        for path in ['/api/status','/api/settings','/api/gmail/info']:
            self.assertNotIn(key,self.client.get(path).get_data(as_text=True))
        self.assertTrue(self.client.get('/api/status').get_json()['ai_key_configured'])
        self.post('/api/ai-key',{'key':''})
        self.assertFalse((self.admin.private/'deepseek-key.json').exists())

    def test_oauth_state_exchange_and_disconnect(self):
        self.setup_login()
        credentials={'web':{'client_id':'test-client','client_secret':'test-client-secret','redirect_uris':['http://localhost:8080/oauth/callback']}}
        self.assertEqual(self.post('/api/gmail/client',{'credentials':credentials}).status_code,200)
        result=self.post('/api/gmail/connect',{}).get_json()
        self.assertIn('code_challenge=',result['url'])
        with self.client.session_transaction() as current:
            state=current['oauth']['state']
        with patch('mailnotes.web.form_request',return_value={'access_token':'test-access','refresh_token':'test-refresh','scope':'https://www.googleapis.com/auth/gmail.readonly','expires_in':3600}) as exchange:
            callback=self.client.get('/oauth/callback?state='+state+'&code=test-code')
            self.assertEqual(callback.status_code,200)
            self.assertEqual(exchange.call_args.args[1]['redirect_uri'],'http://localhost:8080/oauth/callback')
        self.assertTrue(self.admin.token.exists())
        self.assertEqual(self.client.get('/oauth/callback?state='+state+'&code=test-code').status_code,400)
        config=self.admin.config();config['schedule_enabled']=True;self.admin.save_settings(config)
        self.assertEqual(self.post('/api/gmail/disconnect',{}).status_code,200)
        self.assertFalse(self.admin.token.exists())
        self.assertFalse(self.admin.config()['schedule_enabled'])

    def test_error_messages_do_not_leak_upstream_content(self):
        self.setup_login()
        with patch('mailnotes.admin.messages',side_effect=RuntimeError('SECRET and private email text')):
            self.post('/api/run',{'source':'gmail'})
            self.wait_run()
        status=self.client.get('/api/status').get_json()
        self.assertTrue(status['error'])
        self.assertNotIn('SECRET',json.dumps(status))
        self.assertIsNone(status['last_added'])
        self.post('/api/run',{'source':'demo'});self.wait_run()
        self.assertIsNone(self.admin.status()['error'])

    def test_origin_and_login_throttling(self):
        self.setup_login()
        self.assertEqual(self.client.post('/api/run',json={},headers={'X-CSRF-Token':self.csrf,'Origin':'https://evil.example'}).status_code,403)
        other=self.app.test_client();csrf=other.get('/api/session').get_json()['csrf']
        for _ in range(5):
            self.assertEqual(self.post('/api/login',{'password':'incorrect'},other,csrf).status_code,401)
        self.assertEqual(self.post('/api/login',{'password':'incorrect'},other,csrf).status_code,429)


class ServiceErrorTests(unittest.TestCase):
    def test_known_google_reasons_and_secret_redaction(self):
        cases = [
            ('https://gmail.googleapis.com/test', 403, {'error': {'errors': [{'reason': 'accessNotConfigured'}]}}, 'Gmail API chưa được bật'),
            ('https://gmail.googleapis.com/test', 403, {'error': {'details': [{'reason': 'ACCESS_TOKEN_SCOPE_INSUFFICIENT'}]}}, 'thiếu quyền đọc Gmail'),
            ('https://oauth2.googleapis.com/token', 400, {'error': 'invalid_grant'}, 'hết hạn hoặc bị thu hồi'),
            ('https://api.deepseek.com/test', 401, {'error': {'message': 'SECRET'}}, 'DeepSeek từ chối'),
            ('https://gmail.googleapis.com/test', 403, {'error': {'message': 'SECRET'}}, 'Dịch vụ từ chối'),
        ]
        for url, code, body, expected in cases:
            with self.subTest(expected=expected):
                error = HTTPError(url, code, 'SECRET', {}, io.BytesIO(json.dumps(body).encode()))
                message = error_message(error)
                self.assertIn(expected, message)
                self.assertNotIn('SECRET', message)


if __name__=='__main__':
    unittest.main()
