"""Probe whether DeepSeek chat accepts a base64 image and can read its text.

Usage: python scripts/probe_deepseek_vision.py [image.png]
The default image contains a short test code. No customer document is sent.
"""
import base64
import getpass
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def main():
    key = os.environ.get('DEEPSEEK_API_KEY') or getpass.getpass('DeepSeek API key (không hiện trên màn hình): ')
    if not key:
        print('Thiếu DEEPSEEK_API_KEY trong môi trường.', file=sys.stderr)
        return 2
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg'):
            print('Chỉ dùng ảnh PNG/JPEG để thử; PDF cần render từng trang.', file=sys.stderr)
            return 2
        image, mime = path.read_bytes(), 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
    else:
        image, mime = (Path(__file__).with_name('ocr-test-4826.png').read_bytes(), 'image/png')
    payload = {
        'model': 'deepseek-chat',
        'max_tokens': 100,
        'messages': [{'role': 'user', 'content': [
            {'type': 'text', 'text': 'Đọc chính xác chữ trong ảnh. Chỉ trả về chữ nhìn thấy.'},
            {'type': 'image_url', 'image_url': {'url': f'data:{mime};base64,{base64.b64encode(image).decode()}'}}
        ]}],
    }
    request = urllib.request.Request(
        'https://api.deepseek.com/chat/completions',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        # Never print headers or the request, which contain the API key and image.
        body = error.read(1500).decode('utf-8', 'replace')
        print('HTTP', error.code, body)
        return 1
    except urllib.error.URLError as error:
        print('Lỗi kết nối:', error.reason)
        return 1
    print('Phản hồi:', (result.get('choices') or [{}])[0].get('message', {}).get('content'))
    print('Usage:', result.get('usage'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
