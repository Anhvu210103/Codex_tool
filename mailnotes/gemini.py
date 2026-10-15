"""Gemini REST transport: PDF bytes go to Google's API, with no local OCR."""
import base64
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

HOST = 'generativelanguage.googleapis.com'
BASE = 'https://' + HOST
DEFAULT_MODEL = 'gemini-flash-latest'
INLINE_LIMIT = 8 * 1024 * 1024


def call(path, key, *, data=None, raw=None, headers=None, method=None):
    url = path if path.startswith('https://') else BASE + path
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != HOST or parsed.port not in (None, 443) or parsed.username or parsed.password:
        raise ValueError('Địa chỉ tải lên Gemini không hợp lệ.')
    body = json.dumps(data).encode() if data is not None else raw
    request = urllib.request.Request(url, data=body, method=method,
                                     headers={'x-goog-api-key': key, **({'Content-Type':'application/json'} if data is not None else {}), **(headers or {})})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    with urllib.request.build_opener(NoRedirect()).open(request, timeout=120) as response:
        content = response.read()
        return (json.loads(content) if content else {}), response.headers


def file_name(value):
    if not isinstance(value, str) or not re.fullmatch(r'files/[A-Za-z0-9_-]+', value):
        raise ValueError('Gemini không trả định danh file hợp lệ.')
    return value


def generate(message, config, system, payload, key):
    settings = config['summary']
    model = settings.get('model') or DEFAULT_MODEL
    if not re.fullmatch(r'gemini-[A-Za-z0-9._-]+', model):
        raise ValueError('Tên model Gemini không hợp lệ. Dùng tên model từ Google AI Studio.')
    parts = [{'text': json.dumps(payload, ensure_ascii=False)}]
    uploaded = None
    response = None
    warning = ''
    try:
        if message.get('file_hash'):
            digest = message['file_hash']
            if not re.fullmatch(r'[a-f0-9]{64}', digest):
                raise ValueError('Định danh PDF không hợp lệ.')
            data = (Path(config['data_dir']) / 'files' / (digest + '.pdf')).read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError('File PDF đã thay đổi trên đĩa. Hãy tải lại bản gốc.')
            if len(data) <= INLINE_LIMIT:
                parts.append({'inlineData': {'mimeType':'application/pdf', 'data':base64.b64encode(data).decode()}})
            else:
                _, headers = call('/upload/v1beta/files', key, data={'file': {'display_name': message['subject'][:100]}},
                                  headers={'X-Goog-Upload-Protocol':'resumable', 'X-Goog-Upload-Command':'start',
                                           'X-Goog-Upload-Header-Content-Length':str(len(data)), 'X-Goog-Upload-Header-Content-Type':'application/pdf'})
                upload_url = headers.get('X-Goog-Upload-URL')
                if not upload_url:
                    raise ValueError('Gemini chưa cấp địa chỉ tải file. Hãy thử lại.')
                result, _ = call(upload_url, key, raw=data, headers={'Content-Type':'application/pdf', 'X-Goog-Upload-Offset':'0', 'X-Goog-Upload-Command':'upload, finalize'})
                file = result.get('file', result)
                uploaded = file_name(file.get('name'))
                deadline = time.monotonic() + 90
                while file.get('state', 'PROCESSING') != 'ACTIVE':
                    if file.get('state') == 'FAILED' or time.monotonic() >= deadline:
                        raise ValueError('Gemini chưa đọc được PDF hoặc xử lý quá lâu. Kiểm tra file và thử lại.')
                    time.sleep(1)
                    file, _ = call('/v1beta/' + uploaded, key)
                uri = file.get('uri')
                if not isinstance(uri, str) or not uri.startswith(BASE + '/'):
                    raise ValueError('Gemini không trả file PDF hợp lệ.')
                parts.append({'fileData': {'mimeType':'application/pdf', 'fileUri':uri}})
        response, _ = call('/v1beta/models/' + model + ':generateContent', key, data={
            'systemInstruction': {'parts': [{'text': system + ' Nếu có PDF đính kèm, đọc trực tiếp PDF (cả scan), không chỉ dựa vào tên file. Nếu không đọc được nội dung, needs_review=true và giải thích rõ; không bịa nội dung.'}]},
            'contents': [{'role':'user','parts':parts}],
            'generationConfig': {'responseMimeType':'application/json', 'maxOutputTokens':4096,
                                 'responseSchema': {'type':'OBJECT', 'properties': {
                                     'categories': {'type':'ARRAY','items':{'type':'STRING'}},
                                     'summary': {'type':'STRING'}, 'confidence': {'type':'NUMBER'},
                                     'needs_review': {'type':'BOOLEAN'}, 'review_reason': {'type':'STRING'}},
                                     'required':['categories','summary','confidence','needs_review','review_reason']}}})
    finally:
        if uploaded:
            try:
                call('/v1beta/' + uploaded, key, method='DELETE')
            except Exception:
                warning = 'Chưa xác nhận xóa được file tạm trên Gemini. Kiểm tra Files trong tài khoản Google; không ảnh hưởng bản gốc trên máy.'
    usage = response.get('usageMetadata', {})
    def count(field):
        value = usage.get(field)
        return value if type(value) is int and value >= 0 else None
    output = count('candidatesTokenCount')
    thoughts = count('thoughtsTokenCount') or 0
    normalized = {'usage': {'prompt_tokens':count('promptTokenCount'),
                            'prompt_cache_hit_tokens':count('cachedContentTokenCount') or 0,
                            'completion_tokens':output + thoughts if output is not None else None,
                            'total_tokens':count('totalTokenCount')},
                  'choices': [], '_cloud_warning':warning}
    candidates = response.get('candidates', [])
    if candidates:
        candidate = candidates[0]
        text = ''.join(part.get('text', '') for part in candidate.get('content', {}).get('parts', []) if not part.get('thought'))
        normalized['choices'] = [{'finish_reason':'stop' if candidate.get('finishReason') == 'STOP' else 'incomplete', 'message':{'content':text}}]
    return normalized


def models(key):
    names = []
    page = None
    for _ in range(10):
        query = '?pageSize=100' + ('&pageToken=' + urllib.parse.quote(page, safe='') if page else '')
        data, _ = call('/v1beta/models' + query, key)
        for model in data.get('models', []):
            name = model.get('name', '').removeprefix('models/')
            if name.startswith('gemini-') and 'generateContent' in model.get('supportedGenerationMethods', []) and not any(kind in name.lower() for kind in ('image','tts','audio','live','computer-use','robotics')):
                names.append(name)
        page = data.get('nextPageToken')
        if not page:
            break
    return sorted(set(names))
