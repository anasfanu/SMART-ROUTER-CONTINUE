@echo off
title Smart Router - Stop (Windows)
rem Smart Router - Stop (Windows) - klik dua kali untuk kill router + test + mock

echo 🛑 Menghentikan Smart Router, test, dan mock...
wmic process where "commandline like '%%smart_router.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%test_mock_upstream.py%%'" delete >nul 2>&1
wmic process where "commandline like '%%test_router.py%%'" delete >nul 2>&1
echo ✅ Selesai. Semua proses dibersihkan.
echo.
pause
