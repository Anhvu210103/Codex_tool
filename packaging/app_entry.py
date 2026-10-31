import os
import sys

from mailnotes.desktop import data_directory, main


def initialize_streams():
    # Windows GUI executables have no console streams, even when their parent
    # redirects handles. Keep startup errors and library diagnostics on disk.
    if sys.stdout is None or sys.stderr is None:
        path = data_directory() / 'admin' / 'desktop.log'
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        log = os.fdopen(descriptor, 'w', encoding='utf-8', buffering=1)
        if sys.stdout is None:
            sys.stdout = log
        if sys.stderr is None:
            sys.stderr = log

if __name__ == '__main__':
    initialize_streams()
    main()
