import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from mailnotes.admin import Admin, private_json
from mailnotes.archive import component
from mailnotes.documents import pdf_message
from mailnotes.core import process
from mailnotes.web import create_app


def pdf(text=None, mixed=False):
    writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
    if text:
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 50 700 Td ('+text+') Tj ET').encode())
        page[NameObject('/Contents')]=writer._add_object(stream)
    if mixed:writer.add_blank_page(width=600,height=800)
    result=io.BytesIO();writer.write(result);return result.getvalue()


class MarkdownArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.admin=Admin(Path(__file__).resolve().parent.parent,self.root)
        config=self.admin.config();config['rules']=[{'category':name,'description':'Test','keywords':[]} for name in ('Kinh tế','Ngân sách')]
        config['classification_mode']='ai';config['summary'].update(mode='openai',ai_consent=True)
        self.admin.save_settings(config)
        private_json(self.admin.key_path('deepseek'),{'key':'test-key'})

    def tearDown(self):self.temp.cleanup()

    def test_markdown_multigroup_export_dedup_and_manual_group_sync(self):
        result={'categories':['Kinh tế','Ngân sách'],'summary':'Submit report before 20 October.','confidence':.95,'needs_review':False,'review_reason':''}
        response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}]}
        raw=pdf('Report due 20 October. Send monthly statistics before the deadline.')
        with patch('mailnotes.core.request_json',return_value=response) as api:
            self.assertEqual(self.admin.process_pdf(raw,'report.pdf',source='ai'),1)
            self.assertEqual(self.admin.process_pdf(raw,'report.pdf',source='ai'),0)
            self.assertEqual(self.admin.process_pdf(raw,'report.pdf',reprocess=True,source='ai'),1)
            self.assertEqual(api.call_count,1)
            sent=json.loads(api.call_args.kwargs['data']['messages'][1]['content'])['document']
            markdown=next((self.root/'ai/Markdown').glob('*.md'))
            self.assertEqual(sent,markdown.read_text())
            self.assertEqual(markdown.stat().st_mode&0o777,0o600)
            copies=list((self.root/'ai/Theo-nhom').glob('*/*.md'));self.assertEqual(len(copies),2)
            pdf_copies=list((self.root/'ai/Theo-nhom').glob('*/*.pdf'));self.assertEqual(len(pdf_copies),2)
            self.assertTrue(all(path.read_bytes()==raw for path in pdf_copies))
            pdf_copies[0].unlink()  # Existing installs gain grouped PDFs on first notebook read.
            self.assertIn('Submit report',copies[0].read_text())
            self.assertIn('monthly statistics',copies[0].read_text())
            note=self.admin.notes('ai')['notes'][0]
            self.assertTrue(pdf_copies[0].is_file())
            self.assertEqual({item['path'] for item in note['local_pdf_paths']},{str(path) for path in pdf_copies})
            notebook=next((self.root/'ai/notebooks').glob('*.md')).read_text()
            self.assertIn('PDF trên máy',notebook)
            self.assertIn(str(pdf_copies[0]).replace('_','\\_'),notebook)
            self.admin.edit_categories('ai',note['id'],['Ngân sách'])
            self.assertEqual(len(list((self.root/'ai/Theo-nhom').glob('*/*.md'))),1)
            self.assertEqual(len(list((self.root/'ai/Theo-nhom').glob('*/*.pdf'))),1)
            self.assertEqual(api.call_count,1)
            self.assertEqual(len(list((self.root/'ai/files').glob('*.pdf'))),1)

    def test_scan_is_saved_for_review_without_ocr_or_ai(self):
        config=self.admin.runtime_config('ai');config['pdf_ocr']=True
        with patch('mailnotes.documents.subprocess.run',side_effect=AssertionError('OCR must not run')),patch('mailnotes.core.request_json') as api:
            document=pdf_message(pdf(),'scan.pdf',config,id='scan1',sender='AI',received_at='2026-10-16T08:00:00+07:00')
            self.assertEqual(process([document],config,'ai'),1)
            api.assert_not_called()
        self.assertEqual(self.admin.notes('ai')['notes'][0]['categories'],['Cần xem lại'])
        self.assertEqual(len(list((self.root/'ai/Can-xem-lai').glob('*.md'))),1)
        self.assertEqual(len(list((self.root/'ai/Can-xem-lai').glob('*.pdf'))),1)
        self.assertIn('Chưa đọc được chữ',next((self.root/'ai/Can-xem-lai').glob('*.md')).read_text())

    def test_mixed_pdf_reports_unread_image_pages_and_names_cannot_escape(self):
        config=self.admin.runtime_config('pdf')
        document=pdf_message(pdf('Report with one text page.',mixed=True),'mixed.pdf',config,id='mixed',sender='PDF',received_at='2026-10-16T08:00:00+07:00')
        self.assertIn('1 trang không có lớp chữ',document['review_reason'])
        self.assertNotIn('/',component('../../outside'))
        self.assertNotEqual(component('A/B'),component('A\\B'))
        self.assertLess(len(component('Ngân sách nhà nước ' * 40).encode('utf-8')),200)

    def test_markdown_download_and_local_folder_action(self):
        config=self.admin.config();config['summary']['mode']='extractive';config['classification_mode']='rules';self.admin.save_settings(config)
        self.admin.process_pdf(pdf('Text available in Markdown.'),'text.pdf',source='ai')
        app=create_app(data_root=self.root);client=app.test_client()
        self.assertEqual(client.get('/api/archive?source=ai').status_code,401)
        csrf=client.get('/api/session').get_json()['csrf']
        csrf=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
        note=client.get('/api/notes?source=ai').get_json()['notes'][0]
        self.assertGreaterEqual(len(note['local_pdf_paths']),1)
        self.assertTrue(Path(note['local_pdf_paths'][0]['path']).is_file())
        response=client.get('/api/document',query_string={'source':'ai','id':note['id'],'format':'markdown'})
        self.assertEqual(response.status_code,200);self.assertIn('Text available',response.get_data(as_text=True));response.close()
        self.assertEqual(client.get('/api/archive?source=../../outside').status_code,400)
        for platform, command in (('linux','xdg-open'),('darwin','open')):
            with self.subTest(platform=platform),patch('sys.platform',platform),patch('subprocess.Popen') as opened:
                response=client.post('/api/archive?source=ai',json={},headers={'X-CSRF-Token':csrf})
                self.assertEqual(response.status_code,200)
                self.assertEqual(opened.call_args.args[0],[command,str(self.root/'ai')])
