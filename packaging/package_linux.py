"""Create an AppImage from the Linux PyInstaller executable."""
import argparse
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=ROOT / 'dist' / 'SoGhiChep')
    parser.add_argument('--appimagetool', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'SoGhiChep-x86_64.AppImage')
    args = parser.parse_args()
    if not args.app.is_file() or not args.appimagetool.is_file() or not args.runtime.is_file():
        parser.error('Thiếu executable SoGhiChep, appimagetool hoặc AppImage runtime.')

    appdir = ROOT / 'build' / 'SoGhiChep.AppDir'
    shutil.rmtree(appdir, ignore_errors=True)
    binary = appdir / 'usr' / 'bin' / 'SoGhiChep'
    binary.parent.mkdir(parents=True)
    shutil.copy2(args.app, binary)
    binary.chmod(0o755)
    shutil.copy2(ROOT / 'packaging' / 'SoGhiChep.svg', appdir / 'SoGhiChep.svg')
    (appdir / 'SoGhiChep.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Sổ ghi chép\n'
        'Comment=Đọc tài liệu, phân nhóm và ghi chép tự động\n'
        'Exec=SoGhiChep\nIcon=SoGhiChep.svg\nTerminal=false\nCategories=Office;\n',
        encoding='utf-8')
    shutil.copy2(ROOT / 'packaging' / 'SoGhiChep.svg', appdir / '.DirIcon')
    apprun = appdir / 'AppRun'
    apprun.write_text('#!/bin/sh\nHERE="$(dirname "$(readlink -f "$0")")"\nexec "$HERE/usr/bin/SoGhiChep" "$@"\n', encoding='utf-8')
    apprun.chmod(0o755)
    # AppImage contents must remain readable when the build runner uses a
    # restrictive umask (the hosted runner currently creates directories 0700).
    for path in [appdir, *appdir.rglob('*')]:
        mode = path.stat().st_mode
        path.chmod(mode | 0o055 if path.is_dir() else mode | 0o044)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.unlink(missing_ok=True)
    environment = {**os.environ, 'ARCH':'x86_64', 'APPIMAGE_EXTRACT_AND_RUN':'1'}
    subprocess.run([str(args.appimagetool), '--no-appstream', '--runtime-file', str(args.runtime),
                    str(appdir), str(args.output)], check=True, env=environment)
    args.output.chmod(0o755)
    print(f'Created {args.output}')


if __name__ == '__main__':
    main()
