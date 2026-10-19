"""Sign when configured, create a DMG, and optionally notarize it."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run(*args):
    subprocess.run([str(item) for item in args], check=True)


def main():
    if sys.platform != 'darwin':
        raise SystemExit('DMG chỉ được tạo trên macOS.')
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=ROOT / 'dist' / 'SoGhiChep.app')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'SoGhiChep.dmg')
    args = parser.parse_args()
    if not args.app.is_dir():
        parser.error('Thiếu dist/SoGhiChep.app.')

    identity = os.environ.get('MACOS_SIGNING_IDENTITY')
    if identity:
        run('codesign', '--force', '--deep', '--options', 'runtime', '--timestamp', '--sign', identity, args.app)
        run('codesign', '--verify', '--deep', '--strict', '--verbose=2', args.app)
    else:
        # Ad-hoc signing records bundle integrity for internal test builds.
        run('codesign', '--force', '--deep', '--sign', '-', args.app)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='so-ghi-chep-dmg-') as temporary:
        staging = Path(temporary) / 'Sổ ghi chép'
        staging.mkdir()
        shutil.copytree(args.app, staging / args.app.name, symlinks=True)
        (staging / 'Applications').symlink_to('/Applications')
        run('hdiutil', 'create', '-volname', 'Sổ ghi chép', '-srcfolder', staging,
            '-ov', '-format', 'UDZO', args.output)
    run('hdiutil', 'verify', args.output)

    notarization = [os.environ.get(name) for name in ('APPLE_ID', 'APPLE_TEAM_ID', 'APPLE_APP_PASSWORD')]
    if any(notarization) and not all(notarization):
        raise SystemExit('Cần đặt đủ APPLE_ID, APPLE_TEAM_ID và APPLE_APP_PASSWORD để notarize.')
    if all(notarization):
        if not identity:
            raise SystemExit('Notarization yêu cầu MACOS_SIGNING_IDENTITY và chứng thư Developer ID.')
        apple_id, team_id, password = notarization
        run('xcrun', 'notarytool', 'submit', args.output, '--apple-id', apple_id,
            '--team-id', team_id, '--password', password, '--wait')
        run('xcrun', 'stapler', 'staple', args.output)
        run('xcrun', 'stapler', 'validate', args.output)
    print(f'Created {args.output}')


if __name__ == '__main__':
    main()
