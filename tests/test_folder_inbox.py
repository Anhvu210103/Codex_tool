import os
import tempfile
import time
import unittest
import io
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfWriter

from mailnotes.admin import Admin
from mailnotes.folder_inbox import archive_processed, inbox_directory, ready_pdfs, iter_ready_pdfs
from mailnotes.web import create_app


class FolderInboxTests(unittest.TestCase):
    @staticmethod
    def pdf(title=''):
        writer=PdfWriter();writer.add_blank_page(width=600,height=800)
        if title:writer.add_metadata({'/Title':title})
        output=io.BytesIO();writer.write(output);return output.getvalue()

    def test_only_complete_real_pdf_is_read_and_then_archived(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);valid=root/'Văn bản.pdf';valid.write_bytes(b'%PDF-test')
            old=time.time()-10;os.utime(valid,(old,old))
            fresh=root/'fresh.pdf';fresh.write_bytes(b'%PDF-new')
            fake=root/'fake.pdf';fake.write_bytes(b'not-pdf');os.utime(fake,(old,old))
            outside=root.parent/'outside-folder-inbox.pdf';outside.write_bytes(b'%PDF-outside')
            link=root/'link.pdf'
            try:link.symlink_to(outside)
            except OSError:link=None
            ready,errors=ready_pdfs(root,now=time.time())
            self.assertEqual([(item[0].name,item[1]) for item in ready],[('Văn bản.pdf',b'%PDF-test')])
            self.assertEqual(errors,[{'file':'fake.pdf','error':'Tệp có đuôi PDF nhưng nội dung không phải PDF hợp lệ.'}])
            moved=archive_processed(ready[0][0],ready[0][2],root)
            self.assertTrue(moved.is_file());self.assertFalse(valid.exists())
            self.assertEqual(ready_pdfs(root,now=time.time())[0],[])
            outside.unlink()

    def test_managed_install_can_override_inbox_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'MAILNOTES_INBOX_DIR':directory}):
            self.assertEqual(inbox_directory(), Path(directory).resolve())

    def test_folder_reads_one_pdf_at_a_time_and_reports_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ('a.pdf','b.pdf'):
                (root/name).write_bytes(b'%PDF-test')
            with (root/'large.pdf').open('wb') as stream:
                stream.truncate(21*1024*1024)
            errors=[]
            with patch('mailnotes.folder_inbox.os.open', wraps=os.open) as opened:
                candidates=iter_ready_pdfs(root,minimum_age=0,errors=errors)
                self.assertFalse(opened.called)
                self.assertEqual(next(candidates)[0].name,'a.pdf')
                self.assertEqual(opened.call_count,1)
                self.assertEqual(next(candidates)[0].name,'b.pdf')
                self.assertEqual(list(candidates),[])
            self.assertEqual([item['file'] for item in errors],['large.pdf'])

    def test_long_original_filename_can_be_archived_without_repeating_forever(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/('đ'*120+'.pdf');path.write_bytes(b'%PDF-test')
            import hashlib
            moved=archive_processed(path,hashlib.sha256(b'%PDF-test').hexdigest(),root)
            self.assertTrue(moved.is_file())
            self.assertLessEqual(len(moved.name.encode('utf-8')),255)
            self.assertFalse(path.exists())

    def test_failed_file_stays_in_inbox_while_later_files_are_processed_and_retry_recovers(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);admin=Admin(Path.cwd(),root/'data');inbox=root/'inbox';inbox.mkdir()
            for name in ('a.pdf','b.pdf','c.pdf'):
                path=inbox/name;path.write_bytes(self.pdf(name));os.utime(path,(time.time()-10,time.time()-10))
            original=admin._process_pdf_locked
            def process(data,name,*args):
                if name=='b.pdf':raise ValueError('Simulated temporary provider failure')
                return original(data,name,*args)
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox),patch.object(admin,'_process_pdf_locked',side_effect=process):
                self.assertTrue(admin.start_folder_import())
                with admin.run_lock:pass
            self.assertEqual(admin.notes('folder')['total'],2)
            self.assertEqual([path.name for path in inbox.glob('*.pdf')],['b.pdf'])
            self.assertEqual(admin.status()['folder_inbox']['errors'][0]['file'],'b.pdf')
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                self.assertTrue(admin.start_folder_import())
                with admin.run_lock:pass
            self.assertEqual(admin.notes('folder')['total'],3)
            self.assertEqual(list(inbox.glob('*.pdf')),[])
            self.assertIsNone(admin.status()['folder_inbox']['error'])

    def test_admin_imports_folder_pdf_moves_it_and_skips_cross_source_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);admin=Admin(Path.cwd(),root/'data');inbox=root/'inbox';inbox.mkdir()
            raw=self.pdf();first=inbox/'first.pdf';first.write_bytes(raw);old=time.time()-10;os.utime(first,(old,old))
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                self.assertTrue(admin.start_folder_import())
                for _ in range(100):
                    if not admin.status()['folder_inbox']['running']:break
                    time.sleep(.02)
            self.assertEqual(admin.notes('folder')['total'],1)
            self.assertFalse(first.exists());self.assertEqual(len(list((inbox/'Da-xu-ly').glob('*.pdf'))),1)
            duplicate=inbox/'same-again.pdf';duplicate.write_bytes(raw);os.utime(duplicate,(old,old))
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                self.assertTrue(admin.start_folder_import())
                for _ in range(100):
                    if not admin.status()['folder_inbox']['running']:break
                    time.sleep(.02)
            self.assertEqual(admin.notes('folder')['total'],1)
            self.assertFalse(duplicate.exists());self.assertEqual(admin.status()['folder_inbox']['last_added'],0)
            from_upload=self.pdf('already uploaded');self.assertEqual(admin.process_pdf(from_upload,'uploaded.pdf'),1)
            cross_source=inbox/'downloaded-again.pdf';cross_source.write_bytes(from_upload);os.utime(cross_source,(old,old))
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                self.assertTrue(admin.start_folder_import())
                for _ in range(100):
                    if not admin.status()['folder_inbox']['running']:break
                    time.sleep(.02)
            self.assertEqual(admin.notes('folder')['total'],1)
            self.assertFalse(cross_source.exists());self.assertEqual(admin.status()['folder_inbox']['last_added'],0)

    def test_shutdown_finishes_current_pdf_and_leaves_remaining_files_for_next_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);admin=Admin(Path.cwd(),root/'data');inbox=root/'inbox';inbox.mkdir()
            for name in ('a.pdf','b.pdf','c.pdf'):
                path=inbox/name;path.write_bytes(self.pdf(name));os.utime(path,(time.time()-10,time.time()-10))
            original=admin._process_pdf_locked
            def process(*args):
                added=original(*args);admin.stop.set();return added
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox),patch.object(admin,'_process_pdf_locked',side_effect=process):
                self.assertTrue(admin.start_folder_import())
                with admin.run_lock:pass
            self.assertEqual(admin.notes('folder')['total'],1)
            self.assertEqual(sorted(path.name for path in inbox.glob('*.pdf')),['b.pdf','c.pdf'])
            self.assertIn('tạm dừng',admin.status()['folder_inbox']['error'])

    def test_web_exposes_inbox_and_runs_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);inbox=root/'inbox';inbox.mkdir();pdf=inbox/'manual.pdf';pdf.write_bytes(self.pdf());old=time.time()-10;os.utime(pdf,(old,old))
            app=create_app(data_root=root/'data');client=app.test_client();csrf=client.get('/api/session').get_json()['csrf'];csrf=client.post('/api/setup',json={'password':'test-private-password'},headers={'X-CSRF-Token':csrf}).get_json()['csrf']
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                info=client.get('/api/folder-inbox');self.assertEqual(info.status_code,200);self.assertEqual(info.get_json()['path'],str(inbox))
                started=client.post('/api/folder-inbox',json={'action':'run'},headers={'X-CSRF-Token':csrf});self.assertEqual(started.status_code,202)
                for _ in range(100):
                    if not app.extensions['admin'].status()['folder_inbox']['running']:break
                    time.sleep(.02)
            self.assertEqual(client.get('/api/notes?source=folder').get_json()['total'],1)

    def test_enabled_folder_schedule_runs_without_clicking_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);admin=Admin(Path.cwd(),root/'data');inbox=root/'inbox';inbox.mkdir()
            pdf=inbox/'scheduled.pdf';pdf.write_bytes(self.pdf());old=time.time()-10;os.utime(pdf,(old,old))
            settings=admin.config();settings['folder_inbox_enabled']=True;admin.save_settings(settings)
            with patch('mailnotes.folder_inbox.inbox_directory',return_value=inbox):
                admin.start_scheduler()
                for _ in range(150):
                    if admin.notes('folder')['total'] == 1:break
                    time.sleep(.02)
                for _ in range(150):
                    if not admin.status()['folder_inbox']['running']:break
                    time.sleep(.02)
                admin.stop.set();admin.scheduler.join(timeout=2)
            self.assertEqual(admin.notes('folder')['total'],1)
            self.assertFalse(pdf.exists())


if __name__ == '__main__':unittest.main()
