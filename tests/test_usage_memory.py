from datetime import datetime, timezone
from pathlib import Path
import tempfile
import tracemalloc
import unittest

from mailnotes.admin import Admin
from mailnotes.database import connect
from mailnotes.usage import ensure_usage


class UsageMemoryTests(unittest.TestCase):
    def test_large_usage_history_does_not_load_all_price_payloads_into_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(Path(__file__).resolve().parents[1],Path(directory))
            root=Path(directory)/'gmail';root.mkdir()
            stamp='2026-11-01T00:00:00+00:00'
            with connect(root/'notes.sqlite3') as connection:
                ensure_usage(connection)
                connection.executemany('INSERT INTO ai_usage (created_at,provider,model,note_id,cache_hit,input_tokens,cached_tokens,output_tokens,total_tokens,estimated_usd,prices) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    ((stamp,'vngcloud','fixture','private-note-'+str(index),0,10,0,2,12,.001,'x'*2048) for index in range(12000)))
            tracemalloc.start()
            try:
                usage=admin.usage(datetime(2026,11,1,1,tzinfo=timezone.utc))
                _,peak=tracemalloc.get_traced_memory()
            finally:tracemalloc.stop()
            self.assertEqual(usage['totals']['api_calls'],12000)
            self.assertEqual(usage['today']['total_tokens'],144000)
            self.assertEqual(len(usage['recent']),50)
            self.assertLess(peak,10*1024*1024,f'Usage dashboard allocated {peak/1024/1024:.1f} MB for a bounded response')
            self.assertFalse(any('prices' in item or 'note_id' in item for item in usage['recent']))

    def test_recent_history_is_globally_bounded_and_ties_keep_source_order(self):
        with tempfile.TemporaryDirectory() as directory:
            admin=Admin(Path(__file__).resolve().parents[1],Path(directory))
            for source in ('gmail','pdf'):
                root=Path(directory)/source;root.mkdir()
                with connect(root/'notes.sqlite3') as connection:
                    ensure_usage(connection)
                    connection.executemany('INSERT INTO ai_usage (created_at,provider,model,note_id,cache_hit,input_tokens,cached_tokens,output_tokens,total_tokens,estimated_usd,prices) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                        (('2026-11-01T00:00:00+00:00','vngcloud','fixture',str(index),0,index,0,1,index+1,0,'{}') for index in range(40)))
            usage=admin.usage()
            self.assertEqual(usage['totals']['api_calls'],80)
            self.assertEqual(len(usage['recent']),50)
            self.assertEqual([item['source'] for item in usage['recent'][:4]],['gmail','pdf','gmail','pdf'])
            self.assertEqual([item['input_tokens'] for item in usage['recent'][:4]],[39,39,38,38])
