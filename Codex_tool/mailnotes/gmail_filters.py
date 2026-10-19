"""Human-friendly filters, evaluated at the start of each poll in the user's timezone."""
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def validate_filter(value):
    if not isinstance(value, dict):
        raise ValueError('Lựa chọn thư Gmail không hợp lệ.')
    period = value.get('period', 'today')
    if period not in ('today', 'week', 'range', 'all', 'advanced'):
        raise ValueError('Chọn thời gian đọc thư hợp lệ.')
    start, end = value.get('start_date', ''), value.get('end_date', '')
    if period == 'range':
        try:
            if not isinstance(start, str) or not isinstance(end, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', start) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', end) or date.fromisoformat(start) > date.fromisoformat(end):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('Chọn ngày bắt đầu và kết thúc; ngày kết thúc phải từ ngày bắt đầu trở đi.') from None
    else:
        start = end = ''
    senders = value.get('senders', [])
    if not isinstance(senders, list) or len(senders) > 30 or any(not isinstance(sender, str) or len(sender) > 254 or not re.fullmatch(r'[^@\s"():{}<>]+@[^@\s"():{}<>]+\.[^@\s"():{}<>]+', sender) for sender in senders):
        raise ValueError('Nhập địa chỉ email người gửi đầy đủ, cách nhau bằng dấu phẩy.')
    label = value.get('label', '')
    if not isinstance(label, str) or len(label) > 200 or re.search(r'["\\\r\n]', label):
        raise ValueError('Tên nhãn không hợp lệ.')
    for field in ('pdf_only', 'include_spam_trash'):
        if not isinstance(value.get(field, False), bool):
            raise ValueError('Lựa chọn đọc thư không hợp lệ.')
    return {'period': period, 'start_date': start, 'end_date': end, 'senders': senders,
            'label': label.strip(), 'pdf_only': value.get('pdf_only', False),
            'include_spam_trash': value.get('include_spam_trash', False)}


def date_bounds(config, now=None):
    settings = config.get('gmail_filter')
    if not settings or settings['period'] in ('advanced', 'all'):
        return None
    zone = ZoneInfo(config.get('timezone', 'Asia/Ho_Chi_Minh'))
    today = (now or datetime.now(zone)).astimezone(zone).date()
    if settings['period'] == 'range':
        first, last = date.fromisoformat(settings['start_date']), date.fromisoformat(settings['end_date'])
    else:
        last = today
        first = today - timedelta(days=6) if settings['period'] == 'week' else today
    return (int(datetime.combine(first, time.min, zone).timestamp()),
            int(datetime.combine(last + timedelta(days=1), time.min, zone).timestamp()))


def build_query(config, now=None):
    settings = config.get('gmail_filter')
    if not settings or settings['period'] == 'advanced':
        return config.get('gmail_query', '')
    parts = []
    bounds = date_bounds(config, now)
    if bounds:
        # Request midnight inclusively; exact millisecond boundaries are checked below.
        parts.extend([f'after:{bounds[0]-1}', f'before:{bounds[1]}'])
    if settings['senders']:
        parts.append('{' + ' '.join('from:"' + sender + '"' for sender in settings['senders']) + '}')
    if settings['label']:
        parts.append('label:"' + settings['label'] + '"')
    if settings['pdf_only']:
        parts.append('has:attachment filename:pdf')
    if settings['include_spam_trash']:
        parts.append('in:anywhere')
    return ' '.join(parts)
