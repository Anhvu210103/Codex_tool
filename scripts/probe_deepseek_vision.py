"""Probe whether DeepSeek chat accepts a base64 image and can read its text.

Usage: DEEPSEEK_API_KEY=... python scripts/probe_deepseek_vision.py [image.png]
The default image contains a short test code. No customer document is sent.
"""
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def test_image():
    from PIL import Image, ImageDraw, ImageFont

    image = Image.new('RGB', (900, 260), 'white')
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype('DejaVuSans.ttf', 78)
    except OSError:
        font = ImageFont.load_default()
    draw.text((35, 70), 'OCR TEST 4826', fill='black', font=font)
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue(), 'image/png'


def main():
    key = os.environ.get('DEEPSEEK_API_KEY')
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
        image, mime = test_image()
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
