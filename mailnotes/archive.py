"""Local Markdown originals and classified copies; original PDFs stay in files/."""
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import unicodedata


def component(value):
    text = unicodedata.normalize('NFC', str(value))
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '-', text).strip(' .')
    text = text.encode('utf-8')[:160].decode('utf-8', errors='ignore').rstrip(' .')
    return (text or 'Tai-lieu') + '--' + hashlib.sha256(str(value).encode()).hexdigest()[:10]


def write_private(root, relative, text):
    root = Path(root).resolve()
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError('Thư mục xuất tài liệu nằm ngoài vùng dữ liệu.')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(text)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def markdown_path(root, file_hash):
    if not re.fullmatch(r'[a-f0-9]{64}', file_hash or ''):
        raise ValueError('Định danh PDF không hợp lệ.')
    return Path(root) / 'Markdown' / (file_hash + '.md')


def save_markdown(root, file_hash, text):
    path = markdown_path(root, file_hash)
    return write_private(root, path.relative_to(root), text.strip() + ('\n' if text.strip() else ''))


def render_archive(connection, root):
    root = Path(root).resolve()
    rows = connection.execute('SELECT id,subject,sender,categories,summary,received_at,review_reason,file_hash FROM notes WHERE file_hash IS NOT NULL AND file_hash != ""').fetchall()
    for identifier, title, sender, raw_groups, summary, received, warning, digest in rows:
        original_md = markdown_path(root, digest)
        if not original_md.exists():
            # Old notes can be converted by explicitly reading their PDF again.
            continue
        text = original_md.read_text(encoding='utf-8')
        key = hashlib.sha256(identifier.encode()).hexdigest()
        marker = '<!-- mailnotes-export:' + key + ' -->\n'
        filename = component(title) + '--' + key[:16] + '.md'
        manifest = root / 'exports' / (key + '.json')
        previous = json.loads(manifest.read_text()) if manifest.exists() else []
        exported = []
        for category in dict.fromkeys(json.loads(raw_groups)):
            relative = (Path('Can-xem-lai') / filename if category == 'Cần xem lại' else
                        Path('Theo-nhom') / component(category) / filename)
            pdf_link = os.path.relpath(root / 'files' / (digest + '.pdf'), (root / relative).parent)
            md_link = os.path.relpath(original_md, (root / relative).parent)
            body = (marker + '# ' + str(title).replace('\n', ' ') + '\n\n'
                    + '**Nhóm:** ' + category + '\n\n'
                    + '**Nguồn:** ' + str(sender).replace('\n', ' ') + '\n\n'
                    + '**Thời gian ghi nhận:** ' + received + '\n\n'
                    + '[PDF gốc](<' + pdf_link + '>) · [Markdown gốc](<' + md_link + '>)\n\n'
                    + '## Tóm tắt\n\n' + summary + '\n\n'
                    + ('**Cần kiểm tra:** ' + warning + '\n\n' if warning else '')
                    + '## Nội dung trích từ PDF\n\n' + (text or 'Chưa đọc được chữ từ PDF.\n'))
            write_private(root, relative, body)
            exported.append(relative.as_posix())
        # Remove only this tool's marked copies after a manual category change.
        for old in previous:
            candidate = root / old
            if (old not in exported and candidate.resolve().is_relative_to(root)
                    and Path(old).parts[0] in ('Theo-nhom', 'Can-xem-lai') and candidate.is_file()
                    and candidate.read_text(encoding='utf-8').startswith(marker)):
                candidate.unlink()
        write_private(root, Path('exports') / (key + '.json'), json.dumps(exported, ensure_ascii=False))
