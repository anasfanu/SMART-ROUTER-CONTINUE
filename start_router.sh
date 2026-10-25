#!/bin/bash
# Smart Router - Start (Linux) — wrapper tipis. SELURUH logika start ada di smart_router.py
# (validasi .env, dependency, kill lama, spawn background, health check).
cd "$(dirname "$0")" || exit 1
python3 smart_router.py
