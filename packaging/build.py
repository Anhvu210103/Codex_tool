"""Run on the target OS; macOS bundles cannot be built on Linux."""
import platform
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
name = 'SoGhiChep'
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--name', name,
        '--exclude-module', 'playwright',
        '--onefile', '--windowed', '--collect-data', 'certifi', '--paths', str(root), '--collect-all', 'pypdf', '--collect-all', 'waitress',
        '--collect-submodules', 'google.auth', '--collect-submodules', 'google.oauth2',
        '--add-data', str(root/'config.json') + ':.' ,
        '--add-data', str(root/'examples') + ':examples',
        '--add-data', str(root/'chrome-extension') + ':chrome-extension',
        '--add-data', str(root/'mailnotes/templates') + ':mailnotes/templates',
        '--add-data', str(root/'mailnotes/static') + ':mailnotes/static']
if sys.platform == 'darwin':
    args += ['--osx-bundle-identifier', 'vn.mailnotes.desktop']
args += [str(root/'packaging/app_entry.py')]
subprocess.run(args, cwd=root, check=True)
print('Built for', platform.system(), platform.machine(), 'in dist/')
