"""Build on the target OS; desktop executables are not cross-compiled."""
import platform
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
name = 'SoGhiChep'
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--name', name,
        '--exclude-module', 'playwright',
        '--onefile', '--windowed', '--collect-data', 'certifi', '--collect-data', 'tzdata', '--paths', str(root), '--collect-all', 'pypdf', '--collect-all', 'waitress',
        '--collect-submodules', 'google.auth', '--collect-submodules', 'google.oauth2',
        '--add-data', str(root/'config.json') + os.pathsep + '.' ,
        '--add-data', str(root/'examples') + os.pathsep + 'examples',
        '--add-data', str(root/'chrome-extension') + os.pathsep + 'chrome-extension',
        '--add-data', str(root/'mailnotes/templates') + os.pathsep + 'mailnotes/templates',
        '--add-data', str(root/'mailnotes/static') + os.pathsep + 'mailnotes/static']
if sys.platform == 'darwin':
    args += ['--osx-bundle-identifier', 'vn.mailnotes.desktop']
args += [str(root/'packaging/app_entry.py')]
subprocess.run(args, cwd=root, check=True)
print('Built for', platform.system(), platform.machine(), 'in dist/')
