#!/usr/bin/env python3
"""
Smart Router untuk Continue - Hybrid Dual Provider (Groq + OpenRouter)
Fix: Per-chunk timeout, proper ReadTimeout handling, client disconnect handling.

Revisi (hasil inspeksi bug):
- ThreadingHTTPServer (anti blokir), idle shutdown aman saat stream aktif
- stream_with_chunk_timeout: put() non-blocking + resp.close() (anti thread/socket leak)
- Payload client diteruskan utuh (temperature, max_tokens, tools, dst.)
- SSE error event saat semua model gagal; priming sebelum kirim header 200
- API key HANYA dibaca dari file .env (tanpa prompt CLI)
- Filter harga numerik, cache cek `is not None`, except spesifik
- Routing eksplisit: POST /v1/chat/completions | GET /health | GET /v1/models
"""

import json
import time
import threading
import requests
import sys
import os
import re
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timedelta
from pathlib import Path
from queue import Queue, Empty, Full

# ============ 1. LOAD API KEY (HANYA dari file .env — tanpa prompt CLI) ============
def load_env_file(path=".env"):
    """Parser .env sederhana (tanpa dependensi wajib python-dotenv)."""
    candidates = []
    try:
        candidates.append(Path.cwd() / path)          # 1) cwd (konsisten dgn perilaku dotenv standar)
    except OSError:
        pass
    candidates.append(Path(__file__).resolve().parent / path)  # 2) di samping skrip (klik dari file manager)
    p = next((c for c in candidates if c.exists()), None)
    if p is None:
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip("'\"")
        if k and k not in os.environ:
            os.environ[k] = v


def get_api_key(provider):
    env_var = f"{provider}_API_KEY"
    api_key = os.getenv(env_var)
    if api_key and not api_key.startswith("your-") and len(api_key) > 10:
        return api_key
    return None

load_env_file()
OPENROUTER_API_KEY = get_api_key("OPENROUTER")
GROQ_API_KEY = get_api_key("GROQ")

# ====== FUNGSI: JALAN DENGAN 1 ATAU 2 API KEY (auto-filter, tanpa perlu pilih apa pun) ======
# Provider yang tidak punya key otomatis DILEWATI (di-filter) — bukan error, bukan prompt.
# 1 key  -> router tetap jalan penuh dengan pool dari provider tsb.
# 2 key  -> keduanya digabung seperti biasa.
ACTIVE_PROVIDERS = [p for p, k in (("groq", GROQ_API_KEY), ("openrouter", OPENROUTER_API_KEY)) if k]

print("\n" + "=" * 60)
print(" STATUS API KEY (mode single-key didukung):")
print(f"   OpenRouter: {'✅ Ter-load' if OPENROUTER_API_KEY else '⏭️  Tidak ada (dilewati otomatis)'}")
print(f"   Groq:       {'✅ Ter-load' if GROQ_API_KEY else '⏭️  Tidak ada (dilewati otomatis)'}")
print(f"   Provider aktif: {', '.join(p.upper() for p in ACTIVE_PROVIDERS) or '-'}")
if len(ACTIVE_PROVIDERS) == 1:
    print(f"   ℹ️  Hanya 1 key terdeteksi → router berjalan penuh dengan pool {ACTIVE_PROVIDERS[0].upper()} saja.")
print("=" * 60 + "\n")

if not ACTIVE_PROVIDERS:
    print("❌ ERROR: Minimal satu API Key harus diisi (Groq dan/atau OpenRouter)!")
    sys.exit(1)

# ============ 2. KONFIGURASI ============
PORT = int(os.getenv("PORT", "8765"))
HOST = os.getenv("HOST", "127.0.0.1")
CACHE_DURATION = int(os.getenv("CACHE_DURATION", "3600"))
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "300"))
UPSTREAM_CONNECT_TIMEOUT = 5    # connect timeout (detik)
UPSTREAM_READ_TIMEOUT = 45      # read timeout per-read (harus > CHUNK_TIMEOUT)
CHUNK_TIMEOUT = int(os.getenv("CHUNK_TIMEOUT", "20"))  # Timeout per chunk (detik) - ANTI HANG
POLL_INTERVAL = 0.5             # interval cek stop_event pada queue

