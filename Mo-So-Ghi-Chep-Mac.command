#!/bin/sh
# Double-click launcher for the Docker Desktop build on macOS.
cd "$(dirname "$0")" || exit 1
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH
MAILNOTES_INBOX_HOST_PATH="$(pwd -P)/inbox"
MAILNOTES_DATA_HOST_PATH="$(pwd -P)/.local"
export MAILNOTES_INBOX_HOST_PATH MAILNOTES_DATA_HOST_PATH
mkdir -p inbox .local || exit 1

if ! command -v docker >/dev/null 2>&1; then
  open -a 'Docker' >/dev/null 2>&1 || true
  if ! command -v docker >/dev/null 2>&1; then
    printf 'Can cai Docker Desktop truoc. Xem deploy/mac-install.md\n'
    read -r _
    exit 1
  fi
fi

if ! docker info >/dev/null 2>&1; then
  open -a 'Docker' >/dev/null 2>&1 || true
  printf 'Dang cho Docker Desktop khoi dong...\n'
  count=0
  while ! docker info >/dev/null 2>&1; do
    count=$((count + 1))
    if [ "$count" -ge 60 ]; then
      printf 'Docker Desktop chua san sang. Mo Docker Desktop roi thu lai.\n'
      read -r _
      exit 1
    fi
    sleep 2
  done
fi

# A second click should only reopen the browser, not rebuild the image.
if ! docker compose ps --status running --services 2>/dev/null | grep -qx mailnotes \
   || ! curl -fsS --max-time 3 'http://localhost:8080/health' 2>/dev/null | grep -q '"app":"mailnotes"'; then
  printf 'Dang mo So ghi chep, vui long doi...\n'
  if ! docker compose up -d --build --wait mailnotes; then
    printf 'Tool chua khoi dong duoc. Xem loi phia tren va deploy/mac-install.md\n'
    read -r _
    exit 1
  fi
fi

open 'http://localhost:8080'
printf 'So ghi chep dang chay tai http://localhost:8080\n'
