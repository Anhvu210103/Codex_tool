#!/bin/sh
# Source launcher: reuses the Python environment and data already installed here.
cd -- "$(dirname -- "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
    if command -v zenity >/dev/null 2>&1; then
        zenity --error --title='Sổ ghi chép' --text='Bản mã nguồn chưa được cài thư viện. Hãy dùng bản app đóng gói, hoặc xem hướng dẫn cài lần đầu trong README.'
    elif [ "$(uname -s)" = Darwin ]; then
        open README.md >/dev/null 2>&1 || true
    else
        xdg-open README.md >/dev/null 2>&1 || true
    fi
    exit 1
fi
exec .venv/bin/python -m mailnotes.desktop
