#!/bin/bash
# Smart Router - Start (Linux) — cukup klik dua kali / jalankan ./start_router.sh
cd "$(dirname "$0")" || exit 1
# Simpan log & PID di folder project (bukan $HOME) agar mudah ditemukan & tidak bentrok antar salinan project
LOG="./smart_router.log"
PIDFILE="./smart_router.pid"

echo "🚀 Starting Smart Router..."

# API key HANYA dari file .env (tidak ada prompt CLI)
if [ ! -f ".env" ]; then
    echo "❌ File .env tidak ditemukan!"
    echo "💡 Salin .env.example ke .env lalu isi API key Anda:"
    echo "   cp .env.example .env"
    read -p "Tekan Enter untuk keluar..."
    exit 1
fi

# Kalau sudah jalan -> restart bersih (kill lama, start baru)
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "♻️  Server sudah jalan (PID $(cat "$PIDFILE")), restart..."
    kill "$(cat "$PIDFILE")" 2>/dev/null
    sleep 1
fi

# Install dependencies jika belum ada venv (venv dipakai bersama, tidak boleh ikut terhapus .gitignore)
if [ ! -d "venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv venv || { read -p "Gagal. Tekan Enter..."; exit 1; }
fi
source venv/bin/activate
pip install -q -r requirements.txt || echo "⚠️  Gagal install dependency (mungkin offline). Mencoba tetap jalan..."

# Start server di background (auto-stop sendiri setelah idle)
nohup python smart_router.py > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
sleep 2

if kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    ROUTER_PORT=$(grep -E '^PORT=' ".env" | tail -n1 | cut -d= -f2 | tr -d '"'"'\r")
    echo "✅ Smart Router jalan! PID $(cat "$PIDFILE") → http://127.0.0.1:${ROUTER_PORT:-8765}"
    echo "💡 Log: $LOG | Auto-stop setelah 5 menit idle. Stop manual: ./stop_router.sh"
else
    echo "❌ Gagal start. Cek log: $LOG"
    tail -n 5 "$LOG"
    rm -f "$PIDFILE"
fi
read -p "Tekan Enter untuk menutup jendela ini..."
