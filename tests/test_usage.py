import io
import base64
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mailnotes.admin import Admin, private_json
from mailnotes.core import process
from mailnotes.web import create_app
from test_documents_ai import ai_result, sample_pdf


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.admin=Admin(Path(__file__).resolve().parent.parent,self.root)
        self.config={'data_dir':str(self.root/'gmail'),'classification_mode':'ai','_api_key':'test-key',
                     'rules':[{'category':'Work','description':'Requests'}],
                     'summary':{'provider':'deepseek','mode':'openai','model':'deepseek-chat',
                                'pricing':{'input_per_million':2,'cached_input_per_million':.2,'output_per_million':8}}}
        self.mail={'id':'1','sender':'office','subject':'Report','body':'Please send the report before 20 October.','received_at':'2026-10-14T08:00:00+07:00'}

    def tearDown(self):self.temporary.cleanup()

    def test_reported_tokens_cost_cache_and_price_snapshot(self):
        response=ai_result();response['usage']={'prompt_tokens':1000,'prompt_cache_hit_tokens':200,'completion_tokens':100,'total_tokens':1100}
        with patch('mailnotes.core.request_json',return_value=response) as api:
            process([self.mail],self.config,'gmail')
            process([self.mail],self.config,'gmail')
            self.config['summary']['pricing']['output_per_million']=100
            process([{**self.mail,'id':'2'}],self.config,'gmail')
            self.assertEqual(api.call_count,1)
        usage=self.admin.usage();total=usage['totals']
        self.assertEqual(total['api_calls'],1);self.assertEqual(total['local_cache_hits'],1)
        self.assertEqual(total['input_tokens'],1000);self.assertEqual(total['cached_tokens'],200)
        self.assertEqual(total['output_tokens'],100);self.assertEqual(total['total_tokens'],1100)
        self.assertAlmostEqual(total['estimated_usd'],.00244)
        self.assertEqual(total['unpriced_calls'],0)

    def test_missing_usage_is_unknown_not_free(self):
        with patch('mailnotes.core.request_json',return_value=ai_result()):process([self.mail],self.config,'gmail')
        total=self.admin.usage()['totals']
        self.assertEqual(total['unknown_usage_calls'],1);self.assertEqual(total['unpriced_calls'],1)
        self.assertIsNone(self.admin.usage()['recent'][0]['estimated_usd'])

    def test_invalid_json_still_records_returned_usage(self):
        response={'choices':[{'message':{'content':'bad JSON'}}], 'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30}}
        with patch('mailnotes.core.request_json',return_value=response):
            with self.assertRaises(ValueError):process([self.mail],self.config,'gmail')
        self.assertEqual(self.admin.usage()['totals']['total_tokens'],30)
        with sqlite3.connect(self.root/'gmail/notes.sqlite3') as connection:
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM notes').fetchone()[0],0)

    def test_gmail_reads_attachment_content_and_accounts_usage(self):
        raw=sample_pdf();encoded=base64.urlsafe_b64encode(raw).decode().rstrip('=')
        detail={'id':'email1','internalDate':'1791939600000','payload':{'headers':[{'name':'From','value':'office@example.com'}], 'parts':[{'mimeType':'text/plain','body':{'data':base64.urlsafe_b64encode(b'Please see the attached document.').decode()}}, {'mimeType':'application/pdf','filename':'report.pdf','body':{'attachmentId':'pdf1','size':len(raw)}}]}}
        def gmail_response(url,**kwargs):
            if '/attachments/' in url:return {'data':encoded}
            if '?format=full' in url:return detail
            return {'messages':[{'id':'email1'}]}
        settings=self.admin.config();settings.update(source='gmail',classification_mode='ai',gmail_pdf=True,gmail_filter={'period':'all'})
        settings['rules']=self.config['rules'];settings['summary']={**self.config['summary'],'ai_consent':True}
        self.admin.save_settings(settings)
        private_json(self.admin.key_path('deepseek'),{'key':'test-key'})
        response=ai_result();response['usage']={'prompt_tokens':1000,'prompt_cache_hit_tokens':200,'completion_tokens':100,'total_tokens':1100}
        with patch('mailnotes.gmail.access_token',return_value='fake-token'),patch('mailnotes.gmail.request_json',side_effect=gmail_response),patch('mailnotes.core.request_json',return_value=response) as ai:
            self.assertTrue(self.admin.start_run('gmail'))
            with self.admin.run_lock:pass
            self.assertEqual(self.admin.status()['last_added'],1)
            self.assertIsNone(self.admin.status()['error'])
            payload=json.loads(ai.call_args.kwargs['data']['messages'][1]['content'])
            self.assertIn('20 October',payload['document'])
            self.assertNotIn('Please see the attached',payload['document'])
            note=self.admin.notes('gmail')['notes'][0]
            self.assertEqual(note['subject'],'report.pdf');self.assertEqual(note['origin_id'],'email1')
            self.assertIn('20 October',note['summary'])
            self.assertEqual(self.admin.usage()['totals']['total_tokens'],1100)
            self.assertEqual(self.admin.reprocess_note('gmail',note['id']),1)
            self.assertEqual(ai.call_count,1)
            self.assertEqual(self.admin.notes('gmail')['total'],1)
            self.assertEqual(self.admin.usage()['totals']['local_cache_hits'],1)

    def test_api_auth_prices_and_pdf_read_again(self):
        app=create_app(data_root=self.root);app.config['TESTING']=True;client=app.test_client()
        self.assertEqual(client.get('/api/usage').status_code,401)
        csrf=client.get('/api/session').get_json()['csrf']
        setup=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf})
        headers={'X-CSRF-Token':setup.get_json()['csrf']}
        config=client.get('/api/settings').get_json();config['summary']['pricing']={'input_per_million':None,'cached_input_per_million':None,'output_per_million':-1}
        self.assertEqual(client.post('/api/settings',json=config,headers=headers).status_code,400)
        upload=client.post('/api/pdf',data={'file':(io.BytesIO(sample_pdf()),'report.pdf')},headers=headers)
        self.assertEqual(upload.status_code,200)
        note=client.get('/api/notes?source=pdf').get_json()['notes'][0]
        reread=client.post('/api/notes/reprocess',json={'source':'pdf','id':note['id']},headers=headers)
        self.assertEqual(reread.status_code,200)
        self.assertEqual(client.get('/api/notes?source=pdf').get_json()['total'],1)
        self.assertEqual(client.get('/api/usage').get_json()['totals']['api_calls'],0)
