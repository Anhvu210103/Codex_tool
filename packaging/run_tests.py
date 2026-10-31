"""Run unit tests and expose the failing tail in GitHub's build summary."""
import os
import subprocess
import sys


def main():
    result = subprocess.run(
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors='replace',
    )
    print(result.stdout, end='')
    if result.returncode and os.environ.get('GITHUB_ACTIONS') == 'true':
        tail = ' | '.join(line.strip() for line in result.stdout.splitlines()[-35:] if line.strip())
        tail = tail.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Unit tests failed::{tail[:12000]}')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
