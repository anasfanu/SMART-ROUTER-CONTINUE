"""Test suite: jalankan smart_router dengan mock upstream (monkeypatch URL).

Mode API key yang diuji:
  - 2 key (Groq + OpenRouter)  -> T0..T12, pool gabungan kedua provider.
  - 1 key saja                 -> T13/T14, provider tanpa key otomatis DILEWATI
    (tanpa prompt/pilihan), router tetap berjalan penuh dari 1 provider.
"""
import os, sys, json, time, threading, subprocess

os.environ["GROQ_API_KEY"] = "gsk-test-key-longer-than-10-chars"
os.environ["OPENROUTER_API_KEY"] = "sk-or-v1-testkeylonger10"
os.environ["PORT"] = "8799"
os.environ["IDLE_TIMEOUT"] = "600"
os.environ["CHUNK_TIMEOUT"] = "3"

import requests as _real_requests
sys.path.insert(0, "/workspace")

mock = subprocess.Popen([sys.executable, "/workspace/test_mock_upstream.py"])
time.sleep(0.7)

import smart_router as sr

sr.GROQ_API_KEY = "gsk-fake"
sr.OPENROUTER_API_KEY = "sk-or-fake"

def fake_get(url, **kw):
    if "127.0.0.1" in url or "localhost" in url:
        return _orig_requests_get(url, **kw)   # request ke mock/router: biarkan asli
    ncalls_provider["n"] += 1
    class R:
        status_code = 200
        @property
        def text(self): return __import__('json').dumps(self.json())
        def raise_for_status(self): pass
        def json(self):
            if "groq" in url:
                return {"data":[{"id":"llama-3.3-70b-versatile"},{"id":"gemma2-9b-it"},{"id":"whisper-large-v3"}]}
            # openrouter: satu model free dgn harga float "0.0" (uji FIX BUG #12)
            return {"data":[{"id":"deepseek/deepseek-chat-v3:free","name":"DeepSeek V3 Free",
                             "pricing":{"prompt":0.0,"completion":0}}]}
    return R()
_orig_requests_get = _real_requests.get
_real_requests.get = fake_get
requests = _real_requests   # nama 'requests' dipakai utk panggil API router/mock

DOWN = False
ncalls_fetch = {"n": 0}
ncalls_provider = {"n": 0}
_orig_fetch = sr.fetch_and_filter_models
def patched_fetch(force=False):
    # deteksi apakah pemanggilan ini benar-benar menembak API provider (bukan baca cache)
    hits_before = ncalls_provider["n"]
    models = _orig_fetch(force=force)
    if ncalls_provider["n"] > hits_before:
        ncalls_fetch["n"] += 1
    # rotasi diuji lewat mutasi base_url langsung pada cached_models (tanpa refetch)
    return models
sr.fetch_and_filter_models = patched_fetch
# percepat read-timeupstream hang agar rotasi cepat (chunk timeout 3s tetap teruji)
sr.UPSTREAM_READ_TIMEOUT = 4

threading.Thread(target=sr.main, daemon=True).start()
time.sleep(1.0)

PASS, FAIL = [], []
def check(name, cond):
    (PASS if cond else FAIL).append(name)
    print(("✅ PASS " if cond else "❌ FAIL ") + name)

B = "http://127.0.0.1:8799"

# T0: OpenRouter model dengan pricing float 0.0 lolos filter (FIX BUG #12) & kuota per-provider (FIX #14)
check("T0 OR :free dgn pricing float masuk pool",
      any(m["provider"]=="openrouter" for m in sr.cached_models))

# siapkan rotasi: model pertama selalu mengarah ke upstream hang (9902), sisanya sehat (9901)
def set_base_urls():
    for i, m in enumerate(sr.cached_models):
        m["base_url"] = "http://127.0.0.1:9902" if i == 0 else "http://127.0.0.1:9901"
set_base_urls()

