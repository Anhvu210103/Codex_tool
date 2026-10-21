"""Customer-facing counts, source selection, exports and scan failures."""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from pypdf import PdfWriter

from mailnotes.admin import Admin
from mailnotes.core import ensure_schema
from mailnotes.database import connect
from mailnotes.documents import pdf_text
from mailnotes.web import create_app


class CustomerFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.admin = Admin(Path(__file__).resolve().parent.parent, self.root)

    def tearDown(self):
        self.temp.cleanup()

    def insert(self, source, count, stamp, category='Kinh tế'):
        directory = self.root / source
        directory.mkdir(exist_ok=True)
        with connect(directory / 'notes.sqlite3') as connection:
            ensure_schema(connection)
            for index in range(count):
                connection.execute('INSERT INTO notes (id,sender,subject,categories,summary,received_at,day,source,content_hash) VALUES (?,?,?,?,?,?,?,?,?)',
                                   (source+':'+str(index), 'Văn phòng', source+' '+str(index), json.dumps([category]), 'Tóm tắt báo cáo', stamp, stamp[:10], source, str(index)))
            connection.commit()

    def test_all_sources_preserves_full_counts_filters_and_latest_rows(self):
        self.insert('pdf', 510, '2026-10-20T08:00:00+07:00')
        self.insert('folder', 4, '2026-10-21T08:00:00+07:00', 'Cần xem lại')
        self.insert('demo', 3, '2026-10-21T09:00:00+07:00')
        notes = self.admin.notes('all')
        self.assertEqual(notes['total'], 514)
        self.assertEqual(len(notes['notes']), 500)
        self.assertEqual(notes['notes'][0]['source'], 'folder')
        self.assertEqual(notes['days'], ['2026-10-21', '2026-10-20'])
        self.assertEqual(self.admin.notes('all', category='Cần xem lại')['total'], 4)
        self.assertEqual(self.admin.notes('all', search='folder')['total'], 4)
        dashboard = self.admin.dashboard('all')
        self.assertEqual(dashboard['total_notes'], 514)
        self.assertEqual(dashboard['needs_review'], 4)
        self.assertEqual(dashboard['recent'][0]['source'], 'folder')

    def test_all_sources_orders_by_actual_time_across_timezones(self):
        self.insert('folder', 1, '2026-10-21T08:00:00+07:00')
        self.insert('pdf', 1, '2026-10-21T04:00:00+00:00')
        self.assertEqual(self.admin.notes('all')['notes'][0]['source'], 'pdf')

    def test_authenticated_export_combines_all_sources_and_keeps_empty_error(self):
        for source in ('folder', 'pdf'):
            path = self.root / source / 'notebooks'
            path.mkdir(parents=True)
            (path/'2026-10-21.md').write_text('Nội dung '+source, encoding='utf-8')
        client = create_app(data_root=self.root).test_client()
        self.assertEqual(client.get('/api/export?source=all&day=2026-10-21').status_code, 401)
        csrf = client.get('/api/session').get_json()['csrf']
        client.post('/api/setup', json={'password':'customer-test-password'}, headers={'X-CSRF-Token':csrf})
        exported = client.get('/api/export?source=all&day=2026-10-21')
        self.assertEqual(exported.status_code, 200)
        self.assertIn('Nội dung folder', exported.get_data(as_text=True))
        self.assertIn('Nội dung pdf', exported.get_data(as_text=True))
        self.assertEqual(client.get('/api/export?source=all&day=2026-10-22').status_code, 404)

    def test_mac_path_display_does_not_change_download_storage(self):
        writer = PdfWriter(); writer.add_blank_page(width=600,height=800)
        output=io.BytesIO(); writer.write(output)
        self.admin.process_pdf(output.getvalue(), 'scan.pdf')
        self.assertEqual(self.admin.status()['last_source'], 'pdf')
        self.assertEqual(self.admin.status()['last_added'], 1)
        self.assertFalse(self.admin.status()['running'])
        with patch.dict(os.environ, {'MAILNOTES_DATA_DISPLAY_PATH':'/Users/Khach/Documents/SoGhiChep/.local'}):
            item = self.admin.notes('all')['notes'][0]['local_markdown_paths'][0]
        self.assertTrue(Path(item['path']).is_file())
        self.assertTrue(item['display_path'].startswith('/Users/Khach/Documents/SoGhiChep/.local/pdf/'))

    def test_rejected_or_truncated_ocr_never_looks_like_success(self):
        writer=PdfWriter(); writer.add_blank_page(width=600,height=800)
        output=io.BytesIO(); writer.write(output)
        def render(command, **kwargs):
            Path(command[-1]+'-1.png').write_bytes(b'image')
        for failure in [HTTPError('https://api.deepseek.com/chat/completions',400,'Bad request',{},None),
                        {'choices':[{'finish_reason':'length','message':{'content':'Nội dung bị cắt giữa chừng nên không thể coi là đọc hết tài liệu.'}}]}]:
            options={'side_effect':failure} if isinstance(failure,Exception) else {'return_value':failure}
            with patch('mailnotes.documents.subprocess.run',side_effect=render), patch('mailnotes.core.request_json',**options):
                text,warning=pdf_text(output.getvalue(),ocr=True,api_key='test-key')
            self.assertEqual(text,'')
            self.assertIn('OCR',warning)
