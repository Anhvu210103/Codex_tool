import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mailnotes.desktop import data_directory, install_linux_menu, instance_lock, running_instance, state_path
from mailnotes.web import create_app


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name).resolve()

    def tearDown(self):self.temporary.cleanup()

    def test_single_instance_lock(self):
        with instance_lock(self.root):
            with self.assertRaises(BlockingIOError):
                with instance_lock(self.root):pass
        with instance_lock(self.root):pass

    def test_stale_state_cannot_open_an_external_url(self):
        state_path(self.root).parent.mkdir()
        state_path(self.root).write_text(json.dumps({'port':'https://other.example','instance':'test'}))
        with patch('urllib.request.build_opener') as opener:
            self.assertIsNone(running_instance(self.root));opener.assert_not_called()
        state_path(self.root).write_text(json.dumps({'port':8080,'instance':'right'}))
        opener=unittest.mock.MagicMock()
        opener.open.return_value.__enter__.return_value=io.BytesIO(b'{"app":"mailnotes","instance":"wrong"}')
        with patch('urllib.request.build_opener',return_value=opener):
            self.assertIsNone(running_instance(self.root))

    def test_source_reuses_existing_data_and_frozen_uses_user_storage(self):
        with patch.dict(os.environ,{'MAILNOTES_DATA_DIR':str(self.root)}):self.assertEqual(data_directory(),self.root)
        with patch.dict(os.environ,{},clear=True),patch('sys.frozen',True,create=True),patch('sys.platform','darwin'),patch('pathlib.Path.home',return_value=self.root):
            self.assertEqual(data_directory(),self.root/'Library/Application Support/SoGhiChep')
        with patch.dict(os.environ,{},clear=True),patch('sys.frozen',True,create=True),patch('sys.platform','linux'),patch('pathlib.Path.home',return_value=self.root):
            self.assertEqual(data_directory(),self.root/'.local/share/so-ghi-chep')
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.root/'LocalAppData')},clear=True),patch('sys.frozen',True,create=True),patch('sys.platform','win32'):
            self.assertEqual(data_directory(),self.root/'LocalAppData/SoGhiChep')

    def test_menu_has_no_terminal_and_quotes_spaces(self):
        with patch.dict(os.environ,{'XDG_DATA_HOME':str(self.root)}),patch('sys.platform','linux'),patch('mailnotes.desktop.command',return_value=['/tmp/app with spaces/SoGhiChep']):
            install_linux_menu()
        text=(self.root/'applications/so-ghi-chep.desktop').read_text()
        self.assertIn('Terminal=false',text);self.assertIn('Exec="/tmp/app with spaces/SoGhiChep"',text)

    def test_desktop_stop_requires_auth_and_rejects_busy_processing(self):
        app=create_app(data_root=self.root);client=app.test_client()
        self.assertEqual(client.post('/api/desktop/stop').status_code,403)
        csrf=client.get('/api/session').get_json()['csrf']
        setup=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf})
        headers={'X-CSRF-Token':setup.get_json()['csrf']}
        self.assertEqual(client.post('/api/desktop/stop',json={},headers=headers).status_code,400)
        app.extensions['desktop_shutdown']=lambda:None
        app.extensions['admin'].run_lock.acquire()
        try:self.assertEqual(client.post('/api/desktop/stop',json={},headers=headers).status_code,409)
        finally:app.extensions['admin'].run_lock.release()
        with patch('mailnotes.web.threading.Timer') as timer:
            self.assertEqual(client.post('/api/desktop/stop',json={},headers=headers).status_code,200)
            timer.return_value.start.assert_called_once()
