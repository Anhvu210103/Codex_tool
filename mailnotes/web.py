import argparse
import base64
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import threading
import time
import urllib.parse
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_file, session

from .admin import Admin, error_message, password_record, private_json, read_json, verify_password
from .gmail import SCOPE, form_request, save_token


def create_app(base=None, data_root=None, public_url=None):
    base = Path(base or Path(__file__).resolve().parent.parent)
    admin = Admin(base, data_root)
    app = Flask(__name__)
    app.extensions['admin'] = admin
    secret_path = admin.private / 'session.json'
    if not secret_path.exists():
        private_json(secret_path, {'key': secrets.token_hex(32)})
    public_url = (public_url or os.environ.get('MAILNOTES_PUBLIC_URL', 'http://localhost:8080')).rstrip('/')
    parsed = urllib.parse.urlsplit(public_url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise ValueError('Public URL must be a plain HTTP(S) origin')
    if parsed.scheme != 'https' and parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
        raise ValueError('Use HTTPS for remote deployment')
    app.config.update(SECRET_KEY=read_json(secret_path, {})['key'], MAX_CONTENT_LENGTH=22 * 1024 * 1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                      SESSION_COOKIE_SECURE=parsed.scheme == 'https', PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
                      TRUSTED_HOSTS=[parsed.hostname, 'localhost', '127.0.0.1'])
    password_path = admin.private / 'password.json'
    bootstrap = os.environ.get('MAILNOTES_ADMIN_PASSWORD')
    if bootstrap and not password_path.exists():
        private_json(password_path, password_record(bootstrap))
    attempts = {}
    attempts_lock = threading.Lock()
    operations = threading.Lock()

    def csrf():
        if 'csrf' not in session:
            session['csrf'] = secrets.token_urlsafe(32)
        return session['csrf']

    @app.before_request
    def security():
        if request.path.startswith('/static/'):
            return
        csrf()
        if session.get('authenticated'):
            record = read_json(password_path, {})
            if not hmac.compare_digest(session.get('auth_epoch', ''), record.get('epoch', 'invalid')):
                session.clear()
                csrf()
        if request.path.startswith('/api/') and request.method != 'GET':
            supplied = request.headers.get('X-CSRF-Token', '')
            if not hmac.compare_digest(supplied.encode(), session['csrf'].encode()):
                return jsonify(error='Phiên đã hết hạn. Tải lại trang rồi thử lại.'), 403
            origin = request.headers.get('Origin')
            if origin and origin != public_url:
                return jsonify(error='Nguồn yêu cầu không hợp lệ.'), 403
        public = {'/', '/api/session', '/api/login', '/api/setup'}
        if request.path not in public and not session.get('authenticated'):
            if request.path.startswith('/api/'):
                return jsonify(error='Vui lòng đăng nhập.'), 401
            return redirect('/')

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Cache-Control'] = 'no-store'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        if parsed.scheme == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Dữ liệu quá lớn. File PDF tối đa 20 MB.'), 413

    @app.errorhandler(500)
    def internal(error):
        return jsonify(error='Lỗi hệ thống. Kiểm tra cấu hình máy chủ rồi thử lại.'), 500

    def payload():
        if request.content_length and request.content_length > 128 * 1024:
            raise ValueError('Cấu hình vượt giới hạn 128 KB.')
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError('Yêu cầu JSON không hợp lệ.')
        return data

    @app.get('/')
    def home():
        return render_template('admin.html')

    @app.get('/api/session')
    def session_info():
        return jsonify(authenticated=bool(session.get('authenticated')), needs_setup=not password_path.exists(), csrf=csrf())

    @app.post('/api/setup')
    def setup():
        # Bootstrap only from loopback before exposing the server to the network.
        if request.remote_addr not in ('127.0.0.1', '::1') or parsed.hostname not in ('localhost', '127.0.0.1', '::1'):
            return jsonify(error='Quản trị viên cần thiết lập mật khẩu trên máy chủ trước.'), 403
        with operations:
            if password_path.exists():
                return jsonify(error='Đã thiết lập. Vui lòng đăng nhập.'), 409
            private_json(password_path, password_record(payload().get('password')))
        session.clear()
        session.update(authenticated=True, permanent=True, auth_epoch=read_json(password_path, {})['epoch'])
        return jsonify(csrf=csrf())

    @app.post('/api/login')
    def login():
        address = request.remote_addr
        with attempts_lock:
            now = time.monotonic()
            for key in list(attempts):
                attempts[key] = [stamp for stamp in attempts[key] if now - stamp < 300]
                if not attempts[key]:
                    del attempts[key]
            recent = attempts.setdefault(address, [])
            if len(recent) >= 5:
                return jsonify(error='Đã thử quá nhiều lần. Vui lòng chờ 5 phút.'), 429
            recent.append(now)
        record = read_json(password_path, None)
        if not record or not verify_password(payload().get('password'), record):
            return jsonify(error='Mật khẩu không đúng.'), 401
        with attempts_lock:
            attempts.pop(address, None)
        session.clear()
        session.update(authenticated=True, permanent=True, auth_epoch=record['epoch'])
        return jsonify(csrf=csrf())

    @app.post('/api/logout')
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.post('/api/password')
    def change_password():
        data = payload()
        with operations:
            if not verify_password(data.get('current'), read_json(password_path, {})):
                return jsonify(error='Mật khẩu hiện tại không đúng.'), 403
            private_json(password_path, password_record(data.get('password')))
        session.clear()
        return jsonify(ok=True)

    @app.route('/api/settings', methods=['GET', 'POST'])
    def settings():
        if request.method == 'GET':
            return jsonify(admin.config())
        return jsonify(admin.save_settings(payload()))

    @app.get('/api/status')
    def status():
        status = admin.status()
        requested = request.args.get('provider')
        if requested in ('deepseek', 'openai'):
            status['ai_key_configured'] = admin.has_key(requested)
        return jsonify(status)

    @app.post('/api/run')
    def run():
        source = payload().get('source')
        if source not in (None, 'demo', 'gmail'):
            raise ValueError('Nguồn không hợp lệ.')
        if not admin.start_run(source):
            return jsonify(error='Đang có lượt xử lý. Vui lòng chờ.'), 409
        return jsonify(ok=True), 202

    @app.get('/api/notes')
    def notes():
        return jsonify(admin.notes(request.args.get('source', 'demo'), request.args.get('day', ''), request.args.get('q', ''), request.args.get('category', '')))

    @app.get('/api/export')
    def export():
        source, day = request.args.get('source', 'demo'), request.args.get('day', '')
        if source not in ('demo', 'gmail', 'pdf') or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            raise ValueError('Chọn nguồn và ngày hợp lệ để tải sổ.')
        path = admin.root / source / 'notebooks' / (day + '.md')
        if not path.exists():
            return jsonify(error='Ngày này chưa có ghi chép.'), 404
        # Read a snapshot, so an atomic notebook replacement cannot affect transfer.
        return send_file(io.BytesIO(path.read_bytes()), mimetype='text/markdown; charset=utf-8',
                         as_attachment=True, download_name=f'so-ghi-chep-{day}.md')

    @app.post('/api/pdf')
    def upload_pdf():
        from .documents import MAX_PDF_BYTES
        file = request.files.get('file')
        if not file or not file.filename:
            raise ValueError('Chọn file PDF.')
        data = file.stream.read(MAX_PDF_BYTES + 1)
        try:
            added = admin.process_pdf(data, Path(file.filename).name, request.form.get('reprocess') == 'true')
        except ValueError:
            raise
        except Exception as error:
            return jsonify(error=error_message(error)), 400
        return jsonify(added=added)

    @app.post('/api/notes/categories')
    def edit_categories():
        data = payload()
        admin.edit_categories(data.get('source'), data.get('id'), data.get('categories'))
        return jsonify(ok=True)

    @app.get('/api/document')
    def document():
        source = request.args.get('source')
        if source not in ('gmail', 'pdf'):
            raise ValueError('Nguồn không hợp lệ.')
        database = admin.root / source / 'notes.sqlite3'
        if not database.exists():
            return jsonify(error='Không tìm thấy PDF.'), 404
        import sqlite3
        with sqlite3.connect(database) as connection:
            row = connection.execute('SELECT file_hash FROM notes WHERE id=?', (request.args.get('id'),)).fetchone()
        if not row or not row[0] or not re.fullmatch(r'[a-f0-9]{64}', row[0]):
            return jsonify(error='Không tìm thấy PDF.'), 404
        path = database.parent / 'files' / (row[0] + '.pdf')
        if not path.exists():
            return jsonify(error='File PDF đã bị xóa trên máy chủ.'), 404
        return send_file(path, mimetype='application/pdf', as_attachment=True, download_name='tai-lieu.pdf')

    @app.post('/api/gmail/client')
    def gmail_client():
        data = payload().get('credentials')
        if not isinstance(data, dict) or not isinstance(data.get('web'), dict):
            raise ValueError('Chọn file OAuth client loại Web application tải từ Google Cloud.')
        client = data['web']
        if any(not isinstance(client.get(key), str) or not client[key] for key in ('client_id', 'client_secret')):
            raise ValueError('File OAuth thiếu client_id hoặc client_secret.')
        callback = public_url + '/oauth/callback'
        if callback not in client.get('redirect_uris', []):
            raise ValueError('Thêm Redirect URI sau vào Google Cloud rồi tải lại file: ' + callback)
        with admin.run_lock:
            private_json(admin.credentials, {'web': {key: client[key] for key in ('client_id', 'client_secret', 'redirect_uris')}})
            admin.token.unlink(missing_ok=True)
        return jsonify(ok=True)

    @app.get('/api/gmail/info')
    def gmail_info():
        return jsonify(callback=public_url + '/oauth/callback', scope=SCOPE)

    @app.post('/api/gmail/connect')
    def gmail_connect():
        client = read_json(admin.credentials, {}).get('web')
        if not client:
            raise ValueError('Tải file OAuth Web application lên trước.')
        verifier = secrets.token_urlsafe(64)
        state = secrets.token_urlsafe(32)
        session['oauth'] = {'state': state, 'verifier': verifier, 'started': time.time()}
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urllib.parse.urlencode({
            'client_id': client['client_id'], 'redirect_uri': public_url + '/oauth/callback',
            'response_type': 'code', 'scope': SCOPE, 'access_type': 'offline', 'prompt': 'consent',
            'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})
        return jsonify(url=url)

    @app.get('/oauth/callback')
    def oauth_callback():
        flow = session.pop('oauth', None)
        state = request.args.get('state', '')
        if not flow or time.time() - flow['started'] > 600 or not hmac.compare_digest(state.encode(), flow['state'].encode()):
            return render_template('oauth.html', message='Phiên kết nối không hợp lệ hoặc đã hết hạn. Hãy kết nối lại.'), 400
        if request.args.get('error') or not request.args.get('code'):
            return render_template('oauth.html', message='Bạn chưa cấp quyền Gmail. Có thể thử lại trong Cài đặt.'), 400
        try:
            with admin.run_lock:
                client = read_json(admin.credentials, {})['web']
                token = form_request('https://oauth2.googleapis.com/token', {
                    'client_id': client['client_id'], 'client_secret': client['client_secret'],
                    'code': request.args['code'], 'code_verifier': flow['verifier'],
                    'redirect_uri': public_url + '/oauth/callback', 'grant_type': 'authorization_code'})
                if not token.get('refresh_token'):
                    raise ValueError('No refresh token')
                scopes = token.get('scope', '').split()
                if SCOPE not in scopes:
                    raise ValueError('Required Gmail scope missing')
                token['expires_at'] = time.time() + token.get('expires_in', 3600)
                save_token(admin.token, token)
        except Exception:
            return render_template('oauth.html', message='Chưa kết nối được Gmail. Kiểm tra cấu hình OAuth và thử lại.'), 400
        return render_template('oauth.html', message='Đã lưu kết nối Gmail. Hãy chạy thử để kiểm tra quyền đọc email.')

    @app.post('/api/gmail/disconnect')
    def disconnect():
        with admin.run_lock:
            admin.token.unlink(missing_ok=True)
            config = admin.config()
            config['schedule_enabled'] = False
            admin.save_settings(config)
        session.pop('oauth', None)
        return jsonify(ok=True)

    @app.post('/api/ai-key')
    def ai_key():
        data = payload()
        provider = data.get('provider', admin.config()['summary']['provider'])
        if provider not in ('deepseek', 'openai'):
            raise ValueError('Nhà cung cấp AI không hợp lệ.')
        key = data.get('key')
        if not isinstance(key, str) or len(key) > 1000:
            raise ValueError('API key không hợp lệ.')
        if key.strip():
            private_json(admin.key_path(provider), {'key': key.strip()})
        else:
            admin.key_path(provider).unlink(missing_ok=True)
        return jsonify(ok=True)

    return app


def main():
    parser = argparse.ArgumentParser(description='Mailnotes administration')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--public-url', default=os.environ.get('MAILNOTES_PUBLIC_URL'))
    args = parser.parse_args()
    app = create_app(public_url=args.public_url or f'http://localhost:{args.port}')
    admin = app.extensions['admin']
    if args.host not in ('127.0.0.1', '::1', 'localhost') and not (admin.private / 'password.json').exists():
        parser.error('Set MAILNOTES_ADMIN_PASSWORD (12+ characters) before binding remotely.')
    admin.start_scheduler()
    try:
        # Waitress is the production server; a single process owns the scheduler.
        from waitress import serve
        serve(app, host=args.host, port=args.port, threads=8, clear_untrusted_proxy_headers=True)
    finally:
        admin.stop.set()


if __name__ == '__main__':
    main()
