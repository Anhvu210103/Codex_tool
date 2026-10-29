import json
import tempfile
import unittest
from pathlib import Path

from mailnotes.admin import Admin, private_json
from mailnotes.web import create_app


class GreenNodeProviderTests(unittest.TestCase):
    def test_old_provider_config_migrates_to_vngcloud_without_reusing_prices_or_consent(self):
        base=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=Admin(base,root).config()
            original['summary'].update(provider='gemini',model='gemini-flash-latest',mode='openai',ai_consent=True,
                                       pricing={'input_per_million':99})
            original['rules']=[{'category':'Nhóm riêng','description':'Giữ nguyên','keywords':[],'senders':[]}]
            original.update(schedule_enabled=True,folder_inbox_enabled=True)
            private_json(root/'admin/settings.json',original)
            migrated=Admin(base,root).config()
            self.assertEqual(migrated['summary']['provider'],'vngcloud')
            self.assertEqual(migrated['summary']['model'],'deepseek/deepseek-v4-flash')
            self.assertFalse(migrated['summary']['ai_consent'])
            self.assertEqual(migrated['summary']['mode'],'openai')
            self.assertIsNone(migrated['summary']['pricing']['input_per_million'])
            self.assertFalse(migrated['schedule_enabled'])
            self.assertFalse(migrated['folder_inbox_enabled'])
            self.assertEqual(migrated['rules'],original['rules'])

    def test_api_rejects_unknown_provider_and_html_uses_vngcloud(self):
        with tempfile.TemporaryDirectory() as directory:
            client=create_app(data_root=Path(directory)).test_client()
            csrf=client.get('/api/session').get_json()['csrf']
            csrf=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
            response=client.post('/api/ai-key',json={'provider':'gemini','key':'unused'},headers={'X-CSRF-Token':csrf})
            self.assertEqual(response.status_code,400)
            response=client.get('/static/admin.js');page=response.get_data(as_text=True);response.close()
            self.assertNotIn('Gemini',page)
            self.assertNotIn('OpenAI',page)
            self.assertIn('GreenNode',page)
