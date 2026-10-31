from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import unittest

from mailnotes.core import ensure_schema
from mailnotes.database import connect


class SchemaConcurrencyTests(unittest.TestCase):
    def test_scan_and_notebook_can_initialize_and_migrate_together(self):
        with tempfile.TemporaryDirectory() as directory:
            for legacy in (False, True):
                database = Path(directory) / f'notes-{legacy}.sqlite3'
                if legacy:
                    with connect(database) as connection:
                        connection.execute('CREATE TABLE notes (id TEXT PRIMARY KEY)')
                        connection.execute('INSERT INTO notes VALUES (?)', ('saved-document',))
                ready = threading.Barrier(4)

                def initialize():
                    with connect(database) as connection:
                        ready.wait(timeout=5)
                        ensure_schema(connection)
                        return {row[1] for row in connection.execute('PRAGMA table_info(notes)')}

                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(lambda _: initialize(), range(4)))
                for columns in results:
                    self.assertTrue({'origin_id', 'review_reason', 'file_hash'} <= columns)
                if legacy:
                    with connect(database) as connection:
                        self.assertEqual(connection.execute('SELECT id FROM notes').fetchall(), [('saved-document',)])
