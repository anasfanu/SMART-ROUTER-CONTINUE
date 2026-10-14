#!/usr/bin/env python3
"""
Smart Router untuk Continue - Dual Provider (Groq Priority + OpenRouter)
Groq diprioritaskan karena kecepatan LPU, OpenRouter sebagai cadangan.
"""

import json
import time
import threading
import requests
import sys
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from pathlib import Path

# ============ 1. LOAD API KEY ============
def get_api_key(provider):
    """Ambil API key dari .env atau input CLI"""
    env_var = f"{provider}_API_KEY"
    try:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv(env_var)
        if api_key and not api_key.startswith("your-") and len(api_key) > 10:
            return api_key
    except ImportError:
        pass

    local_key_path = Path.home() / ".smart-router-continue" / f"{provider.lower()}_key.txt"
    if local_key_path.exists():
        key = local_key_path.read_text().strip()
        if key and len(key) > 10:
            return key

    print(f"\n🔑 SETUP {provider} API KEY")
    api_key = input(f"👉 Paste {provider} API Key (atau kosongkan untuk skip): ").strip()
    if api_key and len(api_key) > 10:
        local_key_path.parent.mkdir(parents=True, exist_ok=True)
        local_key_path.write_text(api_key)
        return api_key
    return None

OPENROUTER_API_KEY = get_api_key("OPENROUTER")
GROQ_API_KEY = get_api_key("GROQ")

# Debug: Tampilkan status API key
print("\n" + "=" * 60)
print(" STATUS API KEY:")
print(f"   OpenRouter: {'✅ Ter-load' if OPENROUTER_API_KEY else '❌ Tidak ada'}")
print(f"   Groq:       {'✅ Ter-load' if GROQ_API_KEY else '❌ Tidak ada'}")
print("=" * 60 + "\n")

if not OPENROUTER_API_KEY and not GROQ_API_KEY:
    print("❌ ERROR: Minimal satu API Key harus diisi!")
    sys.exit(1)

# ============ 2. KONFIGURASI ============
PORT = int(os.getenv("PORT", "8765"))
HOST = os.getenv("HOST", "127.0.0.1")
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "3600"))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "300"))

# ============ 3. STATE GLOBAL ============
last_request_time = time.time()
cached_models = None
cache_timestamp = None
shutdown_timer = None

# ============ 4. KATEGORI MODEL ============
CODING_KEYWORDS = [
    "code", "coder", "coding", "instruct", "chat", "versatile", "instant",
    "qwq", "r1", "distill", "llama", "mixtral", "gemma", "qwen", "deepseek",
    "nemotron", "laguna", "inkling", "north-mini"
]

NON_CODING_KEYWORDS = [
    "embed", "rerank", "safety", "image", "vision", "moderation",
    "classifier", "detect", "filter", "whisper", "tts", "speech",
    "guard", "tokenizer"
]

# ============ 5. FUNGSI UTAMA ============
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def is_coding_model(model):
    """Cek apakah model cocok untuk coding"""
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    desc = model.get("description", "").lower()
    combined = f"{model_id} {name} {desc}"
    
    for kw in NON_CODING_KEYWORDS:
        if kw in combined:
            return False
    for kw in CODING_KEYWORDS:
        if kw in combined:
            return True
    return False

def score_model_for_coding(model, provider):
    """Beri skor - GROQ DIPRIORITASKAN (bonus +50)"""
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    combined = f"{model_id} {name}"
    
    # Base score
    score = 50
    
    # 🚀 GROQ BONUS BESAR (kecepatan LPU) - selalu di atas OpenRouter
    if provider == "groq":
        score += 50  # Groq selalu menang skor
    
    # Bonus model high-tier
    high_tier = [
        "llama-3.3-70b", "llama3-70b", "llama-3.1-70b",
        "mixtral-8x7b", "qwq-32b", "deepseek-r1-distill-llama-70b",
        "nemotron-3-ultra", "inkling"
    ]
    for tier in high_tier:
        if tier in combined:
            score += 20
            break
    
    # Bonus model medium-tier
    mid_tier = [
        "llama-3.1-8b", "llama3-8b", "gemma2-9b", "gemma-7b",
        "nemotron-3.5", "laguna", "north-mini"
    ]
    for tier in mid_tier:
        if tier in combined:
            score += 10
            break
    
    # Bonus free tier OpenRouter
    if ":free" in model_id:
        score += 5
    
    return min(score, 100)

