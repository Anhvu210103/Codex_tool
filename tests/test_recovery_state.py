import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mailnotes.admin import Admin, private_json
from mailnotes.web import create_app

BASE=Path(__file__).resolve().parents[1]


class RecoveryStateTests(unittest.TestCase):
    def test_pdf_run_is_journaled_before_processing_and_restarts_as_interrupted(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(BASE,Path(directory))
            def process(*args):
                saved=json.loads((admin.private/'status.json').read_text(encoding='utf-8'))
                self.assertTrue(saved['running']);self.assertEqual(saved['last_source'],'ai');self.assertEqual(saved['last_added'],0)
                restarted=Admin(BASE,Path(directory))
                self.assertFalse(restarted.status()['running'])
                self.assertIn('gián đoạn',restarted.status()['error'])
                return 1
            with patch.object(admin,'_process_pdf_locked',side_effect=process):
                self.assertEqual(admin.process_pdf(b'%PDF-test','test.pdf',source='ai'),1)
            saved=json.loads((admin.private/'status.json').read_text(encoding='utf-8'))
            self.assertFalse(saved['running']);self.assertEqual(saved['last_added'],1)

    def test_gmail_run_is_journaled_before_worker_processes_messages(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(BASE,Path(directory));private_json(admin.key_path('vngcloud'),{'key':'test-key'})
            snapshots=[]
            def process(*args):
                snapshots.append(json.loads((admin.private/'status.json').read_text(encoding='utf-8')))
                return 0
            with patch('mailnotes.admin.messages',return_value=[]),patch('mailnotes.admin.process',side_effect=process):
                self.assertTrue(admin.start_run('gmail'))
                with admin.run_lock:pass
            self.assertEqual(len(snapshots),1);self.assertTrue(snapshots[0]['running'])
            self.assertEqual(snapshots[0]['last_source'],'gmail')
            self.assertFalse(admin.status()['running'])

    def test_failed_worker_start_clears_journal_and_processing_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(BASE,Path(directory))
            with patch('mailnotes.admin.threading.Thread',side_effect=RuntimeError('Cannot start worker')):
                with self.assertRaises(RuntimeError):admin.start_run('demo')
            self.assertFalse(admin.run_lock.locked());self.assertFalse(admin.status()['running'])
            self.assertFalse(json.loads((admin.private/'status.json').read_text(encoding='utf-8'))['running'])

    def test_failed_journal_write_does_not_start_pdf_processing_or_leak_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(BASE,Path(directory))
            with patch('mailnotes.admin.private_json',side_effect=OSError('Disk unavailable')),patch.object(admin,'_process_pdf_locked') as process:
                with self.assertRaises(OSError):admin.process_pdf(b'%PDF-test','test.pdf')
            process.assert_not_called();self.assertFalse(admin.run_lock.locked())

    def test_unexpected_http_error_has_private_trace_and_safe_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(BASE,Path(directory));app.config.update(TESTING=True,PROPAGATE_EXCEPTIONS=False)
            @app.get('/api/synthetic-failure')
            def fail():raise RuntimeError('synthetic-server-detail')
            client=app.test_client();csrf=client.get('/api/session').get_json()['csrf']
            client.post('/api/setup',json={'password':'synthetic-private-password'},headers={'X-CSRF-Token':csrf})
            with patch.object(app.logger,'error'):
                response=client.get('/api/synthetic-failure')
            self.assertEqual(response.status_code,500)
            self.assertIn('Mã lỗi:',response.get_json()['error'])
            self.assertNotIn('synthetic-server-detail',response.get_data(as_text=True))
            log=(Path(directory)/'admin/errors.log').read_text(encoding='utf-8')
            self.assertIn('HTTP GET /api/synthetic-failure',log)
            self.assertIn('synthetic-server-detail',log)
