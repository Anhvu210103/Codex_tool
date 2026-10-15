import io
import json
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from mailnotes.gmail_browser_pilot import select_with_ai, click_control


class BrowserPilotTests(unittest.TestCase):
    def test_ai_selects_only_a_visible_control_and_records_token_usage(self):
        page = MagicMock()
        page.screenshot.return_value = b'png'
        candidates = [{'index':2,'label':'Office — document.pdf','role':'row'}]
        response = {'candidates':[{'content':{'parts':[{'text':json.dumps({'index':2})}]}}],
                    'usageMetadata':{'promptTokenCount':100,'cachedContentTokenCount':0,
                                     'candidatesTokenCount':5,'thoughtsTokenCount':2,'totalTokenCount':107}}
        with sqlite3.connect(':memory:') as db, patch('mailnotes.gmail_browser_pilot.call',return_value=(response,{})):
            choice = select_with_ai(page,candidates,'mail','test-key','gemini-flash-latest',db,{})
            self.assertEqual(choice,candidates[0])
            self.assertEqual(db.execute('SELECT input_tokens,output_tokens,total_tokens FROM ai_usage').fetchone(),(100,7,107))

    def test_invalid_ai_choice_stops_before_click(self):
        page = MagicMock()
        page.screenshot.return_value = b'png'
        response = {'candidates':[{'content':{'parts':[{'text':'{"index":5}'}]}}]}
        with sqlite3.connect(':memory:') as db, patch('mailnotes.gmail_browser_pilot.call',return_value=(response,{})):
            with self.assertRaisesRegex(RuntimeError,'ngoài danh sách'):
                select_with_ai(page,[{'index':0,'label':'PDF','role':'button'}],'pdf','test-key','gemini-flash-latest',db,{})
        page.locator.assert_not_called()

    def test_destructive_control_is_blocked(self):
        page = MagicMock()
        with self.assertRaisesRegex(RuntimeError,'đã chặn'):
            click_control(page,{'index':0,'label':'Delete','role':'button'})
        page.locator.assert_not_called()
