@echo off
title Smart Router for Continue
echo 🚀 Starting Smart Router...

:: Cek apakah .env ada
if not exist ".env" (
    echo ❌ File .env tidak ditemukan!
    echo 💡 Salin .env.example ke .env dan isi API key Anda
    pause
    exit /b 1
)

:: Cek apakah Python ada
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python tidak ditemukan! Install Python dulu.
    pause
    exit /b 1
)

:: Install dependencies jika belum
if not exist "venv" (
    echo 📦 Membuat virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Cek apakah server sudah jalan
curl -s http://127.0.0.1:8765/health >nul 2>&1
if not errorlevel 1 (
    echo ✅ Server sudah jalan, skip start.
    exit /b 0
)

:: Start server di background (minimized)
start /min pythonw smart_router.py
echo ✅ Smart Router started in background!
echo 💡 Server akan auto-stop setelah 5 menit idle.
timeout /t 2 >nul