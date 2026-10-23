#!/bin/bash
# Smart Router - Stop (Linux) — klik dua kali untuk menghentikan server + test/mock
cd "$(dirname "$0")" || exit 1
PIDFILE="./smart_router.pid"

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    kill "$(cat "$PIDFILE")" 2>/dev/null
    echo "🛑 Smart Router dihentikan (PID $(cat "$PIDFILE"))."
    rm -f "$PIDFILE"
else
    echo "ℹ️  Tidak ada Smart Router yang berjalan."
fi

# Bersihkan proses test / mock upstream bila masih tersisa
pkill -f "test_mock_upstream.py" 2>/dev/null && echo "🧹 Mock upstream dibersihkan."
pkill -f "test_router.py" 2>/dev/null && echo "🧹 Proses test dibersihkan."
# Fallback: router yang dijalankan manual (tanpa PID file) tetap ikut dibersihkan
pkill -f "smart_router.py" 2>/dev/null && echo "🧹 Sisa proses router dibersihkan."

read -p "Tekan Enter untuk menutup jendela ini..."
