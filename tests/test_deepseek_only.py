import json
import tempfile
import unittest
from pathlib import Path

from mailnotes.admin import Admin, private_json
from mailnotes.web import create_app


class DeepSeekOnlyTests(unittest.TestCase):
    def test_old_provider_config_migrates_without_reusing_prices_or_consent(self):
        base=Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            original=Admin(base,root).config()
            original['summary'].update(provider='gemini',model='gemini-flash-latest',mode='openai',ai_consent=True,
                                       pricing={'input_per_million':99})
            original['rules']=[{'category':'Nhóm riêng','description':'Giữ nguyên','keywords':[],'senders':[]}]
            private_json(root/'admin/settings.json',original)
            migrated=Admin(base,root).config()
            self.assertEqual(migrated['summary']['provider'],'deepseek')
            self.assertEqual(migrated['summary']['model'],'deepseek-chat')
            self.assertFalse(migrated['summary']['ai_consent'])
            self.assertEqual(migrated['summary']['mode'],'extractive')
            self.assertIsNone(migrated['summary']['pricing']['input_per_million'])
            self.assertEqual(migrated['rules'],original['rules'])

    def test_api_rejects_other_provider_and_html_only_offers_deepseek(self):
        with tempfile.TemporaryDirectory() as directory:
            client=create_app(data_root=Path(directory)).test_client()
            csrf=client.get('/api/session').get_json()['csrf']
            csrf=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
            response=client.post('/api/ai-key',json={'provider':'gemini','key':'unused'},headers={'X-CSRF-Token':csrf})
            self.assertEqual(response.status_code,400)
            page=client.get('/').get_data(as_text=True)
            self.assertNotIn('Gemini',page)
            self.assertNotIn('OpenAI',page)
            self.assertIn('DeepSeek',page)
