@echo off
title Smart Router - Start (Windows)
rem Smart Router - Start (Windows) - cukup klik dua kali file ini
cd /d "%~dp0"

echo.
echo 🚀 Starting Smart Router...
echo.

rem API key HANYA dari file .env (tidak ada prompt CLI)
if not exist ".env" (
    echo ❌ File .env tidak ditemukan!
    echo 💡 Salin .env.example ke .env lalu isi API key Anda:
    echo     copy .env.example .env
    echo.
    pause
    exit /b 1
)

rem Cek Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python tidak ditemukan! Install Python dulu dari python.org
    echo.
    pause
    exit /b 1
)

rem Kill proses router/test/mock lama agar bersih saat di-klik ulang
wmic process where "commandline like '%%smart_router.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%test_mock_upstream.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%test_router.py%%'" delete >nul 2>&1

rem Install dependencies jika belum ada venv
if not exist "venv" (
    echo 📦 Membuat virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -q -r requirements.txt

rem Start server di background (minimized, auto-stop setelah idle)
start "" /min pythonw smart_router.py
timeout /t 2 >nul
echo ✅ Smart Router jalan di background → http://127.0.0.1:8765
echo 💡 Auto-stop setelah 5 menit idle. Stop manual: double-click stop_router.bat
echo.
pause
