import base64
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter
from mailnotes.admin import Admin
from mailnotes.core import process
from mailnotes.documents import pdf_message
from mailnotes.gemini import generate, models, call
from mailnotes.gmail import messages
from mailnotes.web import create_app


def gemini_response(content=None):
    result={'categories':['Work'],'summary':'Gửi báo cáo trước 20/10.','confidence':.9,'needs_review':False,'review_reason':''}
    return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':content or json.dumps(result,ensure_ascii=False)}]}}],
            'usageMetadata':{'promptTokenCount':1000,'cachedContentTokenCount':200,'candidatesTokenCount':80,'thoughtsTokenCount':20,'totalTokenCount':1100}}


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        writer=PdfWriter();writer.add_blank_page(width=600,height=800);output=io.BytesIO();writer.write(output);self.pdf=output.getvalue()
        self.config={'data_dir':str(self.root/'pdf'),'classification_mode':'ai','_api_key':'test-gemini-key','pdf_ocr':True,
                     'rules':[{'category':'Work','description':'Việc cần làm'}],
                     'summary':{'provider':'gemini','mode':'openai','model':'gemini-flash-latest',
                                'pricing':{'input_per_million':2,'cached_input_per_million':.2,'output_per_million':8}}}

    def tearDown(self):self.temporary.cleanup()

    def document(self):
        return pdf_message(self.pdf,'scan.pdf',self.config,id='scan1',sender='Upload',received_at='2026-10-15T08:00:00+07:00')

    def test_scan_sent_as_pdf_without_local_extraction_and_usage_includes_thinking(self):
        with patch('mailnotes.documents.pdf_text',side_effect=AssertionError('local OCR must not run')):
            document=self.document()
        self.assertEqual(document['body'],'');self.assertEqual(document['review_reason'],'')
        with patch('mailnotes.gemini.call',return_value=(gemini_response(),{})) as request:
            self.assertEqual(process([document],self.config,'pdf'),1)
            self.assertEqual(process([document],self.config,'pdf'),0)
            self.assertEqual(process([{**document,'id':'same-pdf-other-note'}],self.config,'pdf'),1)
            self.assertEqual(request.call_count,1)
            parts=request.call_args.kwargs['data']['contents'][0]['parts']
            self.assertEqual(base64.b64decode(parts[1]['inlineData']['data']),self.pdf)
            self.assertEqual(parts[1]['inlineData']['mimeType'],'application/pdf')
            self.assertIn(':generateContent',request.call_args.args[0])
        admin=Admin(Path(__file__).resolve().parent.parent,self.root)
        stats=admin.usage()['totals']
        self.assertEqual(stats['input_tokens'],1000);self.assertEqual(stats['output_tokens'],100)
        self.assertEqual(stats['total_tokens'],1100);self.assertEqual(stats['local_cache_hits'],1)
        self.assertAlmostEqual(stats['estimated_usd'],.00244)
        self.assertEqual(admin.notes('pdf')['notes'][0]['categories'],['Work'])

    def test_gmail_scan_attachment_goes_to_gemini_without_ocr(self):
        encoded=base64.urlsafe_b64encode(self.pdf).decode().rstrip('=')
        detail={'id':'mail1','internalDate':'1792026000000','payload':{'headers':[{'name':'From','value':'office@example.com'}],'parts':[{'mimeType':'application/pdf','filename':'scan.pdf','body':{'attachmentId':'pdf1','size':len(self.pdf)}}]}}
        def gmail(url,**kwargs):
            if '/attachments/' in url:return {'data':encoded}
            if '?format=full' in url:return detail
            return {'messages':[{'id':'mail1'}]}
        config={**self.config,'data_dir':str(self.root/'gmail'),'gmail_query':'label:test','gmail_pdf':True}
        with patch('mailnotes.gmail.access_token',return_value='fake-gmail-token'),patch('mailnotes.gmail.request_json',side_effect=gmail),patch('mailnotes.documents.pdf_text',side_effect=AssertionError('must not OCR')),patch('mailnotes.gemini.call',return_value=(gemini_response(),{})) as request:
            self.assertEqual(process(messages(config,'credentials','token'),config,'gmail'),1)
            parts=request.call_args.kwargs['data']['contents'][0]['parts']
            self.assertEqual(base64.b64decode(parts[1]['inlineData']['data']),self.pdf)
        with sqlite3.connect(self.root/'gmail/notes.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT origin_id FROM notes').fetchone()[0],'mail1')

    def test_large_pdf_uses_upload_api_and_deletes_remote_file(self):
        document=self.document()
        uploaded='files/test-file'
        responses=[({}, {'X-Goog-Upload-URL':'https://generativelanguage.googleapis.com/upload/test'}),
                   ({'file':{'name':uploaded,'state':'PROCESSING'}},{}),
                   ({'name':uploaded,'state':'ACTIVE','uri':'https://generativelanguage.googleapis.com/v1beta/'+uploaded},{}),
                   (gemini_response(),{}), ({},{})]
        with patch('mailnotes.gemini.INLINE_LIMIT',1),patch('mailnotes.gemini.time.sleep'),patch('mailnotes.gemini.call',side_effect=responses) as request:
            result=generate(document,self.config,'system',{},'test-key')
        self.assertEqual(request.call_count,5)
        self.assertEqual(request.call_args.kwargs['method'],'DELETE')
        self.assertEqual(request.call_args.args[0],'/v1beta/files/test-file')
        body=request.call_args_list[3].kwargs['data']
        self.assertIn('fileData',body['contents'][0]['parts'][1])
        self.assertEqual(result['usage']['completion_tokens'],100)

    def test_upload_url_cannot_send_key_to_other_host(self):
        with patch('urllib.request.urlopen') as request:
            with self.assertRaises(ValueError):call('https://other.example/upload','test-key',raw=b'PDF')
            request.assert_not_called()

    def test_remote_cleanup_attempted_when_generation_fails(self):
        document=self.document()
        responses=[({}, {'X-Goog-Upload-URL':'https://generativelanguage.googleapis.com/upload/test'}),
                   ({'file':{'name':'files/test-file','state':'ACTIVE','uri':'https://generativelanguage.googleapis.com/v1beta/files/test-file'}},{}),
                   RuntimeError('request failed'), ({},{})]
        with patch('mailnotes.gemini.INLINE_LIMIT',1),patch('mailnotes.gemini.call',side_effect=responses) as request:
            with self.assertRaises(RuntimeError):generate(document,self.config,'system',{},'test-key')
        self.assertEqual(request.call_args.kwargs['method'],'DELETE')

    def test_invalid_json_still_records_usage_and_no_note(self):
        with patch('mailnotes.gemini.call',return_value=(gemini_response('not JSON'),{})):
            with self.assertRaises(ValueError):process([self.document()],self.config,'pdf')
        with sqlite3.connect(self.root/'pdf/notes.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notes').fetchone()[0],0)
            self.assertEqual(connection.execute('SELECT total_tokens FROM ai_usage').fetchone()[0],1100)

    def test_web_key_check_and_reprocess_old_local_scan_as_cloud(self):
        app=create_app(data_root=self.root);client=app.test_client()
        token=client.get('/api/session').get_json()['csrf']
        setup=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':token})
        headers={'X-CSRF-Token':setup.get_json()['csrf']}
        client.post('/api/pdf',data={'file':(io.BytesIO(self.pdf),'old-scan.pdf')},headers=headers)
        note=client.get('/api/notes?source=pdf').get_json()['notes'][0]
        self.assertEqual(note['categories'],['Cần xem lại'])
        saved=client.post('/api/ai-key',json={'provider':'gemini','key':'test-gemini-key'},headers=headers)
        self.assertEqual(saved.status_code,200)
        self.assertEqual((self.root/'admin/gemini-key.json').stat().st_mode&0o777,0o600)
        config=client.get('/api/settings').get_json();config['classification_mode']='ai';config['summary'].update(provider='gemini',mode='openai',model='gemini-flash-latest',ai_consent=True);config['rules']=[{'category':'Work','description':'Việc cần làm'}]
        self.assertEqual(client.post('/api/settings',json=config,headers=headers).status_code,200)
        with patch('mailnotes.gemini.models',return_value=['gemini-flash-latest']):
            check=client.post('/api/gemini/check',json={},headers=headers)
            self.assertEqual(check.get_json()['models'],['gemini-flash-latest'])
        with patch('mailnotes.documents.pdf_text',side_effect=AssertionError('must not OCR')),patch('mailnotes.gemini.call',return_value=(gemini_response(),{})):
            result=client.post('/api/notes/reprocess',json={'source':'pdf','id':note['id']},headers=headers)
        self.assertEqual(result.status_code,200)
        updated=client.get('/api/notes?source=pdf').get_json()
        self.assertEqual(updated['total'],1);self.assertEqual(updated['notes'][0]['categories'],['Work'])
        self.assertNotIn('test-gemini-key',client.get('/api/settings').get_data(as_text=True))
