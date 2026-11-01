import re
import shutil
import tempfile
import unittest
import os
import json
import hashlib
from pathlib import Path
from unittest.mock import patch

from mailnotes.web import create_app
from mailnotes.admin import private_json


class StartupTests(unittest.TestCase):
    def test_backend_version_is_frozen_for_the_running_instance_and_matches_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(data_root=directory);client=app.test_client()
            expected=json.loads((Path(__file__).resolve().parents[1]/'chrome-extension/manifest.json').read_text(encoding='utf-8'))['version']
            self.assertEqual(client.get('/health').get_json()['version'],expected)
            private_json(app.extensions['admin'].private/'extension-token.json',{'hash':hashlib.sha256(b'test-pair').hexdigest()})
            ping=client.post('/extension/ping',json={},headers={'Origin':'chrome-extension://'+'a'*32,'Authorization':'Bearer test-pair'})
            self.assertEqual(ping.get_json()['version'],expected)
            with patch('mailnotes.web.VERSION','future-unloaded-source'):
                self.assertEqual(client.get('/health').get_json()['version'],expected)
                self.assertIn('Sổ ghi chép · v'+expected,client.get('/').get_data(as_text=True))

    def test_updated_template_shows_restart_instruction_for_an_older_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            app=create_app(data_root=directory)
            with app.test_request_context('/'):
                page=app.jinja_env.get_template('admin.html').render(asset_version='test')
            self.assertIn('Cần mở lại tool sau cập nhật',page)
    def test_managed_install_can_override_data_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'MAILNOTES_DATA_DIR':directory}):
            app=create_app()
            self.assertEqual(app.extensions['admin'].root,Path(directory).resolve())

    def test_static_version_changes_without_server_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            app=create_app(data_root=root/'data')
            shutil.copytree(app.static_folder,root/'assets')
            app.static_folder=str(root/'assets')
            client=app.test_client()
            def version():
                response=client.get('/')
                self.assertEqual(response.status_code,200)
                return re.search(r'admin\.js\?v=([a-f0-9]{16})',response.get_data(as_text=True)).group(1)
            before=version()
            path=root/'assets/admin.js'
            path.write_text(path.read_text()+'\n// Simulate an asset update.\n')
            self.assertNotEqual(version(),before)

    def test_html_provides_visible_recovery_without_javascript(self):
        with tempfile.TemporaryDirectory() as directory:
            client=create_app(data_root=directory).test_client()
            page=client.get('/').get_data(as_text=True)
            opening=re.search(r'<section id="startup"([^>]*)>',page)
            self.assertIsNotNone(opening)
            self.assertNotIn('hidden',opening.group(1))
            self.assertIn('Tải lại trang',page)
