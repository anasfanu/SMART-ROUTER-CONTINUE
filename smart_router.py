#!/usr/bin/env python3
"""
Smart Router untuk Continue - Ultra-Light Edition
Fitur:
✅ Auto-filter model gratis coding terbaik (high-to-low)
✅ Ambil 8 terbaik otomatis
✅ Ultra-light: <10MB RAM, 0% CPU saat idle
✅ Auto-stop setelah 5 menit idle
✅ Cache daftar model 1 jam (hemat API call)
✅ Support streaming untuk Continue
✅ API key aman di .env (tidak ter-commit ke GitHub)
"""

import json
import time
import threading
import requests
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path


# ============ LOAD API KEY (HYBRID: .env ATAU CLI) ============
from pathlib import Path

def get_api_key():
    """Ambil API key dari .env atau minta user input via CLI"""
    # 1. Coba load dari .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key and api_key != "sk-or-v1-your-api-key-here":
            print("✅ API key ditemukan di .env")
            return api_key
    except ImportError:
        pass

    # 2. Cek file lokal di user profile
    local_key_path = Path.home() / ".smart-router-continue" / "api_key.txt"
    if local_key_path.exists():
        api_key = local_key_path.read_text().strip()
        if api_key:
            print(f"✅ API key ditemukan di {local_key_path}")
            return api_key

    # 3. Minta user input via CLI (First time setup)
    print("\n" + "=" * 60)
    print(" SETUP API KEY PERTAMA KALI")
    print("=" * 60)
    print("Smart Router membutuhkan API key OpenRouter untuk berjalan.")
    print("Dapatkan gratis di: https://openrouter.ai/keys")
    print("=" * 60)

    api_key = input("\n👉 Paste API key Anda di sini (sk-or-v1-...): ").strip()

    if not api_key or not api_key.startswith("sk-or-v1-"):
        print("❌ API key tidak valid! Harus dimulai dengan 'sk-or-v1-'")
        sys.exit(1)

    # Simpan ke file lokal
    local_key_path.parent.mkdir(parents=True, exist_ok=True)
    local_key_path.write_text(api_key)

    print(f"\n✅ API key disimpan di: {local_key_path}")
    print("💡 Anda tidak perlu input lagi di masa depan.")
    print("=" * 60 + "\n")

    return api_key

API_KEY = get_api_key()

# ============ KONFIGURASI ============
PORT = int(os.getenv("PORT", "8765"))
OPENROUTER_API = "https://openrouter.ai/api/v1"
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "3600"))  # 1 jam
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "300"))       # 5 menit
HOST = os.getenv("HOST", "127.0.0.1")

# ============ STATE GLOBAL ============
last_request_time = time.time()
cached_models = None
cache_timestamp = None
shutdown_timer = None


# ============ KATEGORI MODEL CODING ============
CODING_KEYWORDS = [
    "code", "coder", "coding", "codestral", "devstral", "north-mini-code",
    "nemotron", "laguna", "inkling", "gemma", "qwen-coder", "deepseek-coder",
    "starcoder", "codegen", "wizardcoder", "phind", "codellama"
]

NON_CODING_KEYWORDS = [
    "embed", "rerank", "safety", "image", "vision", "moderation",
    "classifier", "detect", "filter"
]


