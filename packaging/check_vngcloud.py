"""Check the configured VNG Cloud model without printing credentials or content."""
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mailnotes.admin import Admin
from mailnotes.core import request_json
from mailnotes.providers import provider


def main():
    base = Path(__file__).resolve().parents[1]
    admin = Admin(base)
    config = admin.runtime_config('ai')
    settings = config['summary']
    gateway = provider(settings['provider'])
    key = config.get('_api_key') or os.environ.get(gateway['environment'])
    if not key:
        print('Chưa có API key trên máy này. Lưu key trong Cài đặt rồi chạy lại.')
        return 2
    print('Nhà cung cấp:', gateway['label'])
    print('Model yêu cầu:', settings['model'])
    try:
        response = request_json(gateway['endpoint'], data={
            'model': settings['model'], 'temperature': 0, 'max_tokens': 200,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'user', 'content': 'Trả duy nhất JSON {"ok":true,"purpose":"phan-loai-tai-lieu"}.'}],
        }, headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
        choice = response['choices'][0]
        content = json.loads(choice['message']['content'])
        usage = response.get('usage') or {}
        print('HTTP chat/JSON: thành công' if content.get('ok') is True else 'HTTP chat/JSON: phản hồi chưa đúng')
        print('Model phản hồi:', response.get('model', 'không báo'))
        print('Token: đầu vào', usage.get('prompt_tokens', 'không báo'),
              '· đầu ra', usage.get('completion_tokens', 'không báo'))
        return 0 if content.get('ok') is True else 1
    except HTTPError as error:
        print('API trả HTTP', error.code, '— kiểm tra model, quyền key và hạn mức trên GreenNode.')
    except (URLError, TimeoutError) as error:
        print('Không kết nối được VNG Cloud:', getattr(error, 'reason', type(error).__name__))
    except (KeyError, IndexError, TypeError, ValueError):
        print('API có phản hồi nhưng không trả JSON theo định dạng tool cần.')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
