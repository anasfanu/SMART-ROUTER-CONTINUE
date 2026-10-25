#!/bin/bash
# Smart Router - Stop (Linux) — wrapper tipis. SELURUH logika stop ada di smart_router.py
# (kill via PID file + pembersihan sisa proses router/test/mock).
cd "$(dirname "$0")" || exit 1
python3 smart_router.py --stop
