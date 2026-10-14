#!/usr/bin/env python3
"""
Smart Router untuk Continue - Hybrid Dual Provider (Groq + OpenRouter)
Fix: Per-chunk timeout, proper ReadTimeout handling, client disconnect handling.
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
from queue import Queue, Empty

# ============ 1. LOAD API KEY ============
def get_api_key(provider):
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

    print(f"\n SETUP {provider} API KEY")
    api_key = input(f"👉 Paste {provider} API Key (atau kosongkan untuk skip): ").strip()
    if api_key and len(api_key) > 10:
        local_key_path.parent.mkdir(parents=True, exist_ok=True)
        local_key_path.write_text(api_key)
        return api_key
    return None

OPENROUTER_API_KEY = get_api_key("OPENROUTER")
GROQ_API_KEY = get_api_key("GROQ")

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
CHUNK_TIMEOUT = 20  # Timeout per chunk (detik) - ANTI HANG

# ============ 3. STATE GLOBAL ============
last_request_time = time.time()
cached_models = None
cache_timestamp = None
shutdown_timer = None

# ============ 4. BLACKLIST MODEL LAMBAT ============
SLOW_MODELS = [
    "qwen/qwen3.8-27b",
    "qwen-2.5-coder-32b",
    "nvidia/nemotron-3-ultra-550b",
    "nvidia/nemotron-3-super-120b",
]

NON_CODING_KEYWORDS = [
    "embed", "rerank", "safety", "image", "vision", "moderation",
    "classifier", "detect", "filter", "whisper", "tts", "speech",
    "guard", "tokenizer", "audio", "stt", "asr"
]

CODING_KEYWORDS = [
    "code", "coder", "coding", "instruct", "chat", "versatile", "instant",
    "qwq", "r1", "distill", "llama", "mixtral", "gemma", "qwen", "deepseek",
    "nemotron", "laguna", "inkling", "north-mini", "lfm"
]

# ============ 5. FUNGSI UTAMA ============
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def is_slow_model(model_id):
    mid = model_id.lower()
    for slow in SLOW_MODELS:
        if slow in mid:
            return True
    return False

def is_non_coding(model_id):
    mid = model_id.lower()
    for kw in NON_CODING_KEYWORDS:
        if kw in mid:
            return True
    return False

def is_coding_model(model, provider):
    model_id = model.get("id", "")
    if is_slow_model(model_id):
        return False
    if is_non_coding(model_id):
        return False
    if provider == "groq":
        return True
    name = model.get("name", "").lower()
    combined = f"{model_id.lower()} {name}"
    for kw in CODING_KEYWORDS:
        if kw in combined:
            return True
    return False

def score_model_for_coding(model, provider):
    model_id = model.get("id", "").lower()
    name = model.get("name", "").lower()
    combined = f"{model_id} {name}"
    
    if provider == "groq":
        score = 70
        if "llama-3.1-70b" in combined or "llama3-70b" in combined:
            score += 25
        elif "llama-3.3-70b" in combined:
            score += 25
        elif "mixtral-8x7b" in combined:
            score += 22
        elif "deepseek-r1-distill-llama-70b" in combined:
            score += 20
        elif "qwq-32b" in combined:
            score += 18
        elif "gemma2-9b" in combined:
            score += 15
        elif "llama-3.1-8b" in combined or "llama3-8b" in combined:
            score += 12
        else:
            score += 5
    else:
        score = 50
        if "nemotron-3-ultra" in combined and "550b" not in combined:
            score += 25
        elif "inkling" in combined:
            score += 22
        elif "nemotron-3.5" in combined:
            score += 18
        elif "laguna" in combined:
            score += 15
        elif "north-mini" in combined:
            score += 12
        elif ":free" in model_id:
            score += 5
    
    return score

def fetch_and_filter_models():
    global cached_models, cache_timestamp
    
    if cached_models and cache_timestamp:
        if datetime.now() - cache_timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_models

    unified_models = []

    if GROQ_API_KEY:
        log(" Mengambil Model dari Groq...")
        try:
            resp = requests.get("https://api.groq.com/openai/v1/models", 
                                headers={"Authorization": f"Bearer {GROQ_API_KEY}"}, timeout=15)
            resp.raise_for_status()
            all_groq_models = resp.json().get("data", [])
            log(f"   📦 Total {len(all_groq_models)} model dari Groq API")
            
            groq_candidates = []
            for m in all_groq_models:
                model_id = m.get("id", "")
                if is_coding_model(m, "groq"):
                    groq_candidates.append({
                        "id": model_id,
                        "title": f"[GROQ] {model_id}",
                        "score": score_model_for_coding(m, "groq"),
                        "provider": "groq",
                        "api_key": GROQ_API_KEY,
                        "base_url": "https://api.groq.com/openai/v1"
                    })
            
            groq_candidates.sort(key=lambda x: x["score"], reverse=True)
            top_groq = groq_candidates[:5]
            unified_models.extend(top_groq)
            log(f"   ✅ {len(top_groq)} model Groq terpilih")
            for m in top_groq:
                log(f"      🚀 {m['id']} (Score: {m['score']})")
                
        except Exception as e:
            log(f"   ❌ Gagal ambil model Groq: {e}")

    if OPENROUTER_API_KEY:
        log("🔍 Mengambil Model Gratis dari OpenRouter...")
        try:
            resp = requests.get("https://openrouter.ai/api/v1/models", 
                                headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, timeout=15)
            resp.raise_for_status()
            or_count = 0
            for m in resp.json().get("data", []):
                pricing = m.get("pricing", {})
                if str(pricing.get("prompt", "1")) == "0" and ":free" in m.get("id", ""):
                    if is_coding_model(m, "openrouter"):
                        unified_models.append({
                            "id": m["id"],
                            "title": f"[OR] {m.get('name', m['id'])}",
                            "score": score_model_for_coding(m, "openrouter"),
                            "provider": "openrouter",
                            "api_key": OPENROUTER_API_KEY,
                            "base_url": "https://openrouter.ai/api/v1"
                        })
                        or_count += 1
            log(f"   ✅ {or_count} model OpenRouter gratis lolos filter")
        except Exception as e:
            log(f"   ❌ Gagal ambil model OpenRouter: {e}")

    unified_models.sort(key=lambda x: x["score"], reverse=True)
    cached_models = unified_models[:15]
    cache_timestamp = datetime.now()
    
    log("\n" + "=" * 60)
    log(f"🏆 Top {len(cached_models)} Model Pool:")
    log("=" * 60)
    for i, m in enumerate(cached_models, 1):
        tag = "🚀" if m["provider"] == "groq" else "🌐"
        log(f"  {i:2}. {tag} [{m['provider'].upper():10}] {m['id']} (Score: {m['score']})")
    log("=" * 60 + "\n")
        
    return cached_models

def optimize_prompt_messages(messages):
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
    """Panggil API - raise exception jika timeout, jangan return None"""
    headers = {"Authorization": f"Bearer {model_info['api_key']}", "Content-Type": "application/json"}
    if model_info['provider'] == 'openrouter':
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "Continue Smart Router"

    payload = {**payload, "model": model_info['id']}
    
    # Raise exception jika timeout (biar di-handle di caller)
    resp = requests.post(
        f"{model_info['base_url']}/chat/completions", 
        headers=headers, json=payload, stream=stream, timeout=(5, 30)
    )
    return resp

def stream_with_chunk_timeout(resp, timeout_seconds):
    """
    Wrapper untuk iter_lines() dengan timeout per chunk.
    FIX BUG #1: Anti-hang jika model kirim data lambat.
    """
    chunk_queue = Queue(maxsize=100)
    stop_event = threading.Event()
    
    def reader_thread():
        try:
            for line in resp.iter_lines():
                if stop_event.is_set():
                    break
                if line:
                    chunk_queue.put(line)
        except Exception as e:
            chunk_queue.put(("ERROR", str(e)))
        finally:
            chunk_queue.put(None)  # Signal selesai
    
    thread = threading.Thread(target=reader_thread, daemon=True)
    thread.start()
    
    while not stop_event.is_set():
        try:
            item = chunk_queue.get(timeout=timeout_seconds)
            if item is None:
                break  # Stream selesai
            if isinstance(item, tuple) and item[0] == "ERROR":
                raise Exception(item[1])
            yield item
        except Empty:
            raise TimeoutError(f"Chunk timeout setelah {timeout_seconds} detik")
    
    stop_event.set()
    thread.join(timeout=2)

def smart_route(payload, stream=False):
    global last_request_time
    last_request_time = time.time()
    
    models = fetch_and_filter_models()
    if not models:
        log("⚠️ Tidak ada model tersedia!")
        return None

    optimized_messages = optimize_prompt_messages(payload.get("messages", []))

    if not stream:
        for model in models:
            try:
                resp = call_llm(model, {"messages": optimized_messages, "stream": False}, False)
                if resp and resp.status_code == 200:
                    log(f"✅ Berhasil (Non-stream): {model['id']}")
                    return resp
                elif resp:
                    log(f"⚠️ {model['id']} gagal (Status {resp.status_code}), rotasi...")
            except requests.exceptions.Timeout:
                log(f"⏱️ {model['id']} timeout, rotasi...")
            except Exception as e:
                log(f"❌ {model['id']} error: {e}, rotasi...")
        return None
    else:
        def stream_generator():
            accumulated_response = ""
            model_idx = 0
            
            while model_idx < len(models):
                model = models[model_idx]
                log(f"🎯 Streaming dengan model #{model_idx+1}: {model['id']}")
                
                current_messages = optimized_messages.copy()
                if accumulated_response:
                    log(f"💡 Melanjutkan dari {len(accumulated_response)} karakter...")
                    current_messages.append({"role": "assistant", "content": accumulated_response})
                    current_messages.append({"role": "user", "content": "[SYSTEM: Lanjutkan dari titik terakhir. JANGAN ulangi bagian yang sudah ditulis.]"})
                
                try:
                    resp = call_llm(model, {"messages": current_messages, "stream": True}, True)
                    
                    if resp.status_code != 200:
                        log(f"️ {model['id']} gagal (Status {resp.status_code}), rotasi...")
                        model_idx += 1
                        continue
                    
                    log(f"✅ Berhasil stream: {model['id']}")
                    stream_completed = False
                    
                    # FIX BUG #1: Gunakan chunk timeout wrapper
                    for line in stream_with_chunk_timeout(resp, CHUNK_TIMEOUT):
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            json_str = line_str[6:]
                            if json_str == '[DONE]':
                                yield "data: [DONE]\n\n"
                                stream_completed = True
                                break
                            try:
                                data = json.loads(json_str)
                                delta = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if delta:
                                    accumulated_response += delta
                                yield f"data: {json.dumps(data)}\n\n"
                            except json.JSONDecodeError:
                                pass
                    
                    if stream_completed:
                        return
                    else:
                        log(f"⚠️ Stream {model['id']} terputus, rotasi...")
                        model_idx += 1
                        
                except TimeoutError as e:
                    log(f"⏱️ {model['id']} hang ({e}), rotasi paksa...")
                    model_idx += 1
                except requests.exceptions.Timeout:
                    log(f"️ {model['id']} timeout, rotasi...")
                    model_idx += 1
                except Exception as e:
                    log(f"❌ {model['id']} error: {e}. Rotasi...")
                    model_idx += 1
            
            yield "data: [DONE]\n\n"

        return stream_generator()

def reset_idle_timer():
    global shutdown_timer
    if shutdown_timer:
        shutdown_timer.cancel()
    shutdown_timer = threading.Timer(IDLE_TIMEOUT, shutdown_server)
    shutdown_timer.daemon = True
    shutdown_timer.start()

def shutdown_server():
    idle_time = time.time() - last_request_time
    if idle_time >= IDLE_TIMEOUT:
        log(f"💤 Idle {IDLE_TIMEOUT}s, shutdown server...")
        os._exit(0)

class SmartHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
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
        
        stream = payload.get("stream", False)
        result = smart_route(payload, stream)
        
        if not result:
            self.send_error(503, "All models failed")
            return
        
        if stream:
            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            
            try:
                for chunk in result:
                    if chunk:
                        if isinstance(chunk, str):
                            self.wfile.write(chunk.encode('utf-8'))
                        else:
                            self.wfile.write(chunk)
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                log("⚠️ Client disconnect (user stop)")
            except Exception as e:
                log(f"❌ Error saat streaming: {e}")
        else:
            self.send_response(result.status_code)
            for key in ["content-type"]:
                if key in result.headers:
                    self.send_header(key, result.headers[key])
            self.end_headers()
            self.wfile.write(result.content)

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
        else:
            self.send_error(404)

def main():
    log("=" * 60)
    log("🚀 Smart Router: Hybrid Groq + OpenRouter")
    log("=" * 60)
    log(f"📍 Server: http://{HOST}:{PORT}")
    log(f" Auto-stop: {IDLE_TIMEOUT}s idle")
    log(f"⏱️ Chunk timeout: {CHUNK_TIMEOUT}s (anti-hang)")
    
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