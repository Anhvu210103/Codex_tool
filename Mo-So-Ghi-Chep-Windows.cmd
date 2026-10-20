@echo off
setlocal
cd /d "%~dp0"
where docker >nul 2>nul
if errorlevel 1 (
  echo Chua tim thay Docker Desktop. Cai va mo Docker Desktop truoc khi chay tool.
  pause
  exit /b 1
)
docker compose up -d --build --wait mailnotes
if errorlevel 1 (
  echo Khong mo duoc tool. Kiem tra Docker Desktop va doc loi o tren.
  pause
  exit /b 1
)
echo Dang mo So ghi chep tai http://localhost:8080
start "" "http://localhost:8080"
endlocal
