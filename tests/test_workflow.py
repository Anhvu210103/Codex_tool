import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mailnotes.core import classify, process
from mailnotes.gmail import body_text


class WorkflowTests(unittest.TestCase):
    def test_daily_notebook_and_idempotency(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {'data_dir': directory, 'timezone': 'Asia/Ho_Chi_Minh', 'rules': [{'category': 'Báo cáo', 'keywords': ['báo cáo'], 'senders': ['office@']}], 'unmatched_category': 'Khác'}
            mail = {'id': 'abc123', 'sender': 'office@example.com', 'subject': 'BÁO CÁO', 'body': 'Nộp trước ngày 20/10.\nTrân trọng,\nChữ ký', 'received_at': '2026-10-12T18:00:00+00:00'}
            self.assertEqual(process([mail], config, 'gmail'), 1)
            with patch('mailnotes.core.summarize', side_effect=AssertionError('must not resummarize')):
                self.assertEqual(process([mail], config, 'gmail'), 0)
            note = (Path(directory) / 'notebooks/2026-10-13.md').read_text()
            self.assertIn('Báo cáo', note)
            self.assertIn('Nộp trước ngày 20/10.', note)
            self.assertNotIn('Chữ ký', note)
            self.assertIn('#all/abc123', note)
            self.assertNotIn('#all/gmail:', note)

    def test_sender_and_keywords_both_required(self):
        config = {'rules': [{'category': 'Work', 'keywords': ['report'], 'senders': ['office@']}]}
        self.assertEqual(classify({'sender': 'other@example.com', 'subject': 'report', 'body': ''}, config), [])

    def test_mime_plain_preferred_and_attachments_ignored(self):
        def part(mime, text, filename=''):
            return {'mimeType': mime, 'filename': filename, 'body': {'data': base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')}}
        payload = {'mimeType': 'multipart/mixed', 'parts': [part('text/html', '<p>HTML</p>'), part('text/plain', 'Plain'), part('text/plain', 'Attachment', 'file.txt')]}
        self.assertEqual(body_text(payload), 'Plain')
        self.assertEqual(body_text(part('text/html', '<script>bad()</script><p>Xin chào &amp; bạn</p>')).strip(), 'Xin chào & bạn')

    def test_failed_summary_is_retriable(self):
        with tempfile.TemporaryDirectory() as directory:
            config = {'data_dir': directory, 'rules': [], 'unmatched_category': 'Khác'}
            mail = {'id': '1', 'sender': 'a', 'subject': 'b', 'body': 'c', 'received_at': '2026-10-13T00:00:00+00:00'}
            with patch('mailnotes.core.summarize', side_effect=RuntimeError('failed')):
                with self.assertRaises(RuntimeError):
                    process([mail], config, 'demo')
            self.assertEqual(process([mail], config, 'demo'), 1)


if __name__ == '__main__':
    unittest.main()
