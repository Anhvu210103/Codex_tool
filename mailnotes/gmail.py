import base64
import json
import os
import secrets
import hashlib
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from .database import connect
import webbrowser

from .core import html_to_text, request_json

SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'


def form_request(url, fields):
    request = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode())
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def save_token(path, token):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        json.dump(token, stream)
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def client_config(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    client = data.get('installed') or data.get('web')
    if not isinstance(client, dict) or not client.get('client_id') or not client.get('client_secret'):
        raise ValueError('Invalid OAuth application credentials file')
    return client


def authorize(credentials, token_path):
    client = client_config(credentials)
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    import hashlib
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    result = {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
            valid = self.path.startswith('/callback?') and query.get('state') == [state]
            if valid:
                result.update(query)
            self.send_response(200 if valid else 400)
            self.end_headers()
            self.wfile.write(b'You may close this window.' if valid else b'Invalid OAuth callback.')

        def log_message(self, *args):
            pass

    with HTTPServer(('127.0.0.1', 0), Callback) as server:
        redirect = f'http://127.0.0.1:{server.server_port}/callback'
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
            'client_id': client['client_id'], 'redirect_uri': redirect, 'response_type': 'code',
            'scope': SCOPE, 'access_type': 'offline', 'prompt': 'consent', 'state': state,
            'code_challenge': challenge, 'code_challenge_method': 'S256'})
        print('Open this authorization URL in a browser on the SAME machine:\n' + url)
        webbrowser.open(url)
        server.timeout = 1
        deadline = time.monotonic() + 300
        while not result and time.monotonic() < deadline:
            server.handle_request()
    if 'code' not in result:
        raise RuntimeError('OAuth not completed or denied; no token saved')
    token = form_request('https://oauth2.googleapis.com/token', {
        'client_id': client['client_id'], 'client_secret': client['client_secret'],
        'code': result['code'][0], 'code_verifier': verifier,
        'redirect_uri': redirect, 'grant_type': 'authorization_code'})
    token['expires_at'] = time.time() + token.get('expires_in', 3600)
    save_token(token_path, token)
    print('Read-only Gmail authorization saved locally.')


def access_token(credentials, token_path):
    token = json.loads(Path(token_path).read_text(encoding='utf-8'))
    if token.get('expires_at', 0) <= time.time() + 60:
        client = client_config(credentials)
        fresh = form_request('https://oauth2.googleapis.com/token', {
            'client_id': client['client_id'], 'client_secret': client['client_secret'],
            'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'})
        token.update(fresh)
        token['expires_at'] = time.time() + fresh.get('expires_in', 3600)
        save_token(token_path, token)
    return token['access_token']


def decode(data):
    return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)).decode('utf-8', errors='replace')


def body_text(payload):
    plain, rich = [], []

    def visit(part):
        if part.get('filename'):
            return
        mime = part.get('mimeType', '')
        data = part.get('body', {}).get('data')
        if data and mime == 'text/plain':
            plain.append(decode(data))
        elif data and mime == 'text/html':
            rich.append(html_to_text(decode(data)))
        for child in part.get('parts', []):
            visit(child)
    visit(payload)
    return '\n'.join(plain or rich)


def messages(config, credentials, token_path):
    token = access_token(credentials, token_path)
    headers = {'Authorization': 'Bearer ' + token}
    base = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
    from .documents import pdf_message, MAX_PDF_BYTES
    known = set()
    database = Path(config['data_dir']) / 'notes.sqlite3'
    if database.exists():
        with connect(database) as connection:
            known = {row[0] for row in connection.execute('SELECT id FROM notes')}
    from .gmail_filters import build_query, date_bounds
    filter_time = datetime.now(timezone.utc)
    query_text = build_query(config, filter_time)
    bounds = date_bounds(config, filter_time)
    page = None
    while True:
        query = {'q': query_text, 'maxResults': 100}
        if page:
            query['pageToken'] = page
        listing = request_json(base + '?' + urllib.parse.urlencode(query), headers=headers)
        for item in listing.get('messages', []):
            detail = request_json(base + '/' + item['id'] + '?format=full', headers=headers)
            received = int(detail['internalDate']) / 1000
            if bounds and not bounds[0] <= received < bounds[1]:
                continue
            payload = detail['payload']
            fields = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
            metadata = {'sender': fields.get('from', ''),
                        'received_at': datetime.fromtimestamp(int(detail['internalDate']) / 1000, timezone.utc).isoformat(),
                        'origin_id': detail['id']}
            attachments = []
            def collect(part):
                filename = part.get('filename', '')
                if config.get('gmail_pdf', True) and (filename.lower().endswith('.pdf') or part.get('mimeType') == 'application/pdf'):
                    attachments.append(part)
                for child in part.get('parts', []):
                    collect(child)
            collect(payload)
            if not attachments:
                yield {**metadata, 'id': detail['id'], 'subject': fields.get('subject', '(không có tiêu đề)'), 'body': body_text(payload)}
            for index, part in enumerate(attachments):
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')
                identifier = detail['id'] + ':pdf:' + hashlib.sha256((attachment_id or str(index)).encode()).hexdigest()[:24]
                if 'gmail:' + identifier in known:
                    continue
                if body.get('size', 0) > MAX_PDF_BYTES:
                    yield {**metadata, 'id': identifier, 'subject': part.get('filename') or 'PDF', 'body': '',
                           'file_hash': '', 'review_reason': 'PDF vượt 20 MB; cần xử lý riêng.'}
                    continue
                data = body.get('data')
                if attachment_id:
                    downloaded = request_json(base + '/' + detail['id'] + '/attachments/' + urllib.parse.quote(attachment_id, safe=''), headers=headers)
                    data = downloaded['data']
                raw = base64.urlsafe_b64decode((data or '') + '=' * (-len(data or '') % 4))
                if len(raw) > MAX_PDF_BYTES or not raw.startswith(b'%PDF-'):
                    yield {**metadata, 'id': identifier, 'subject': part.get('filename') or 'PDF', 'body': '',
                           'review_reason': 'File đính kèm không phải PDF hợp lệ hoặc vượt 20 MB.'}
                    continue
                yield pdf_message(raw, part.get('filename') or 'PDF', config, id=identifier, **metadata)
        page = listing.get('nextPageToken')
        if not page:
            break
