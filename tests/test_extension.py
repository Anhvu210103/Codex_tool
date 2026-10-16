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
        ping=self.client.post('/extension/ping',json={},headers=self.headers)
        self.assertEqual(ping.status_code,200)
        self.assertEqual(ping.get_json()['app'],'mailnotes-extension')
        self.assertEqual(ping.get_json()['protocol'],1)
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
        upstream={'choices':[{'message':{'content':'{"index":0}'}}],
                  'usage':{'prompt_tokens':10,'completion_tokens':2,'total_tokens':12,'prompt_cache_hit_tokens':0}}
        with patch('mailnotes.gmail_browser_pilot.request_json',return_value=upstream):
            response=self.client.post('/extension/choose',json={'kind':'pdf','candidates':[choice]},headers=self.headers)
        self.assertEqual(response.status_code,200);self.assertEqual(response.get_json()['choice'],choice)
        self.assertNotIn('test-private-key',response.get_data(as_text=True))
        self.assertEqual(self.client.get('/api/usage').get_json()['recent'][0]['source'],'ai')
        writer=PdfWriter();writer.add_blank_page(width=600,height=800);pdf=io.BytesIO();writer.write(pdf);pdf.seek(0);pdf_bytes=pdf.getvalue()
        result=self.client.post('/extension/pdf',data={'file':(pdf,'scan.pdf')},headers=self.headers)
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.get_json()['categories'],['Cần xem lại'])
        self.assertEqual(self.client.get('/api/notes?source=ai').get_json()['total'],1)
        self.assertEqual(self.client.get('/api/notes?source=pdf').get_json()['total'],0)
        note=self.client.get('/api/notes?source=ai').get_json()['notes'][0]
        self.assertEqual(note['source'],'ai')
        self.assertTrue(note['id'].startswith('ai:'))
        document=self.client.get('/api/document',query_string={'source':'ai','id':note['id']})
        self.assertEqual(document.status_code,200);document.close()
        exported=self.client.get('/api/export',query_string={'source':'ai','day':note['day']})
        self.assertEqual(exported.status_code,200)
        self.assertIn('AI thao tác',exported.get_data(as_text=True))
        edited=self.client.post('/api/notes/categories',json={'source':'ai','id':note['id'],'categories':[config['rules'][0]['category']]},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(edited.status_code,200)
        self.assertEqual(self.client.get('/api/dashboard?source=ai').get_json()['total_notes'],1)
        duplicate=self.client.post('/extension/pdf',data={'file':(io.BytesIO(pdf_bytes),'scan.pdf')},headers=self.headers)
        self.assertEqual(duplicate.status_code,200)
        self.assertEqual(duplicate.get_json()['added'],0)
        self.assertEqual(self.client.get('/api/notes?source=ai').get_json()['notes'][0]['categories'],[config['rules'][0]['category']])
        reread=self.client.post('/api/notes/reprocess',json={'source':'ai','id':note['id']},headers={'X-CSRF-Token':self.csrf})
        self.assertEqual(reread.status_code,200)
        self.assertEqual(self.client.get('/api/notes?source=ai').get_json()['total'],1)

    def test_zip_contains_loadable_manifest(self):
        result=self.client.get('/api/extension/download');self.assertEqual(result.status_code,200)
        with zipfile.ZipFile(io.BytesIO(result.data)) as archive:
            self.assertIn('SoGhiChep-AI-Gmail/manifest.json',archive.namelist())

    def test_local_import_reads_only_the_download_directory(self):
        downloads=self.root/'Downloads';downloads.mkdir()
        writer=PdfWriter();writer.add_blank_page(width=600,height=800)
        with (downloads/'scan.pdf').open('wb') as stream:writer.write(stream)
        with patch('mailnotes.linux_downloads.download_directory',return_value=downloads),patch('sys.platform','linux'):
            denied=self.client.post('/extension/import-local',json={'path':str(self.root/'private.pdf')},headers=self.headers)
            self.assertEqual(denied.get_json(),{'available':False})
            result=self.client.post('/extension/import-local',json={'path':str(downloads/'scan.pdf')},headers=self.headers)
        self.assertEqual(result.status_code,200)
        self.assertTrue(result.get_json()['available'])
        self.assertEqual(result.get_json()['source'],'ai')
        self.assertEqual(result.get_json()['categories'],['Cần xem lại'])
        self.assertEqual(self.client.get('/api/notes?source=ai').get_json()['total'],1)
