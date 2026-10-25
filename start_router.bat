@echo off
title Smart Router - Start (Windows)
rem Wrapper tipis. SELURUH logika start ada di smart_router.py
rem (validasi .env, dependency, kill lama, spawn background pythonw, health check).
cd /d "%~dp0"
python smart_router.py