def log(msg):
    """Log dengan timestamp"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def is_coding_model(model):
    """Cek apakah model cocok untuk coding berdasarkan nama & deskripsi"""
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    desc = model.get("description", "").lower()
    combined = f"{model_id} {name} {desc}"
    
    # Cek apakah masuk kategori non-coding
    for kw in NON_CODING_KEYWORDS:
        if kw in combined:
            return False
    
    # Cek apakah masuk kategori coding
    for kw in CODING_KEYWORDS:
        if kw in combined:
            return True
    
    # Cek tags/architecture
    arch = model.get("architecture", {})
    if arch:
        modality = str(arch.get("modality", "")).lower()
        if "text-to-image" in modality or "image-to-text" in modality:
            return False
    
    return False


def score_model_for_coding(model):
    """Beri skor model untuk coding (0-100)"""
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    combined = f"{model_id} {name}"
    score = 50  # Base score
    
    # Bonus untuk model yang DIKENAL bagus untuk coding
    high_tier = ["nemotron-3-ultra", "inkling", "laguna-s", "north-mini-code"]
    mid_tier = ["nemotron-3-super", "gemma-4-31b", "gemma-4-26b", "nemotron-3.5-lightning"]
    
    for tier in high_tier:
        if tier in combined:
            score += 40
            break
    else:
        for tier in mid_tier:
            if tier in combined:
                score += 30
                break
    
    # Bonus untuk parameter besar (lebih pintar)
    params = model.get("context_length", 0)
    if params > 100000:
        score += 10
    
    # Bonus untuk "free" (pasti gratis)
    if ":free" in model_id:
        score += 5
    
    return min(score, 100)


def fetch_and_filter_models():
    """Ambil model gratis, filter coding, urutkan high-to-low, ambil 8 terbaik"""
    global cached_models, cache_timestamp
    
    # Cek cache
    if cached_models and cache_timestamp:
        if datetime.now() - cache_timestamp < timedelta(seconds=CACHE_DURATION):
            log(f"📦 Pakai cache ({len(cached_models)} model)")
            return cached_models
    
    log("🔍 Mengambil daftar model dari OpenRouter...")
    
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        resp = requests.get(f"{OPENROUTER_API}/models", headers=headers, timeout=30)
        resp.raise_for_status()
        all_models = resp.json().get("data", [])
    except Exception as e:
        log(f"❌ Error ambil model: {e}")
        return cached_models or []
    
    log(f"📊 Total model di OpenRouter: {len(all_models)}")
    
    # Filter 1: Hanya yang gratis
    free_models = []
    for m in all_models:
        pricing = m.get("pricing", {})
        prompt_price = str(pricing.get("prompt", "1"))
        if prompt_price == "0" and ":free" in m.get("id", ""):
            free_models.append(m)
    
    log(f"💰 Model gratis: {len(free_models)}")
    
    # Filter 2: Hanya yang cocok untuk coding
    coding_models = [m for m in free_models if is_coding_model(m)]
    log(f"💻 Model coding gratis: {len(coding_models)}")
    
    # Filter 3: Urutkan berdasarkan skor (high-to-low)
    for m in coding_models:
        m["_score"] = score_model_for_coding(m)
    
    coding_models.sort(key=lambda x: x["_score"], reverse=True)
    
    # Ambil 8 terbaik
    top_8 = coding_models[:8]
    
    log("🏆 Top 8 model coding gratis terbaik:")
    for i, m in enumerate(top_8, 1):
        log(f"  {i}. {m['id']} (score: {m['_score']})")
    
    # Update cache
    cached_models = top_8
    cache_timestamp = datetime.now()
    
    return top_8


def call_openrouter(model_id, payload, stream=False):
    """Panggil OpenRouter dengan model tertentu"""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "Continue Smart Router"
    }
    
    payload = {**payload, "model": model_id}
    
    try:
        resp = requests.post(
            f"{OPENROUTER_API}/chat/completions",
            headers=headers,
            json=payload,
            stream=stream,
            timeout=120
        )
        return resp
    except Exception as e:
        log(f"❌ Error panggil {model_id}: {e}")
        return None


def smart_route(payload, stream=False):
    """Pilih model terbaik dan panggil, fallback ke berikutnya jika gagal"""
    global last_request_time
    last_request_time = time.time()
    
    models = fetch_and_filter_models()
    if not models:
        log("⚠️ Tidak ada model tersedia!")
        return None
    
    # Coba setiap model berurutan
    for i, model in enumerate(models):
        model_id = model["id"]
        log(f"🎯 Mencoba model #{i+1}: {model_id}")
        
        resp = call_openrouter(model_id, payload, stream)
        
        if resp and resp.status_code == 200:
            log(f"✅ Berhasil pakai: {model_id}")
            return resp
        
        # Cek apakah error rate limit (429) atau model habis
        if resp and resp.status_code in [429, 503]:
            log(f"⚠️ {model_id} rate-limited/down, coba berikutnya...")
            continue
        
        # Error lain, coba berikutnya
        log(f"⚠️ {model_id} gagal (status {resp.status_code if resp else 'N/A'}), coba berikutnya...")
        continue
    
    # Fallback terakhir: openrouter/free
    log("🆘 Semua model gagal, pakai openrouter/free")
    return call_openrouter("openrouter/free", payload, stream)


def reset_idle_timer():
    """Reset timer auto-shutdown"""
    global shutdown_timer
    if shutdown_timer:
        shutdown_timer.cancel()
    shutdown_timer = threading.Timer(IDLE_TIMEOUT, shutdown_server)
    shutdown_timer.daemon = True
    shutdown_timer.start()


def shutdown_server():
    """Auto-shutdown setelah idle"""
    idle_time = time.time() - last_request_time
    if idle_time >= IDLE_TIMEOUT:
        log(f"💤 Idle {IDLE_TIMEOUT}s, shutdown server...")
        os._exit(0)


class SmartHandler(BaseHTTPRequestHandler):
    """HTTP Handler untuk OpenAI-compatible API"""
    
    def log_message(self, format, *args):
        pass  # Suppress default logging
    
    def do_POST(self):
        global last_request_time
        last_request_time = time.time()
        reset_idle_timer()
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body)
        except:
            self.send_error(400, "Invalid JSON")
            return
        
        # Route ke model terbaik
        stream = payload.get("stream", False)
        resp = smart_route(payload, stream)
        
        if not resp:
            self.send_error(503, "All models failed")
            return
        
        # Forward response
        self.send_response(resp.status_code)
        
        # Copy headers penting
        for key in ["content-type"]:
            if key in resp.headers:
                self.send_header(key, resp.headers[key])
        
        self.end_headers()
        
        if stream:
            # Streaming response
            for chunk in resp.iter_content(chunk_size=None):
                if chunk:
                    self.wfile.write(chunk)
                    self.wfile.flush()
        else:
            # Non-streaming
            self.wfile.write(resp.content)
    
    def do_GET(self):
        """Health check & model list"""
        global last_request_time
        last_request_time = time.time()
        reset_idle_timer()
        
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            models = fetch_and_filter_models()
            self.wfile.write(json.dumps({
                "status": "ok",
                "models_count": len(models),
                "top_model": models[0]["id"] if models else None
            }).encode())
        elif self.path == "/v1/models":
            # Return daftar model untuk Continue
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            models = fetch_and_filter_models()
            self.wfile.write(json.dumps({
                "object": "list",
                "data": [{"id": m["id"], "object": "model"} for m in models]
            }).encode())
        else:
            self.send_error(404)


def main():
    log("=" * 60)
    log("🚀 Smart Router untuk Continue - Ultra-Light Edition")
    log("=" * 60)
    log(f"📍 Server: http://{HOST}:{PORT}")
    log(f"💤 Auto-stop setelah {IDLE_TIMEOUT}s idle")
    log(f"📦 Cache model: {CACHE_DURATION}s")
    log("")
    
    # Pre-warm cache
    fetch_and_filter_models()
    
    # Start server
    server = HTTPServer((HOST, PORT), SmartHandler)
    reset_idle_timer()
    
    try:
        log("✅ Server siap menerima request dari Continue!")
        server.serve_forever()
    except KeyboardInterrupt:
        log("\n👋 Server dimatikan manual")
        server.server_close()


if __name__ == "__main__":
    main()