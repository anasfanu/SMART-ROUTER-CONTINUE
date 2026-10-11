#!/bin/bash
echo "🚀 Starting Smart Router..."

# Cek apakah .env ada
if [ ! -f ".env" ]; then
    echo "❌ File .env tidak ditemukan!"
    echo "💡 Salin .env.example ke .env dan isi API key Anda"
    exit 1
fi

# Cek apakah server sudah jalan
if curl -s http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo "✅ Server sudah jalan, skip start."
    exit 0
fi

# Install dependencies jika belum
if [ ! -d "venv" ]; then
    echo "📦 Membuat virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start server di background
nohup python smart_router.py > /tmp/smart_router.log 2>&1 &
echo "✅ Smart Router started! PID: $!"
echo "💡 Server akan auto-stop setelah 5 menit idle."