# T1: health
r = requests.get(f"{B}/health", timeout=5)
check("T1 GET /health 200 JSON", r.status_code==200 and r.json()["status"]=="ok")

# T2: /v1/models tidak membocorkan api_key (FIX BUG #1/#19)
r = requests.get(f"{B}/v1/models", timeout=5)
check("T2 GET /v1/models tanpa bocor api_key",
      r.status_code==200 and "api_key" not in r.text and "fake" not in r.text)

# T3: POST endpoint salah -> 404 JSON (FIX BUG #19)
r = requests.post(f"{B}/wrong/path", json={"messages":[]}, timeout=5)
check("T3 POST path tak dikenal -> 404 JSON", r.status_code==404 and r.json()["error"]["code"]==404)

# T4: invalid JSON -> 400 JSON bukan HTML (FIX BUG #9/#16)
r = requests.post(f"{B}/v1/chat/completions", data="{rusak", headers={"Content-Type":"application/json"}, timeout=5)
check("T4 invalid JSON -> 400 JSON", r.status_code==400 and "error" in r.json())

# T5: non-stream success + payload params diteruskan (FIX BUG #7)
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"hi"}], "temperature":0.42, "max_tokens":123, "stream":False}, timeout=10)
up = json.load(open("/tmp/last_payload.json"))
check("T5 non-stream 200 + content", r.status_code==200 and r.json()["choices"][0]["message"]["content"]=="halo dunia")
check("T5b temperature & max_tokens diteruskan ke upstream",
      up.get("temperature")==0.42 and up.get("max_tokens")==123)

# T6: stream SSE normal
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"hi"}], "stream":True}, timeout=10, stream=True)
lines = [l for l in r.iter_lines(decode_unicode=True) if l]
text = "".join(json.loads(l[6:])["choices"][0]["delta"].get("content","") for l in lines if l.startswith("data: ") and l[6:]!="[DONE]")
check("T6 stream SSE utuh s/d [DONE]", r.status_code==200 and text=="Halo dunia!" and lines[-1]=="data: [DONE]")

# T7: multimodal content list tidak dirusak (FIX BUG #8)
mm = [{"role":"user","content":[{"type":"text","text":"look"},{"type":"image_url","image_url":{"url":"x"}}]}]
r = requests.post(f"{B}/v1/chat/completions", json={"messages":mm,"stream":False}, timeout=10)
up = json.load(open("/tmp/last_payload.json"))
mm_msg = next(m for m in up["messages"] if m["role"] == "user")  # system prompt coding disisipkan di index 0
check("T7 content list multimodal dipertahankan", isinstance(mm_msg["content"], list) and len(mm_msg["content"])==2)

# T7b: temperature default 0.4 disisipkan bila client tidak mengirimnya + system prompt coding
mm = [{"role":"user","content":"buatkan fungsi"}]
r = requests.post(f"{B}/v1/chat/completions", json={"messages":mm,"stream":False}, timeout=10)
up = json.load(open("/tmp/last_payload.json"))
check("T7b temperature default 0.4 terkirim ke upstream", up.get("temperature") == 0.4)
check("T7b system prompt coding disisipkan", up["messages"][0]["role"]=="system" and "expert programming assistant" in up["messages"][0]["content"])

# T7c: temperature dari client TIDAK ditimpa
r = requests.post(f"{B}/v1/chat/completions", json={"messages":mm,"temperature":0.9,"stream":False}, timeout=10)
up = json.load(open("/tmp/last_payload.json"))
check("T7c temperature client (0.9) menang atas default", up.get("temperature") == 0.9)

# T8: concurrency — streaming tidak memblokir /health (FIX BUG #2 ThreadingHTTPServer)
res = {}
def stream_req():
    rr = requests.post(f"{B}/v1/chat/completions", json={"messages":[{"role":"user","content":"x"}],"stream":True}, timeout=15, stream=True)
    for _ in rr.iter_lines(): pass
    res["stream_done"]=True