def fetch_and_filter_models():
    """Ambil model dari Groq DULU (prioritas), lalu OpenRouter"""
    global cached_models, cache_timestamp
    
    if cached_models and cache_timestamp:
        if datetime.now() - cache_timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_models

    unified_models = []

    #  1. AMBIL DARI GROQ DULU (PRIORITAS UTAMA)
    if GROQ_API_KEY:
        log("🔍 Mengambil model dari Groq...")
        try:
            resp = requests.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                timeout=15
            )
            resp.raise_for_status()
            groq_models = resp.json().get("data", [])
            log(f"   Ditemukan {len(groq_models)} model di Groq")
            
            for m in groq_models:
                model_id = m.get("id", "")
                # Filter lebih luas: terima semua model chat/instruct Groq
                if is_coding_model(m):
                    unified_models.append({
                        "id": model_id,
                        "title": f"[GROQ] {model_id}",
                        "score": score_model_for_coding(m, "groq"),
                        "provider": "groq",
                        "api_key": GROQ_API_KEY,
                        "base_url": "https://api.groq.com/openai/v1"
                    })
            log(f"   ✅ {len([m for m in unified_models if m['provider']=='groq'])} model Groq lolos filter coding")
        except Exception as e:
            log(f"   ❌ Gagal ambil model Groq: {e}")
    else:
        log("⚠️ Groq API key tidak ada, skip Groq")

    #  2. AMBIL DARI OPENROUTER (CADANGAN)
    if OPENROUTER_API_KEY:
        log("🔍 Mengambil model dari OpenRouter...")
        try:
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
                timeout=15
            )
            resp.raise_for_status()
            or_models = resp.json().get("data", [])
            log(f"   Ditemukan {len(or_models)} model di OpenRouter")
            
            for m in or_models:
                pricing = m.get("pricing", {})
                prompt_price = str(pricing.get("prompt", "1"))
                if prompt_price == "0" and ":free" in m.get("id", ""):
                    if is_coding_model(m):
                        unified_models.append({
                            "id": m["id"],
                            "title": f"[OR] {m.get('name', m['id'])}",
                            "score": score_model_for_coding(m, "openrouter"),
                            "provider": "openrouter",
                            "api_key": OPENROUTER_API_KEY,
                            "base_url": "https://openrouter.ai/api/v1"
                        })
            log(f"   ✅ {len([m for m in unified_models if m['provider']=='openrouter'])} model OpenRouter gratis lolos filter")
        except Exception as e:
            log(f"   ❌ Gagal ambil model OpenRouter: {e}")

    # 3. URUTKAN: Groq di atas (skor lebih tinggi), lalu OpenRouter
    unified_models.sort(key=lambda x: x["score"], reverse=True)
    
    # Ambil 12 terbaik
    cached_models = unified_models[:12]
    cache_timestamp = datetime.now()
    
    log("\n" + "=" * 60)
    log(f"🏆 Top {len(cached_models)} Model (Groq Priority):")
    log("=" * 60)
    for i, m in enumerate(cached_models, 1):
        provider_tag = "🚀" if m["provider"] == "groq" else "🌐"
        log(f"  {i:2}. {provider_tag} [{m['provider'].upper():10}] {m['id']} (Score: {m['score']})")
    log("=" * 60 + "\n")
        
    return cached_models

def optimize_prompt_messages(messages):
    """Optimasi prompt untuk hemat token"""
    optimized = []
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            content = re.sub(r'\n{3,}', '\n\n', content)
            lines = [line.strip() for line in content.split('\n')]
            content = '\n'.join(lines)
        optimized.append({"role": msg.get("role", "user"), "content": content})
    return optimized

def call_llm(model_info, payload, stream=False):
    """Panggil API dinamis"""
    headers = {
        "Authorization": f"Bearer {model_info['api_key']}",
        "Content-Type": "application/json"
    }
    if model_info['provider'] == 'openrouter':
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "Continue Smart Router"

    payload = {**payload, "model": model_info['id']}
    
    try:
        resp = requests.post(
            f"{model_info['base_url']}/chat/completions",
            headers=headers, json=payload, stream=stream, timeout=120
        )
        return resp
    except Exception as e:
        log(f"❌ Error panggil {model_info['id']}: {e}")
        return None

