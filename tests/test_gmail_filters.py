import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from mailnotes.admin import validate_settings
from mailnotes.gmail_filters import build_query, date_bounds, validate_filter
from mailnotes.gmail import messages


class GmailFilterTests(unittest.TestCase):
    def config(self, period='today', zone='Asia/Ho_Chi_Minh', **extra):
        return {'timezone':zone, 'gmail_query':'label:legacy', 'gmail_filter':validate_filter({'period':period,**extra})}

    def test_today_local_midnight_and_rollover(self):
        config=self.config()
        now=datetime(2026,10,14,16,59,tzinfo=timezone.utc)
        start,end=date_bounds(config,now)
        self.assertEqual(datetime.fromtimestamp(start,timezone.utc).isoformat(),'2026-10-13T17:00:00+00:00')
        self.assertEqual(datetime.fromtimestamp(end,timezone.utc).isoformat(),'2026-10-14T17:00:00+00:00')
        self.assertIn(f'after:{start-1} before:{end}',build_query(config,now))
        tomorrow=datetime(2026,10,14,17,0,tzinfo=timezone.utc)
        self.assertEqual(date_bounds(config,tomorrow)[0],end)

    def test_week_range_inclusive_and_dst(self):
        now=datetime(2026,10,14,1,tzinfo=timezone.utc)
        start,end=date_bounds(self.config('week'),now)
        self.assertEqual(end-start,7*86400)
        config=self.config('range',start_date='2026-10-01',end_date='2026-10-03')
        self.assertEqual(date_bounds(config,now)[1]-date_bounds(config,now)[0],3*86400)
        config=self.config('range',zone='America/New_York',start_date='2026-03-08',end_date='2026-03-08')
        self.assertEqual(date_bounds(config,now)[1]-date_bounds(config,now)[0],23*3600)

    def test_senders_label_pdf_all_and_legacy(self):
        config=self.config('all',senders=['office@example.com','other@example.org'],label='Công việc/Thông báo',pdf_only=True,include_spam_trash=True)
        query=build_query(config)
        self.assertIn('{from:"office@example.com" from:"other@example.org"}',query)
        self.assertIn('label:"Công việc/Thông báo"',query)
        self.assertIn('has:attachment filename:pdf',query)
        self.assertIn('in:anywhere',query)
        self.assertEqual(build_query(self.config('all')),'')
        self.assertEqual(build_query(self.config('advanced')),'label:legacy')
        self.assertEqual(build_query({'gmail_query':'label:old'}),'label:old')

    def test_invalid_range_and_query_injection_rejected(self):
        for value in [{'period':'range','start_date':'2026-10-15','end_date':'2026-10-14'}, {'period':'range','start_date':'2026-02-30','end_date':'2026-03-01'}, {'period':'all','senders':['office@example.com OR in:anywhere']}, {'period':'all','label':'foo" in:anywhere'}, {'period':'unknown'}]:
            with self.subTest(value=value),self.assertRaises(ValueError):validate_filter(value)

    def test_old_settings_preserved_and_pdf_selection_enables_reading(self):
        settings=json.loads((Path(__file__).resolve().parent.parent/'config.json').read_text())
        settings.pop('gmail_filter');settings['gmail_query']='label:customer'
        normalized=validate_settings(settings)
        self.assertEqual(normalized['gmail_filter']['period'],'advanced')
        self.assertEqual(build_query(normalized),'label:customer')
        settings['gmail_filter']={'period':'today','pdf_only':True};settings['gmail_pdf']=False
        self.assertTrue(validate_settings(settings)['gmail_pdf'])

    def test_exact_day_excludes_neighboring_milliseconds(self):
        now=datetime(2026,10,14,1,tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            config={**self.config(),'data_dir':directory,'gmail_pdf':False}
            start,end=date_bounds(config,now)
            timestamps={'before':start*1000-1,'midnight':start*1000,'last':end*1000-1,'after':end*1000}
            def response(url,**kwargs):
                if '?format=full' in url:
                    identifier=url.split('/')[-1].split('?')[0]
                    return {'id':identifier,'internalDate':str(timestamps[identifier]),'payload':{'headers':[]}}
                return {'messages':[{'id':identifier} for identifier in timestamps]}
            with patch('mailnotes.gmail.access_token',return_value='test-token'),patch('mailnotes.gmail.request_json',side_effect=response),patch('mailnotes.gmail.datetime') as clock:
                clock.now.return_value=now;clock.fromtimestamp.side_effect=datetime.fromtimestamp
                result=list(messages(config,'credentials','token'))
            self.assertEqual([message['id'] for message in result],['midnight','last'])