t = threading.Thread(target=stream_req); t.start()
time.sleep(0.05)
try:
    hr = requests.get(f"{B}/health", timeout=2)
    res["health_during_stream"]=hr.status_code==200
except Exception:
    res["health_during_stream"]=False
t.join()
check("T8 /health tidak terblokir saat stream berjalan", res.get("health_during_stream") and res.get("stream_done"))

# T9: rotasi saat model pertama hang (upstream 9902 diam) -> stream tetap selesai dari model sehat
#     + verifikasi cache: fetch provider tidak dipanggil ulang tiap request (FIX BUG #11)
try: os.remove("/tmp/hit_count.txt")
except Exception: pass
n_fetch_before = ncalls_fetch["n"]
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"x"}], "stream":True}, timeout=90, stream=True)
lines9 = [l for l in r.iter_lines(decode_unicode=True) if l]
text9 = "".join(json.loads(l[6:])["choices"][0]["delta"].get("content","")
                for l in lines9 if l.startswith("data: ") and l[6:] != "[DONE]"
                and "error" not in l)
check("T9 rotasi model hang -> stream selesai & utuh",
      r.status_code==200 and text9=="Halo dunia!" and lines9[-1]=="data: [DONE]")
n_fetch_after = ncalls_fetch["n"]
check("T9b cache dipakai (fetch tidak diulang per request)", n_fetch_after == n_fetch_before)

# T10: semua model gagal (upstream mati total) -> SSE error + [DONE] (FIX BUG #5), non-stream 503 JSON
for m in sr.cached_models:
    m["base_url"] = "http://127.0.0.1:9903"   # port mati -> connection refused
r = requests.post(f"{B}/v1/chat/completions", json={"messages":[{"role":"user","content":"x"}],"stream":True}, timeout=60, stream=True)
body = "\n".join(l for l in r.iter_lines(decode_unicode=True) if l)
check("T10 semua gagal -> SSE error + [DONE]", '"error"' in body and body.strip().endswith("data: [DONE]"))
rr = requests.post(f"{B}/v1/chat/completions", json={"messages":[{"role":"user","content":"x"}]}, timeout=60)
check("T10b non-stream semua gagal -> 503 JSON", rr.status_code==503 and "error" in rr.json())
for m in sr.cached_models:
    m["base_url"] = "http://127.0.0.1:9901"

# T11: hasil [] di-cache, tidak refetch tiap request (FIX BUG #11)
ncalls={"n":0}
def fake_get2(url,**kw):
    ncalls["n"]+=1
    ncalls_provider["n"]+=1
    class R:
        status_code=200
        @property
        def text(self): return '{"data":[]}'
        def raise_for_status(self): pass
        def json(self): return {"data":[]}
    return R()
_real_requests.get = fake_get2
sr.cached_models=None; sr.cache_timestamp=None
sr.CACHE_DURATION = 0   # paksa expire agar fetch terjadi tiap panggilan di test ini
sr.fetch_and_filter_models(); sr.fetch_and_filter_models(); sr.fetch_and_filter_models()
check("T11 hasil [] tetap di-cache (fetch percuma hanya 1x per panggilan, tak ada loop refetch tak berujung)", ncalls["n"]==6)
_real_requests.get = fake_get
sr.CACHE_DURATION = 3600
ncalls_fetch["n"] = 0
patched_fetch(force=True)   # restore pool sehat + hitungan fetch bersih sebelum T12
set_base_urls()

# T12: regresi bug lama — GET /health & /v1/models wajib kirim Content-Length (tidak menggantung)
import http.client as _hc
for path in ("/health", "/v1/models"):
    c = _hc.HTTPConnection("127.0.0.1", 8799, timeout=5)
    c.request("GET", path)
    rp = c.getresponse()
    ok = rp.status == 200 and len(rp.read()) > 0
    check(f"T12 GET {path} respons lengkap tanpa hang", ok)
    c.close()

