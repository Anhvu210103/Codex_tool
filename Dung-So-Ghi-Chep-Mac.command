#!/bin/sh
# Double-click to stop the Mac Docker build without removing customer data.
cd "$(dirname "$0")" || exit 1
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH
if ! command -v docker >/dev/null 2>&1; then
  printf 'Khong tim thay Docker Desktop.\n'
  read -r _
  exit 1
fi
if docker compose down; then
  printf 'Da dung So ghi chep. Du lieu trong .local va inbox duoc giu nguyen.\n'
else
  printf 'Chua dung duoc. Kiem tra Docker Desktop.\n'
  read -r _
  exit 1
fi
