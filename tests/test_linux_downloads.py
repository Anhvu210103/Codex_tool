import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from mailnotes.linux_downloads import read_download, download_directory


class LinuxDownloadTests(unittest.TestCase):
    def test_only_selected_pdf_under_downloads_can_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);downloads=home/'Downloads';downloads.mkdir()
            target=downloads/'report.pdf';target.write_bytes(b'%PDF-test')
            outside=home/'private.pdf';outside.write_bytes(b'%PDF-private')
            (downloads/'link.pdf').symlink_to(outside)
            with patch('sys.platform','linux'),patch('mailnotes.linux_downloads.download_directory',return_value=downloads):
                self.assertEqual(read_download(str(target)),(b'%PDF-test','report.pdf'))
                self.assertIsNone(read_download(str(outside)))
                self.assertIsNone(read_download(str(downloads/'link.pdf')))
                self.assertIsNone(read_download('report.pdf'))
                self.assertIsNone(read_download(str(downloads/'missing.pdf')))
                target.write_bytes(b'<html>Not PDF</html>')
                self.assertIsNone(read_download(str(target)))

    def test_xdg_download_folder_is_parsed_without_running_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);(home/'.config').mkdir()
            (home/'.config/user-dirs.dirs').write_text('XDG_DOWNLOAD_DIR="$HOME/My downloads"\n')
            with patch('pathlib.Path.home',return_value=home),patch.dict('os.environ',{'XDG_CONFIG_HOME':str(home/'.config')}):
                self.assertEqual(download_directory(),(home/'My downloads').resolve())

    def test_windows_and_macos_use_the_desktop_download_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);downloads=home/'Downloads';downloads.mkdir()
            for platform in ('win32','darwin'):
                with self.subTest(platform=platform),patch('sys.platform',platform),patch('pathlib.Path.home',return_value=home),patch.dict('os.environ',{},clear=True):
                    self.assertEqual(download_directory(),downloads.resolve())