# ============ 3. STATE GLOBAL ============
last_request_time = time.time()
cached_models = None
cache_timestamp = None
shutdown_timer = None
state_lock = threading.Lock()   # lindungi timer & state antar-thread
active_streams = 0              # jumlah stream berjalan (blokir shutdown paksa)

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

def fetch_and_filter_models(force=False):
    global cached_models, cache_timestamp

    # FIX BUG #11: gunakan `is not None` agar hasil [] tidak memicu refetch tiap request
    if not force and cached_models is not None and cache_timestamp is not None:
        if datetime.now() - cache_timestamp < timedelta(seconds=CACHE_DURATION):
            return cached_models

    # bangun pada SALINAN — jangan pernah mutasi list cache yang mungkin dibaca thread lain
    pool = [] if cached_models is None else copy.deepcopy(cached_models)
    unified_models = []
    groq_ok, or_ok = False, False

    if GROQ_API_KEY:
        log("📡 Mengambil Model dari Groq...")
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
                        "base_url": "https://api.groq.com/openai/v1"
                    })

            groq_candidates.sort(key=lambda x: x["score"], reverse=True)
            top_groq = groq_candidates[:5]
            unified_models.extend(top_groq)
            groq_ok = True
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
            or_candidates = []
            for m in resp.json().get("data", []):
                pricing = m.get("pricing", {})
                # FIX BUG #12: perbandingan harga numerik, bukan string persis "0"
                try:
                    prompt_price = float(pricing.get("prompt", 1))
                except (TypeError, ValueError):
                    prompt_price = 1
                if prompt_price == 0 and ":free" in m.get("id", ""):
                    if is_coding_model(m, "openrouter"):
                        or_candidates.append({
                            "id": m["id"],
                            "title": f"[OR] {m.get('name', m['id'])}",
                            "score": score_model_for_coding(m, "openrouter"),
                            "provider": "openrouter",
                            "base_url": "https://openrouter.ai/api/v1"
                        })
                        or_count += 1
            or_candidates.sort(key=lambda x: x["score"], reverse=True)
            unified_models.extend(or_candidates[:10])
            or_ok = True
            log(f"   ✅ {or_count} model OpenRouter gratis lolos filter")
        except Exception as e:
            log(f"   ❌ Gagal ambil model OpenRouter: {e}")

    # bila TIDAK ada provider yang berhasil di-fetch: pertahankan pool lama (jangan hancurkan cache)
    if not (groq_ok or or_ok):
        cached_models = pool[:15]
        cache_timestamp = datetime.now()
        log("⚠️ Semua fetch provider gagal, memakai pool lama/cache kosong")
        return cached_models

    # FIX BUG #14: kuota per-provider agar OpenRouter tidak selalu kalah oleh Groq.
    # FUNGSI BARU (single-key mode): kuota bersifat ADAPTIF — provider yang tidak aktif
    # (tidak punya API key) otomatis di-filter, dan jatahnya dialihkan ke provider aktif,
    # sehingga 1 key maupun 2 key tetap menghasilkan pool maksimal (TARGET_POOL_SIZE).
    TARGET_POOL_SIZE = 15
    fetched_providers = {p for p, ok in (("groq", groq_ok), ("openrouter", or_ok)) if ok}
    quota_each = max(1, TARGET_POOL_SIZE // len(fetched_providers)) if fetched_providers else TARGET_POOL_SIZE
    groq_pool = [m for m in unified_models if m["provider"] == "groq"][:quota_each]
    or_pool = [m for m in unified_models if m["provider"] == "openrouter"][:quota_each]
    new_entries = groq_pool + or_pool

    # rebuild salinan pool: ganti entri provider yang sukses di-fetch, sisakan yang gagal
    pool = [m for m in pool if m["provider"] not in fetched_providers]
    pool.extend(new_entries)

    # FUNGSI BARU (single-key mode): provider yang TIDAK punya API key dibuang total dari pool,
    # termasuk sisa entri cache lama — router 1 key hanya melayani provider yang ada key-nya.
    if OPENROUTER_API_KEY is None:
        pool = [m for m in pool if m["provider"] != "openrouter"]
    if GROQ_API_KEY is None:
        pool = [m for m in pool if m["provider"] != "groq"]

    pool.sort(key=lambda x: x["score"], reverse=True)
    cached_models = pool[:TARGET_POOL_SIZE]
    cache_timestamp = datetime.now()

    if len(ACTIVE_PROVIDERS) == 1 and fetched_providers == set(ACTIVE_PROVIDERS):
        log(f"ℹ️ Mode 1 API key: pool dibangun dari {ACTIVE_PROVIDERS[0].upper()} saja "
            f"(provider tanpa key dilewati otomatis).")

    log("\n" + "=" * 60)
    log(f"🏆 Top {len(cached_models)} Model Pool:")
    log("=" * 60)
    for i, m in enumerate(cached_models, 1):
        tag = "🚀" if m["provider"] == "groq" else "🌐"
        log(f"  {i:2}. {tag} [{m['provider'].upper():10}] {m['id']} (Score: {m['score']})")
    log("=" * 60 + "\n")

    return cached_models

# Default temperature untuk coding: deterministik & konsisten.
# Hanya dipakai bila client TIDAK mengirim temperature sendiri (client tetap menang).
DEFAULT_CODING_TEMPERATURE = float(os.getenv("CODING_TEMPERATURE", "0.4"))

# System prompt coding: lebih spesifik → jawaban ringkas, langsung ke kode.
# Catatan: di-merge dengan system message dari Continue (jika ada), tidak menimpanya.
CODING_SYSTEM_PROMPT = (
    "You are an expert programming assistant. "
    "Prefer complete, working code over prose. "
    "When you write code, output it in fenced code blocks with the correct language tag. "
    "Keep explanations short and only when they add value. "
    "If requirements are ambiguous, state your assumption in one line, then implement."
)

def optimize_prompt_messages(messages):
    optimized = []
    for msg in messages:
        content = msg.get("content", "")
        # FIX BUG #8: content list/multimodal (image parts) dilewati apa adanya
        if isinstance(content, str):
            content = re.sub(r'\n{3,}', '\n\n', content)
            lines = [line.strip() for line in content.split('\n')]
            content = '\n'.join(lines)
        new_msg = {"role": msg.get("role", "user"), "content": content}
        # pertahankan field percakapan standar
        for extra in ("name", "tool_calls", "tool_call_id"):
            if extra in msg:
                new_msg[extra] = msg[extra]
        optimized.append(new_msg)
    return optimized

def get_api_key_for_provider(provider):
    """FIX BUG #1: key TIDAK disimpan di objek model, diambil saat call via fungsi ini."""
    return GROQ_API_KEY if provider == "groq" else OPENROUTER_API_KEY

def call_llm(model_info, payload, stream=False):
    """Panggil API - raise exception jika timeout, jangan return None"""
    api_key = get_api_key_for_provider(model_info["provider"])
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if model_info['provider'] == 'openrouter':
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "Continue Smart Router"

    # FIX BUG #7: payload client (temperature, max_tokens, tools, dst.) diteruskan utuh
    payload = {**payload, "model": model_info['id'], "stream": bool(stream)}

    # FIX BUG #15: hierarki timeout konsisten (read > chunk timeout)
    resp = requests.post(
        f"{model_info['base_url']}/chat/completions",
        headers=headers, json=payload, stream=stream,
        timeout=(UPSTREAM_CONNECT_TIMEOUT, UPSTREAM_READ_TIMEOUT)
    )
    return resp

def stream_with_chunk_timeout(resp, timeout_seconds):
    """
    Wrapper untuk iter_lines() dengan timeout per chunk.
    FIX BUG #3: Anti-hang + anti kebocoran thread/socket saat consumer berhenti awal.
    """
    chunk_queue = Queue(maxsize=100)
    stop_event = threading.Event()

    def enqueue_safe(item):
        # put() dengan timeout + cek stop_event -> tidak pernah macet permanen
        while not stop_event.is_set():
            try:
                chunk_queue.put(item, timeout=POLL_INTERVAL)
                return
            except Full:
                continue

    def reader_thread():
        try:
            for line in resp.iter_lines():
                if stop_event.is_set():
                    break
                if line:
                    enqueue_safe(line)
        except Exception as e:
            enqueue_safe(("ERROR", str(e)))
        finally:
            enqueue_safe(None)  # Signal selesai

    thread = threading.Thread(target=reader_thread, daemon=True)
    thread.start()

    try:
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
    finally:
        # selalu bersihkan: set stop, drain queue penuh, close response upstream
        stop_event.set()
        try:
            while True:
                chunk_queue.get_nowait()
        except Empty:
            pass
        thread.join(timeout=2)
        try:
            resp.close()
        except Exception:
            pass

def smart_route(payload, stream=False):
    global last_request_time
    last_request_time = time.time()

    models = fetch_and_filter_models()
    if not models:
        log("⚠️ Tidak ada model tersedia!")
        return None

    optimized_messages = optimize_prompt_messages(payload.get("messages", []))

    # Sisipkan/merge system prompt coding (hanya bila belum ada instruksi serupa).
    # Bila client sudah mengirim system message, pesan kita di-append agar tidak menimpa.
    if optimized_messages and optimized_messages[0].get("role") == "system" \
            and isinstance(optimized_messages[0].get("content"), str):
        if CODING_SYSTEM_PROMPT not in optimized_messages[0]["content"]:
            optimized_messages[0]["content"] += "\n\n" + CODING_SYSTEM_PROMPT
    else:
        optimized_messages.insert(0, {"role": "system", "content": CODING_SYSTEM_PROMPT})

    # payload dasar: pertahankan parameter client lainnya (max_tokens, tools, dll.)
    base_payload = {k: v for k, v in payload.items() if k not in ("messages", "stream")}
    # Temperature default khusus coding: hanya diisi bila client tidak mengirimnya.
    base_payload.setdefault("temperature", DEFAULT_CODING_TEMPERATURE)

    if not stream:
        for model in models:
            try:
                resp = call_llm(model, {**base_payload, "messages": optimized_messages}, False)
                if resp.status_code == 200:
                    log(f"✅ Berhasil (Non-stream): {model['id']}")
                    return resp
                else:
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
            deltas_sent = 0

            while model_idx < len(models):
                model = models[model_idx]
                log(f"🎯 Streaming dengan model #{model_idx+1}: {model['id']}")

                current_messages = list(optimized_messages)
                if accumulated_response:
                    # FIX BUG #10: lanjutkan hanya pada batas paragraf agar tidak menyela kata
                    cut = accumulated_response.rfind("\n\n")
                    keep = accumulated_response[:cut] if cut >= len(accumulated_response) // 2 else accumulated_response
                    log(f"💡 Melanjutkan dari {len(keep)} karakter...")
                    current_messages.append({"role": "assistant", "content": keep})
                    current_messages.append({"role": "user", "content": "[SYSTEM: Lanjutkan dari titik terakhir. JANGAN ulangi bagian yang sudah ditulis.]"})
                    accumulated_response = keep
                    deltas_sent = 0

                try:
                    resp = call_llm(model, {**base_payload, "messages": current_messages}, True)

                    if resp.status_code != 200:
                        log(f"⚠️ {model['id']} gagal (Status {resp.status_code}), rotasi...")
                        model_idx += 1
                        continue

                    log(f"✅ Berhasil stream: {model['id']}")
                    stream_completed = False

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
                                    deltas_sent += 1
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
                    log(f"⏱️ {model['id']} timeout, rotasi...")
                    model_idx += 1
                except Exception as e:
                    log(f"❌ {model['id']} error: {e}. Rotasi...")
                    model_idx += 1

            # FIX BUG #5: beri tahu client lewat SSE error bila semua model habis
            if deltas_sent == 0:
                err = {"error": {"message": "All models failed or timed out", "type": "router_error"}}
                yield f"data: {json.dumps(err)}\n\n"
            yield "data: [DONE]\n\n"

        return stream_generator()

def reset_idle_timer():
    global shutdown_timer
    with state_lock:
        if shutdown_timer:
            shutdown_timer.cancel()
        shutdown_timer = threading.Timer(IDLE_TIMEOUT, shutdown_server)
        shutdown_timer.daemon = True
        shutdown_timer.start()

def shutdown_server():
    # FIX BUG #4: jangan bunuh proses saat masih ada stream aktif
    if active_streams > 0:
        log("⏳ Shutdown ditunda: masih ada stream aktif")
        return
    if time.time() - last_request_time >= IDLE_TIMEOUT:
        log(f"💤 Idle {IDLE_TIMEOUT}s, shutdown server...")
        os._exit(0)

class SmartHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def send_json_error(self, code, message):
        """Seragamkan error sebagai JSON OpenAI-compatible (bukan HTML)."""
        body = json.dumps({"error": {"message": message, "type": "router_error", "code": code}}).encode()
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        global last_request_time, active_streams
        last_request_time = time.time()
        reset_idle_timer()

        # FIX BUG #19: routing eksplisit
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_json_error(404, f"Unknown endpoint: {self.path}")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:  # FIX BUG #16: bukan bare `except:`
            self.send_json_error(400, "Invalid JSON")
            return

        stream = bool(payload.get("stream", False))
        result = smart_route(payload, stream)

        if result is None:
            self.send_json_error(503, "All models failed")
            return

        if stream:
            # FIX BUG #6: prime generator sampai chunk pertama keluar
            first_chunk = None
            try:
                first_chunk = next(iter(result))
            except StopIteration:
                first_chunk = None

            self.send_response(200)
            self.send_header("Content-type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()

            with state_lock:
                active_streams += 1
            try:
                if first_chunk:
                    self.wfile.write(first_chunk.encode('utf-8') if isinstance(first_chunk, str) else first_chunk)
                    self.wfile.flush()
                for chunk in result:
                    if chunk:
                        self.wfile.write(chunk.encode('utf-8') if isinstance(chunk, str) else chunk)
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                log("⚠️ Client disconnect (user stop)")
            except Exception as e:
                log(f"❌ Error saat streaming: {e}")
            finally:
                with state_lock:
                    active_streams -= 1
                try:
                    result.close()
                except Exception:
                    pass
                # FIX BUG #4: timer di-reset setelah request selesai
                last_request_time = time.time()
                reset_idle_timer()
        else:
            body_bytes = result.content
            self.send_response(result.status_code)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

    def do_GET(self):
        global last_request_time
        last_request_time = time.time()
        reset_idle_timer()

        if self.path == "/health":
            models = fetch_and_filter_models()
            body = json.dumps({
                "status": "ok",
                "models_count": len(models),
                "groq_count": len([m for m in models if m["provider"] == "groq"]),
                "openrouter_count": len([m for m in models if m["provider"] == "openrouter"])
            }).encode()
            # FIX: selalu kirim Content-Length (protocol_version HTTP/1.1) agar client tidak menunggu
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/v1/models":
            # FIX BUG #19: sediakan daftar model (tanpa api_key — lihat BUG #1)
            models = fetch_and_filter_models()
            data = [{
                "id": m["id"],
                "object": "model",
                "owned_by": m["provider"],
                "name": m["title"],
            } for m in models]
            body = json.dumps({"object": "list", "data": data}).encode()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_json_error(404, f"Unknown endpoint: {self.path}")

def main():
    log("=" * 60)
    log("🚀 Smart Router: Hybrid Groq + OpenRouter")
    log("=" * 60)
    log(f"📍 Server: http://{HOST}:{PORT}")
    log(f"💤 Auto-stop: {IDLE_TIMEOUT}s idle")
    log(f"⏱️ Chunk timeout: {CHUNK_TIMEOUT}s (anti-hang)")

    fetch_and_filter_models()

    # FIX BUG #2: ThreadingHTTPServer agar streaming panjang tidak memblokir request lain
    server = ThreadingHTTPServer((HOST, PORT), SmartHandler)
    reset_idle_timer()
    try:
        log("✅ Server siap! Continue bisa mulai digunakan.")
        server.serve_forever()
    except KeyboardInterrupt:
        log("\n👋 Server dimatikan manual")
        server.server_close()

if __name__ == "__main__":
    main()
