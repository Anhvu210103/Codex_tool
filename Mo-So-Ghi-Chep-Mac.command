#!/bin/sh
# Double-click launcher for the Docker Desktop build on macOS.
cd "$(dirname "$0")" || exit 1
PATH="/usr/local/bin:/opt/homebrew/bin:/Applications/Docker.app/Contents/Resources/bin:$PATH"
export PATH

if ! command -v docker >/dev/null 2>&1; then
  open -a 'Docker' >/dev/null 2>&1 || true
  if ! command -v docker >/dev/null 2>&1; then
    printf 'Can cai Docker Desktop truoc. Xem deploy/mac-partner.md\n'
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

if ! docker compose up -d --build --wait mailnotes; then
  printf 'Tool chua khoi dong duoc. Xem loi phia tren va deploy/mac-partner.md\n'
  read -r _
  exit 1
fi

open 'http://localhost:8080'
printf 'So ghi chep dang chay tai http://localhost:8080\n'
