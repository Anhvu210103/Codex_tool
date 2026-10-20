import importlib.util
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


@unittest.skipUnless(importlib.util.find_spec('resource'), 'Requires POSIX file limits')
class DatabaseResourceTests(unittest.TestCase):
    def test_repeated_dashboard_reads_do_not_exhaust_file_descriptors(self):
        script = textwrap.dedent('''
            import gc, resource, tempfile
            from pathlib import Path
            from mailnotes.admin import Admin
            from mailnotes.core import process
            limits = resource.getrlimit(resource.RLIMIT_NOFILE)
            with tempfile.TemporaryDirectory() as directory:
                admin = Admin(Path.cwd(), Path(directory))
                process([{'id':'fd-test','subject':'Test','sender':'example',
                          'body':'báo cáo','received_at':'2026-10-16T08:00:00+07:00'}],
                        admin.runtime_config('demo'),'demo')
                gc.collect()
                resource.setrlimit(resource.RLIMIT_NOFILE, (min(128, limits[0]), limits[1]))
                gc.disable()
                try:
                    for _ in range(400):
                        assert admin.dashboard('demo')['total_notes'] == 1
                finally:
                    resource.setrlimit(resource.RLIMIT_NOFILE, limits)
                    gc.enable()
                    gc.collect()
        ''')
        result = subprocess.run([sys.executable, '-c', script],
                                cwd=Path(__file__).resolve().parent.parent,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