# T13: MODE 1 API KEY (hanya Groq) — provider tanpa key otomatis DILEWATI, tanpa prompt/pilihan.
#      Kuota adaptif: seluruh jatah pool dialihkan ke provider aktif -> model non-coding ikut terpakai.
sr.GROQ_API_KEY = "gsk-fake"
sr.OPENROUTER_API_KEY = None
ncalls_provider["n"] = 0
sr.fetch_and_filter_models(force=True)
providers_in_pool = {m["provider"] for m in sr.cached_models}
groq_fetches = ncalls_provider["n"]
check("T13a 1-key(Groq): hanya fetch Groq yang ditembak (OpenRouter dilewati)",
      groq_fetches == 1)
check("T13b 1-key(Groq): pool HANYA berisi model groq", providers_in_pool == {"groq"})
check("T13c 1-key(Groq): kuota adaptif — model non-coding (gemma2) ikut masuk pool",
      any(m["id"] == "gemma2-9b-it" for m in sr.cached_models))
set_base_urls()
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"x"}], "stream":False}, timeout=60)
check("T13d 1-key(Groq): chat tetap berfungsi end-to-end", r.status_code==200 and r.json()["choices"][0]["message"]["content"]=="halo dunia")

# T14: MODE 1 API KEY (hanya OpenRouter) — mirror case, validasi get_api_key_for_provider sisi OR
sr.GROQ_API_KEY = None
sr.OPENROUTER_API_KEY = "sk-or-fake"
sr.fetch_and_filter_models(force=True)
providers_in_pool = {m["provider"] for m in sr.cached_models}
check("T14a 1-key(OR): pool HANYA berisi model openrouter", providers_in_pool == {"openrouter"})
for m in sr.cached_models:
    m["base_url"] = "http://127.0.0.1:9901"   # semua sehat -> stream langsung selesai dari provider tunggal
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"x"}], "stream":True}, timeout=90, stream=True)
lines14 = [l for l in r.iter_lines(decode_unicode=True) if l]
text14 = "".join(json.loads(l[6:])["choices"][0]["delta"].get("content","")
                 for l in lines14 if l.startswith("data: ") and l[6:] != "[DONE]" and "error" not in l)
check("T14b 1-key(OR): stream berfungsi penuh dari provider tunggal",
      text14 == "Halo dunia!" and lines14[-1] == "data: [DONE]")

# T15: rotasi dgn 1 key — butuh minimal 2 model di pool. Mock hanya punya 1 model OR gratis,
#      jadi tambahkan duplikat entri sehat untuk menguji jalur rotasi pada mode single-provider.
if len(sr.cached_models) < 2:
    sr.cached_models.append(dict(sr.cached_models[0]))
first = dict(sr.cached_models[0]); first["base_url"] = "http://127.0.0.1:9902"
sr.cached_models[0] = first
for m in sr.cached_models[1:]:
    m["base_url"] = "http://127.0.0.1:9901"
r = requests.post(f"{B}/v1/chat/completions", json={
    "messages":[{"role":"user","content":"x"}], "stream":True}, timeout=90, stream=True)
lines15 = [l for l in r.iter_lines(decode_unicode=True) if l]
text15 = "".join(json.loads(l[6:])["choices"][0]["delta"].get("content","")
                 for l in lines15 if l.startswith("data: ") and l[6:] != "[DONE]" and "error" not in l)
check("T15 1-key(OR): rotasi saat model pertama hang tetap menyelesaikan stream",
      text15 == "Halo dunia!" and lines15[-1] == "data: [DONE]")

# restore mode 2 key agar hasil akhir konsisten dgn dokumentasi
sr.GROQ_API_KEY = "gsk-fake"
sr.OPENROUTER_API_KEY = "sk-or-fake"
sr.fetch_and_filter_models(force=True)
set_base_urls()

print("\n===== HASIL =====")
print(f"Lulus: {len(PASS)} | Gagal: {len(FAIL)}")
if FAIL: print("GAGAL:", FAIL)
mock.terminate()
sys.exit(1 if FAIL else 0)
