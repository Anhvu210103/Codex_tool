"""SQLite transactions with deterministic connection cleanup."""
from contextlib import contextmanager
import sqlite3


@contextmanager
def connect(*args, **kwargs):
    connection = sqlite3.connect(*args, **kwargs)
    try:
        with connection:
            yield connection
    finally:
        connection.close()
