@echo off
title Smart Router - Stop (Windows)
rem Wrapper tipis. SELURUH logika stop ada di smart_router.py
rem (kill via PID file + pembersihan sisa proses router/test/mock).
cd /d "%~dp0"
python smart_router.py --stop
pause
