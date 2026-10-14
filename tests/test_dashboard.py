import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from mailnotes.admin import Admin
from mailnotes.core import ensure_schema
from mailnotes.usage import record_usage
from mailnotes.web import create_app


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.root=Path(self.temporary.name)
        self.admin=Admin(Path(__file__).resolve().parent.parent,self.root)
        self.now=datetime(2026,10,14,1,tzinfo=timezone.utc)

    def tearDown(self):self.temporary.cleanup()

    def test_counts_include_all_notes_review_updates_and_recent_bounded(self):
        directory=self.root/'pdf';directory.mkdir()
        with sqlite3.connect(directory/'notes.sqlite3') as connection:
            ensure_schema(connection)
            for index in range(510):
                categories=['Work','Cần xem lại'] if index%100==0 else ['Work']
                received='2026-10-13T08:00:00+07:00' if index==0 else '2026-10-14T08:00:00+07:00'
                connection.execute('INSERT INTO notes (id,sender,subject,categories,summary,received_at,day,source,content_hash) VALUES (?,?,?,?,?,?,?,?,?)',('pdf:'+str(index),'Upload','Document '+str(index),json.dumps(categories),'Summary',received,received[:10],'pdf','hash'))
        result=self.admin.dashboard('pdf',self.now)
        self.assertEqual(result['total_notes'],510)
        self.assertEqual(result['received_today'],509)
        self.assertEqual(result['needs_review'],6)
        self.assertEqual(len(result['recent']),8)
        self.assertEqual(result['groups'][0],{'name':'Work','count':510})
        config=self.admin.config();config['rules']=[{'category':'Work','description':'Work','keywords':[],'senders':[]}];self.admin.save_settings(config)
        self.admin.edit_categories('pdf','pdf:100',['Work'])
        self.assertEqual(self.admin.dashboard('pdf',self.now)['needs_review'],5)

    def test_usage_today_obeys_local_midnight_and_preserves_unknown(self):
        directory=self.root/'gmail';directory.mkdir()
        rates={'input_per_million':2,'cached_input_per_million':.2,'output_per_million':8}
        response={'usage':{'prompt_tokens':1000,'prompt_cache_hit_tokens':200,'completion_tokens':100,'total_tokens':1100}}
        with sqlite3.connect(directory/'notes.sqlite3') as connection:
            ensure_schema(connection)
            for index,stamp in enumerate(['2026-10-13T16:59:59+00:00','2026-10-13T17:00:00+00:00','2026-10-14T17:00:00+00:00']):
                record_usage(connection,response if index<2 else {},'deepseek','deepseek-chat',str(index),rates)
                connection.execute('UPDATE ai_usage SET created_at=? WHERE id=?',(stamp,index+1));connection.commit()
        result=self.admin.dashboard('gmail',self.now)
        self.assertEqual(result['usage']['today']['api_calls'],1)
        self.assertEqual(result['usage']['today']['total_tokens'],1100)
        self.assertAlmostEqual(result['usage']['today']['estimated_usd'],.00244)
        self.assertEqual(result['usage']['totals']['unpriced_calls'],1)
        self.assertAlmostEqual(result['usage']['totals']['estimated_usd'],.00488)

    def test_dashboard_requires_login_and_empty_source_is_not_an_error(self):
        app=create_app(data_root=self.root);client=app.test_client()
        self.assertEqual(client.get('/api/dashboard').status_code,401)
        csrf=client.get('/api/session').get_json()['csrf']
        result=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf})
        self.assertEqual(result.status_code,200)
        empty=client.get('/api/dashboard?source=gmail')
        self.assertEqual(empty.status_code,200);self.assertEqual(empty.get_json()['total_notes'],0)
        self.assertEqual(empty.get_json()['recent'],[])
        self.assertEqual(client.get('/api/dashboard?source=../../').status_code,400)
