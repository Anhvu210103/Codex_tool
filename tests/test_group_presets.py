import tempfile
import unittest
from pathlib import Path

from mailnotes.web import create_app


class GroupPresetTests(unittest.TestCase):
    def test_presets_cover_public_administration_and_do_not_replace_saved_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(data_root=Path(directory))
            client = app.test_client()
            self.assertEqual(client.get('/api/group-presets').status_code, 401)
            csrf = client.get('/api/session').get_json()['csrf']
            setup = client.post('/api/setup', json={'password':'test-private-password'},
                                headers={'X-CSRF-Token':csrf})
            self.assertEqual(setup.status_code, 200)
            settings = client.get('/api/settings').get_json()
            settings['rules'] = [{'category':'Nhóm riêng','description':'Chỉ tài liệu khách chọn','keywords':[],'senders':[]}]
            self.assertEqual(client.post('/api/settings', json=settings,
                                         headers={'X-CSRF-Token':setup.get_json()['csrf']}).status_code, 200)
            presets = client.get('/api/group-presets').get_json()
            names = [rule['category'] for rule in presets]
            self.assertEqual(len(names), len(set(names)))
            self.assertGreaterEqual(len(names), 12)
            self.assertIn('Tài chính và ngân sách', names)
            self.assertIn('Đấu thầu và mua sắm công', names)
            self.assertIn('Văn bản pháp luật', names)
            self.assertEqual(client.get('/api/settings').get_json()['rules'][0]['category'], 'Nhóm riêng')
