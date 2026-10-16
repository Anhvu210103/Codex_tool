import io
import json
import sqlite3
import unittest
from unittest.mock import MagicMock, patch

from mailnotes.gmail_browser_pilot import select_with_ai, click_control, browser_binary


class BrowserPilotTests(unittest.TestCase):
    def test_linux_finds_chromium_outside_path(self):
        with patch('mailnotes.gmail_browser_pilot.shutil.which',return_value=None),patch('sys.platform','linux'),patch('os.path.isfile',side_effect=lambda path:path=='/snap/bin/chromium'),patch('os.access',return_value=True):
            self.assertEqual(browser_binary(),'/snap/bin/chromium')

    def test_ai_selects_only_a_visible_control_and_records_token_usage(self):
        page = MagicMock()
        candidates = [{'index':2,'label':'Office — document.pdf','role':'row'}]
        response = {'choices':[{'message':{'content':json.dumps({'index':2})}}],
                    'usage':{'prompt_tokens':100,'prompt_cache_hit_tokens':0,
                             'completion_tokens':7,'total_tokens':107}}
        with sqlite3.connect(':memory:') as db, patch('mailnotes.gmail_browser_pilot.request_json',return_value=response) as request:
            choice = select_with_ai(page,candidates,'mail','test-key','deepseek-chat',db,{})
            self.assertEqual(choice,candidates[0])
            self.assertEqual(request.call_args.args[0],'https://api.deepseek.com/chat/completions')
            page.screenshot.assert_not_called()
            self.assertEqual(db.execute('SELECT input_tokens,output_tokens,total_tokens FROM ai_usage').fetchone(),(100,7,107))

    def test_invalid_ai_choice_stops_before_click(self):
        page = MagicMock()
        response = {'choices':[{'message':{'content':'{"index":5}'}}]}
        with sqlite3.connect(':memory:') as db, patch('mailnotes.gmail_browser_pilot.request_json',return_value=response):
            with self.assertRaisesRegex(RuntimeError,'ngoài danh sách'):
                select_with_ai(page,[{'index':0,'label':'PDF','role':'button'}],'pdf','test-key','deepseek-chat',db,{})
        page.locator.assert_not_called()

    def test_destructive_control_is_blocked(self):
        page = MagicMock()
        with self.assertRaisesRegex(RuntimeError,'đã chặn'):
            click_control(page,{'index':0,'label':'Delete','role':'button'})
        page.locator.assert_not_called()
