#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "${MAILNOTES_PILOT_TERMINAL:-}" != 1 ] && command -v x-terminal-emulator >/dev/null 2>&1; then
    MAILNOTES_PILOT_TERMINAL=1 x-terminal-emulator -e "$HERE/Mo-AI-Gmail.sh"
    exit
fi
if [ "${MAILNOTES_PILOT_TERMINAL:-}" = 1 ]; then
    trap 'status=$?; trap - EXIT; echo "Bản thử đã kết thúc (mã $status). Nhấn Enter để đóng."; read -r _; exit "$status"' EXIT
fi
cd "$HERE"
if [ ! -x .venv/bin/python ]; then
    echo 'Chưa có .venv trong thư mục này. Cài bản web trước.'
    exit 1
fi
if ! .venv/bin/python -c 'import playwright' >/dev/null 2>&1; then
    echo 'Đang cài Playwright một lần cho bản thử AI trên Gmail...'
    .venv/bin/python -m pip install -r requirements-browser.txt
fi
echo 'DeepSeek sẽ chọn thư và nút PDF từ chữ trên trang Gmail. Đăng nhập bằng cửa sổ Chrome khi được hỏi.'
.venv/bin/python -m mailnotes.gmail_browser_pilot
