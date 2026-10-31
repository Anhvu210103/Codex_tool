"""Create a simple customer ZIP from the tested Windows executable."""
import argparse
from pathlib import Path
import shutil
import zipfile


ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app', type=Path, default=ROOT / 'dist' / 'SoGhiChep.exe')
    parser.add_argument('--output', type=Path, default=ROOT / 'dist' / 'SoGhiChep-Windows-x86_64.zip')
    args = parser.parse_args()
    if not args.app.is_file():
        parser.error('Thiếu dist/SoGhiChep.exe.')
    guide = ('SỔ GHI CHÉP — WINDOWS\n\n'
             '1. Giải nén toàn bộ ZIP vào một thư mục cố định.\n'
             '2. Bấm đúp SoGhiChep.exe. Trình duyệt sẽ tự mở.\n'
             '3. Nếu Windows SmartScreen hỏi, chỉ tiếp tục khi file được nhận từ đơn vị triển khai tin cậy.\n'
             '4. Dữ liệu nằm tại %LOCALAPPDATA%\\SoGhiChep và không nằm trong file EXE.\n'
             '5. Để OCR PDF scan, cài Poppler và thêm pdftoppm.exe vào PATH.\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Actions zips the upload itself. Upload this folder so customers only need
    # to extract once, while retaining a standalone ZIP for other distribution.
    folder = args.output.with_suffix('')
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.app, folder / 'SoGhiChep.exe')
    (folder / 'HUONG-DAN.txt').write_text(guide, encoding='utf-8')
    args.output.unlink(missing_ok=True)
    with zipfile.ZipFile(args.output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.write(args.app, 'SoGhiChep/SoGhiChep.exe')
        archive.writestr('SoGhiChep/HUONG-DAN.txt', guide)
    with zipfile.ZipFile(args.output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP Windows bị lỗi.')
    print(f'Created {args.output}')


if __name__ == '__main__':
    main()
