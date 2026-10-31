import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location('updater', Path(__file__).resolve().parents[1] / 'Cap-Nhat-Tool.py')
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdaterTests(unittest.TestCase):
    def archive(self, extra):
        data = io.BytesIO()
        with zipfile.ZipFile(data, 'w') as z:
            for name in ['mailnotes/web.py', 'mailnotes/desktop.py', 'requirements-web.txt', 'config.json']:
                z.writestr('repo/' + name, '')
            for name, content in extra.items():
                z.writestr('repo/' + name, content)
        return data.getvalue()

    def test_archive_cannot_replace_private_state(self):
        with tempfile.TemporaryDirectory() as d:
            files = updater.unpack(self.archive({'.local/admin/settings.json': 'secret', '.env': 'secret', '.venv/bin/python': 'bad'}), Path(d))
            self.assertNotIn(Path('.env'), files)
            self.assertFalse((Path(d) / '.local').exists())
            with self.assertRaises(ValueError):
                updater.unpack(self.archive({'../outside': 'bad'}), Path(d))

    def test_failed_import_rolls_back_code_preserving_private_state(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'root';stage = Path(d) / 'stage';backup = Path(d) / 'backup'
            for directory in [root, stage, backup]:directory.mkdir()
            (root / 'config.json').write_text('old')
            (stage / 'config.json').write_text('new')
            (stage / 'requirements-web.txt').write_text('')
            (root / 'requirements-web.txt').write_text('')
            (root / '.env').write_text('private')
            with patch.object(updater.subprocess, 'run', side_effect=RuntimeError('broken import')):
                with self.assertRaises(RuntimeError):
                    updater.install(root, stage, [Path('config.json'), Path('requirements-web.txt')], backup)
            self.assertEqual((root / 'config.json').read_text(), 'old')
            self.assertEqual((root / '.env').read_text(), 'private')

    def test_success_preserves_private_files_and_retains_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();stage=Path(d)/'stage';stage.mkdir();backup=Path(d)/'backup';backup.mkdir()
            (root/'.local').mkdir();(root/'.local'/'notes.db').write_bytes(b'private-notes')
            for directory, value in [(root,'old'),(stage,'new')]:
                (directory/'config.json').write_text(value)
                (directory/'requirements-web.txt').write_text('same')
            with patch.object(updater.subprocess,'run') as run:
                updater.install(root,stage,[Path('config.json'),Path('requirements-web.txt')],backup)
                self.assertEqual(run.call_count,1)  # unchanged dependencies: import check only
            self.assertEqual((root/'config.json').read_text(),'new')
            self.assertEqual((backup/'config.json').read_text(),'old')
            self.assertEqual((root/'.local'/'notes.db').read_bytes(),b'private-notes')

    def test_existing_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();stage=Path(d)/'stage';stage.mkdir();backup=Path(d)/'backup';backup.mkdir()
            outside=Path(d)/'private';outside.write_text('private')
            try:(root/'config.json').symlink_to(outside)
            except OSError:self.skipTest('Symlink creation is not available on this runner')
            (stage/'config.json').write_text('new')
            with self.assertRaises(ValueError):updater.install(root,stage,[Path('config.json')],backup)
            self.assertEqual(outside.read_text(),'private')

    def test_system_symlink_above_root_does_not_block_update(self):
        with tempfile.TemporaryDirectory() as d:
            real=Path(d)/'real';real.mkdir();alias=Path(d)/'alias'
            try:alias.symlink_to(real,target_is_directory=True)
            except OSError:self.skipTest('Symlink creation is not available on this runner')
            root=alias/'root';root.mkdir();stage=Path(d)/'stage';stage.mkdir();backup=Path(d)/'backup';backup.mkdir()
            for directory,value in ((root,'old'),(stage,'new')):
                (directory/'config.json').write_text(value)
                (directory/'requirements-web.txt').write_text('same')
            with patch.object(updater.subprocess,'run'):
                updater.install(root,stage,[Path('config.json'),Path('requirements-web.txt')],backup)
            self.assertEqual((root/'config.json').read_text(),'new')

class UpdateWebTests(unittest.TestCase):
    def test_update_requires_login_and_desktop_and_idle(self):
        from mailnotes.web import create_app
        with tempfile.TemporaryDirectory() as d:
            app=create_app(data_root=Path(d));client=app.test_client()
            self.assertIn(client.post('/api/desktop/update',json={}).status_code,(401,403))
            csrf=client.get('/api/session').get_json()['csrf']
            csrf=client.post('/api/setup',json={'password':'private-test-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
            headers={'X-CSRF-Token':csrf}
            self.assertEqual(client.post('/api/desktop/update',json={},headers=headers).status_code,400)
            app.extensions['desktop_shutdown']=lambda:None
            with app.extensions['admin'].run_lock:
                self.assertEqual(client.post('/api/desktop/update',json={},headers=headers).status_code,409)
            with patch('mailnotes.web.subprocess.Popen') as launch:
                self.assertEqual(client.post('/api/desktop/update',json={},headers=headers).status_code,200)
                self.assertTrue(launch.called)
            self.assertIn('Cập nhật tool',client.get('/').get_data(as_text=True))
