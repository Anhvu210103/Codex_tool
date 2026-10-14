import base64
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from mailnotes.core import process
from mailnotes.documents import pdf_text, pdf_message
from mailnotes.gmail import messages
from mailnotes.web import create_app


def sample_pdf(text='Report due 20 October. Send the monthly statistics before the deadline.'):
    writer = PdfWriter()
    page = writer.add_blank_page(width=600, height=800)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject(); stream.set_data(('BT /F1 12 Tf 50 700 Td (' + text + ') Tj ET').encode())
    page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO(); writer.write(output)
    return output.getvalue()


def ai_result(categories=None, confidence=.9, **extra):
    result = {'categories': categories or ['Work'], 'summary': 'Send the report before 20 October.', 'confidence': confidence, 'needs_review': False, 'review_reason': '', **extra}
    return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(result)}}]}


class DocumentAITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = {'data_dir':str(self.root), 'classification_mode':'ai', '_api_key':'test-key',
                       'rules':[{'category':'Work','description':'Requests requiring action'}, {'category':'Legal','description':'Legal regulations'}],
                       'summary':{'mode':'openai','provider':'deepseek','model':'deepseek-chat','max_input_chars':12000}}
        self.mail = {'id':'1','sender':'office','subject':'Report','body':'Please send the monthly report before 20 October.', 'received_at':'2026-10-14T08:00:00+07:00'}

    def tearDown(self):
        self.temporary.cleanup()

    def row(self):
        with sqlite3.connect(self.root/'notes.sqlite3') as connection:
            return connection.execute('SELECT categories,summary,review_reason FROM notes ORDER BY id').fetchone()

    def test_single_ai_call_returns_multiple_groups_summary_and_cache(self):
        with patch('mailnotes.core.request_json',return_value=ai_result(['Work','Legal'])) as request:
            self.assertEqual(process([self.mail],self.config,'gmail'),1)
            self.assertEqual(process([self.mail],self.config,'gmail'),0)
            second={**self.mail,'id':'2'}
            self.assertEqual(process([second],self.config,'gmail'),1)
            self.assertEqual(request.call_count,1)
            self.assertEqual(request.call_args.args[0],'https://api.deepseek.com/chat/completions')
            self.assertEqual(request.call_args.kwargs['data']['response_format'],{'type':'json_object'})
        self.assertEqual(json.loads(self.row()[0]),['Work','Legal'])
        self.assertIn('20 October',self.row()[1])

    def test_unknown_or_uncertain_categories_go_to_review(self):
        for result in [ai_result(['Invented']),ai_result(['Work'],confidence=.4),ai_result(['Work'],needs_review=True)]:
            with tempfile.TemporaryDirectory() as directory:
                config={**self.config,'data_dir':directory}
                with patch('mailnotes.core.request_json',return_value=result):
                    process([self.mail],config,'gmail')
                with sqlite3.connect(Path(directory)/'notes.sqlite3') as connection:
                    groups=json.loads(connection.execute('SELECT categories FROM notes').fetchone()[0])
                self.assertEqual(groups,['Cần xem lại'])

    def test_malformed_ai_response_not_saved_and_retry_works(self):
        bad={'choices':[{'message':{'content':'not JSON'}}]}
        with patch('mailnotes.core.request_json',return_value=bad):
            with self.assertRaises(ValueError):process([self.mail],self.config,'gmail')
        with patch('mailnotes.core.request_json',return_value=ai_result()):
            self.assertEqual(process([self.mail],self.config,'gmail'),1)

    def test_truncated_input_keeps_review_warning(self):
        self.config['summary']['max_input_chars']=20
        with patch('mailnotes.core.request_json',return_value=ai_result()) as request:
            process([self.mail],self.config,'gmail')
        self.assertIn('Cần xem lại',json.loads(self.row()[0]))
        self.assertIn('giới hạn',self.row()[2])
        payload=json.loads(request.call_args.kwargs['data']['messages'][1]['content'])
        self.assertEqual(len(payload['document']),20)

    def test_read_real_pdf_and_scan_review_without_ai(self):
        data=sample_pdf()
        text,warning=pdf_text(data)
        self.assertIn('20 October',text);self.assertEqual(warning,'')
        document=pdf_message(data,'test.pdf',self.config,id='pdf1',sender='Upload',received_at=self.mail['received_at'])
        with patch('mailnotes.core.request_json',return_value=ai_result()) as request:
            self.assertEqual(process([document],self.config,'pdf'),1)
            self.assertEqual(request.call_count,1)
        writer=PdfWriter();writer.add_blank_page(width=600,height=800);output=io.BytesIO();writer.write(output)
        scan=pdf_message(output.getvalue(),'scan.pdf',self.config,id='scan',sender='Upload',received_at=self.mail['received_at'])
        with patch('mailnotes.core.request_json',side_effect=AssertionError('must not send blank scan to AI')):
            self.assertEqual(process([scan],self.config,'pdf'),1)
        self.assertTrue((self.root/'files'/ (document['file_hash']+'.pdf')).exists())

    def test_gmail_pdf_attachment_and_skip_download_after_processing(self):
        data=sample_pdf();encoded=base64.urlsafe_b64encode(data).decode().rstrip('=')
        detail={'id':'email1','internalDate':'1791939600000','payload':{'headers':[{'name':'From','value':'office@example.com'}], 'parts':[{'mimeType':'application/pdf','filename':'report.pdf','body':{'attachmentId':'attachment1','size':len(data)}}]}}
        def response(url,**kwargs):
            if '/attachments/' in url:return {'data':encoded}
            if '?format=full' in url:return detail
            return {'messages':[{'id':'email1'}]}
        config={**self.config,'gmail_query':'label:test'}
        with patch('mailnotes.gmail.access_token',return_value='test-access'),patch('mailnotes.gmail.request_json',side_effect=response) as request:
            incoming=list(messages(config,'credentials','token'))
            self.assertEqual(len(incoming),1);self.assertIn('20 October',incoming[0]['body']);self.assertEqual(incoming[0]['origin_id'],'email1')
            with patch('mailnotes.core.request_json',return_value=ai_result()):process(incoming,config,'gmail')
            calls=request.call_count
            self.assertEqual(list(messages(config,'credentials','token')),[])
            self.assertEqual(request.call_count-calls,2) # list + details, no PDF download

    def test_legacy_schema_migration_preserves_old_notes(self):
        with sqlite3.connect(self.root/'notes.sqlite3') as connection:
            connection.execute('CREATE TABLE notes (id TEXT PRIMARY KEY, sender TEXT, subject TEXT, categories TEXT, summary TEXT, received_at TEXT, day TEXT, source TEXT, content_hash TEXT)')
            connection.execute('INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?)', ('gmail:old','sender','Old note','["Work"]','Saved summary',self.mail['received_at'],'2026-10-14','gmail','hash'))
        with patch('mailnotes.core.request_json',return_value=ai_result()):
            process([self.mail],self.config,'gmail')
        with sqlite3.connect(self.root/'notes.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT summary FROM notes WHERE id="gmail:old"').fetchone()[0],'Saved summary')
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notes').fetchone()[0],2)

    def test_reprocess_updates_pdf_without_duplicate_row(self):
        document=pdf_message(sample_pdf(),'test.pdf',self.config,id='pdf1',sender='Upload',received_at=self.mail['received_at'])
        with patch('mailnotes.core.request_json',return_value=ai_result()):
            process([document],self.config,'pdf')
        self.config['rules']=[{'category':'New','description':'New group'}]
        self.config['_reprocess_id']='pdf:pdf1'
        with patch('mailnotes.core.request_json',return_value=ai_result(['New'])) as request:
            self.assertEqual(process([document],self.config,'pdf'),1)
            self.assertEqual(request.call_count,1)
        with sqlite3.connect(self.root/'notes.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notes').fetchone()[0],1)
        self.assertEqual(json.loads(self.row()[0]),['New'])

    def test_web_upload_edit_and_legacy_schema_migration(self):
        app=create_app(data_root=self.root/'web');app.config['TESTING']=True;client=app.test_client()
        csrf=client.get('/api/session').get_json()['csrf']
        setup=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf})
        headers={'X-CSRF-Token':setup.get_json()['csrf']}
        upload=client.post('/api/pdf',data={'file':(io.BytesIO(sample_pdf()),'report.pdf')},headers=headers)
        self.assertEqual(upload.status_code,200);self.assertEqual(upload.get_json()['added'],1)
        note=client.get('/api/notes?source=pdf').get_json()['notes'][0]
        download=client.get('/api/document?source=pdf&id='+note['id'])
        self.assertEqual(download.status_code,200);self.assertTrue(download.get_data().startswith(b'%PDF-'));download.close()
        edit=client.post('/api/notes/categories',json={'source':'pdf','id':note['id'],'categories':['Cần xem lại']},headers=headers)
        self.assertEqual(edit.status_code,200)
        updated=client.get('/api/notes?source=pdf').get_json()['notes'][0]
        self.assertEqual(updated['categories'],['Cần xem lại'])
        export=client.get('/api/export?source=pdf&day='+note['day'])
        self.assertIn('Cần xem lại',export.get_data(as_text=True))
        invalid=client.post('/api/notes/categories',json={'source':'pdf','id':note['id'],'categories':['unknown']},headers=headers)
        self.assertEqual(invalid.status_code,400)
        private=app.extensions['admin'].private
        client.post('/api/ai-key',json={'provider':'deepseek','key':'test-deepseek-secret'},headers=headers)
        self.assertEqual((private/'deepseek-key.json').stat().st_mode&0o777,0o600)
        self.assertNotIn('test-deepseek-secret',client.get('/api/settings').get_data(as_text=True))
