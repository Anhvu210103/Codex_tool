"""Verify the real HTTP request shape and usage parsing against a fake server response."""
import io
import json
import sqlite3
import unittest
from unittest.mock import patch

from mailnotes.ai import analyze


class VngCloudContractTests(unittest.TestCase):
    def test_classification_request_and_token_accounting(self):
        sent = {}
        response = {
            'model': 'deepseek-v4.1-flash-thirdparty',
            'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({
                'categories': ['Công văn'], 'summary': 'Nộp báo cáo ngày mai.',
                'confidence': .95, 'needs_review': False, 'review_reason': '',
            })}}],
            'usage': {'prompt_tokens': 90, 'completion_tokens': 20, 'total_tokens': 110,
                      'prompt_tokens_details': {'cached_tokens': 0}},
        }

        class Reply(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.close()

        def fake_urlopen(request, timeout):
            sent['url'] = request.full_url
            sent['auth'] = request.get_header('Authorization')
            sent['body'] = json.loads(request.data)
            return Reply(json.dumps(response).encode())

        config = {'_api_key': 'test-local-key', 'summary': {
            'provider': 'vngcloud', 'model': 'deepseek/deepseek-v4.1-flash-thirdparty',
            'max_input_chars': 12000, 'pricing': {'input_per_million': None,
            'cached_input_per_million': None, 'output_per_million': None}},
            'rules': [{'category': 'Công văn', 'description': 'Việc phải làm'}]}
        message = {'id': 'doc-1', 'subject': 'Công văn', 'body': 'Nộp báo cáo ngày mai.'}
        connection = sqlite3.connect(':memory:')
        try:
            with patch('urllib.request.urlopen', side_effect=fake_urlopen):
                groups, summary, _ = analyze(message, config, connection)
            self.assertEqual(groups, ['Công văn'])
            self.assertEqual(summary, 'Nộp báo cáo ngày mai.')
            self.assertEqual(sent['url'], 'https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions')
            self.assertEqual(sent['auth'], 'Bearer test-local-key')
            self.assertEqual(sent['body']['model'], 'deepseek/deepseek-v4.1-flash-thirdparty')
            self.assertEqual(sent['body']['response_format'], {'type': 'json_object'})
            self.assertEqual(connection.execute('SELECT input_tokens,output_tokens,total_tokens FROM ai_usage').fetchone(), (90, 20, 110))
        finally:
            connection.close()