def smart_route(payload, stream=False):
    """Route dengan stateful continuation"""
    global last_request_time
    last_request_time = time.time()
    
    models = fetch_and_filter_models()
    if not models:
        log("⚠️ Tidak ada model tersedia!")
        return None

    original_messages = payload.get("messages", [])
    optimized_messages = optimize_prompt_messages(original_messages)
    accumulated_response = ""

    for i, model in enumerate(models):
        provider_emoji = "🚀" if model["provider"] == "groq" else ""
        log(f"🎯 Mencoba #{i+1} {provider_emoji} {model['id']}")
        
        current_messages = optimized_messages.copy()
        
        if accumulated_response:
            log(f"💡 Melanjutkan dari {len(accumulated_response)} karakter...")
            current_messages.append({"role": "assistant", "content": accumulated_response})
            current_messages.append({
                "role": "user",
                "content": "[SYSTEM: Lanjutkan dari titik terakhir. JANGAN ulangi bagian yang sudah ditulis.]"
            })

        try:
            resp = call_llm(model, {"messages": current_messages, "stream": stream}, stream)
            
            if resp and resp.status_code == 200:
                log(f"✅ Berhasil: {model['id']}")
                if stream:
                    def stream_with_state():
                        nonlocal accumulated_response
                        try:
                            for line in resp.iter_lines():
                                if line:
                                    line_str = line.decode('utf-8')
                                    yield line_str + "\n"
                                    if line_str.startswith("data: "):
                                        json_str = line_str[6:]
                                        if json_str.strip() == "[DONE]": break
                                        try:
                                            data = json.loads(json_str)
                                            delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                            if delta: accumulated_response += delta
                                        except: pass
                        except Exception as e:
                            log(f"⚠️ Stream terputus di {model['id']}: {e}")
                            raise Exception("Stream interrupted")
                    return stream_with_state()
                else:
                    try:
                        resp_json = resp.json()
                        accumulated_response = resp_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return resp
                    except Exception as e:
                        log(f"️ Gagal parse JSON: {e}")
                        continue
            elif resp and resp.status_code in [429, 500, 502, 503]:
                log(f"⚠️ {model['id']} rate-limited/down ({resp.status_code}), rotasi...")
                continue
            else:
                log(f"️ {model['id']} gagal ({resp.status_code if resp else 'N/A'}), rotasi...")
                continue
        except Exception as e:
            log(f"❌ {model['id']} error: {e}. Lanjut ke model berikutnya...")
            continue

    # Fallback terakhir
    if OPENROUTER_API_KEY:
        log("🆘 Semua gagal, coba openrouter/free...")
        try:
            fallback = optimized_messages[-5:]
            if accumulated_response:
                fallback.append({"role": "assistant", "content": accumulated_response})
                fallback.append({"role": "user", "content": "[SYSTEM: Lanjutkan dari sini]"})
            return call_llm(
                {"id": "openrouter/free", "api_key": OPENROUTER_API_KEY, 
                 "base_url": "https://openrouter.ai/api/v1", "provider": "openrouter"},
                {"messages": fallback, "stream": stream}, stream
            )
        except Exception as e:
            log(f"❌ Fallback gagal: {e}")
    return None

def reset_idle_timer():
    global shutdown_timer
    if shutdown_timer: shutdown_timer.cancel()
    shutdown_timer = threading.Timer(IDLE_TIMEOUT, shutdown_server)
    shutdown_timer.daemon = True
    shutdown_timer.start()

def shutdown_server():
    idle_time = time.time() - last_request_time
    if idle_time >= IDLE_TIMEOUT:
        log(f"💤 Idle {IDLE_TIMEOUT}s, shutdown...")
        os._exit(0)

class SmartHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    
    def do_POST(self):
        global last_request_time
        last_request_time = time.time()
        reset_idle_timer()
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try: payload = json.loads(body)
        except: self.send_error(400, "Invalid JSON"); return
        
        stream = payload.get("stream", False)
        resp = smart_route(payload, stream)
        
        if not resp: self.send_error(503, "All models failed"); return
        
        self.send_response(resp.status_code)
        for key in ["content-type"]:
            if key in resp.headers: self.send_header(key, resp.headers[key])
        self.end_headers()
        
        if stream:
            for chunk in resp.iter_content(chunk_size=None):
                if chunk:
                    self.wfile.write(chunk)
                    self.wfile.flush()
        else:
            self.wfile.write(resp.content)

    def do_GET(self):
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
                "groq_count": len([m for m in models if m["provider"]=="groq"]),
                "openrouter_count": len([m for m in models if m["provider"]=="openrouter"])
            }).encode())
        else: self.send_error(404)

def main():
    log("=" * 60)
    log("🚀 Smart Router: Groq Priority + OpenRouter Fallback")
    log("=" * 60)
    log(f"📍 Server: http://{HOST}:{PORT}")
    log(f" Auto-stop: {IDLE_TIMEOUT}s idle")
    
    fetch_and_filter_models()
    
    server = HTTPServer((HOST, PORT), SmartHandler)
    reset_idle_timer()
    try:
        log("✅ Server siap! Continue bisa mulai digunakan.")
        server.serve_forever()
    except KeyboardInterrupt:
        log("\n👋 Server dimatikan manual")
        server.server_close()

if __name__ == "__main__":
    main()