import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from mailnotes.web import create_app


class ExtensionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.app=create_app(data_root=self.root);self.client=self.app.test_client()
        csrf=self.client.get('/api/session').get_json()['csrf']
        self.csrf=self.client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
        token=self.client.post('/api/extension/pair',json={},headers={'X-CSRF-Token':self.csrf}).get_json()['token']
        self.headers={'Origin':'chrome-extension://'+'a'*32,'Authorization':'Bearer '+token}

    def tearDown(self):self.temp.cleanup()

    def test_bridge_requires_pair_token_and_extension_origin(self):
        self.assertEqual(self.client.post('/extension/choose',json={}).status_code,403)
        self.assertEqual(self.client.post('/extension/choose',json={},headers={'Origin':self.headers['Origin']}).status_code,401)
        preflight=self.client.options('/extension/choose',headers={'Origin':self.headers['Origin']})
        self.assertEqual(preflight.status_code,204)
        self.assertEqual(preflight.headers['Access-Control-Allow-Origin'],self.headers['Origin'])
        self.client.post('/api/extension/pair',json={},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(self.client.post('/extension/choose',json={},headers=self.headers).status_code,401)

    def test_ai_choice_and_pdf_import_without_exposing_key(self):
        config=self.client.get('/api/settings').get_json();config['summary'].update(mode='openai',ai_consent=True)
        self.client.post('/api/settings',json=config,headers={'X-CSRF-Token':self.csrf})
        self.client.post('/api/ai-key',json={'provider':'deepseek','key':'test-private-key'},headers={'X-CSRF-Token':self.csrf})
        choice={'index':0,'label':'document.pdf','role':'button'}
        with patch('mailnotes.gmail_browser_pilot.select_with_ai',return_value=choice):
            response=self.client.post('/extension/choose',json={'kind':'pdf','candidates':[choice]},headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.get_json()['choice'],choice)
        self.assertNotIn('test-private-key',response.get_data(as_text=True))
        writer=PdfWriter();writer.add_blank_page(width=600,height=800);pdf=io.BytesIO();writer.write(pdf);pdf.seek(0)
        result=self.client.post('/extension/pdf',data={'file':(pdf,'scan.pdf')},headers=self.headers)
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.get('/api/notes?source=pdf').get_json()['total'],1)

    def test_zip_contains_loadable_manifest(self):
        result=self.client.get('/api/extension/download');self.assertEqual(result.status_code,200)
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            self.assertIn('SoGhiChep-AI-Gmail/manifest.json',archive.namelist())
