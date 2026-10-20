#!/bin/sh
cd -- "$(dirname -- "$0")" || exit 1
python3 Cap-Nhat-Tool.py
result=$?
printf '\nNhấn Enter để đóng.\n'
read answer
exit "$result"
