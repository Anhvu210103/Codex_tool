import re
import shutil
import tempfile
import unittest
import os
from pathlib import Path
from unittest.mock import patch

from mailnotes.web import create_app


class StartupTests(unittest.TestCase):
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
