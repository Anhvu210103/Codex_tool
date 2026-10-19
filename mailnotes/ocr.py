"""Google Document AI OCR client for image-only PDFs.

DeepSeek remains the classification and summary model. Document AI is used
only when a PDF has no extractable text layer.
"""
import base64
import json
import urllib.error
import urllib.request


class DocumentAIOCRError(RuntimeError):
    pass


class DocumentAIOCR:
    def __init__(self, processor, credentials):
        if not isinstance(processor, str) or not processor.startswith('projects/'):
            raise ValueError('Google Document AI processor không hợp lệ.')
        if not isinstance(credentials, dict) or not credentials.get('client_email') or not credentials.get('private_key'):
            raise ValueError('Google service account JSON không hợp lệ.')
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
        except ImportError as error:
            raise DocumentAIOCRError('Thiếu thư viện google-auth; cài lại dependencies của tool.') from error
        self.processor = processor.rstrip('/')
        self.credentials = service_account.Credentials.from_service_account_info(
            credentials, scopes=['https://www.googleapis.com/auth/cloud-platform'])
        self._request_class = Request

    def extract(self, data):
        try:
            self.credentials.refresh(self._request_class())
        except Exception as error:
            raise DocumentAIOCRError('Google Document AI không xác thực được. Kiểm tra service account và quyền truy cập.') from error
        location = self.processor.split('/locations/', 1)[1].split('/', 1)[0] if '/locations/' in self.processor else 'us'
        host = f'https://{location}-documentai.googleapis.com' if location != 'us' else 'https://us-documentai.googleapis.com'
        url = host + '/v1/' + self.processor + ':process'
        payload = json.dumps({'rawDocument': {
            'content': base64.b64encode(data).decode('ascii'), 'mimeType': 'application/pdf'}}).encode()
        request = urllib.request.Request(url, data=payload, headers={
            'Authorization': 'Bearer ' + self.credentials.token,
            'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as error:
            raise DocumentAIOCRError('Google Document AI không đọc được PDF. Kiểm tra processor, quyền và hạn mức.') from error
        text = ((result.get('document') or {}).get('text') or '').strip()
        if len(text) < 20:
            raise DocumentAIOCRError('OCR cloud không trả về đủ chữ; tài liệu được giữ ở Cần xem lại.')
        return text[:100000]
