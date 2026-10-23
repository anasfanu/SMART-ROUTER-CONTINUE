# 🧠 Smart Router untuk Continue

Proxy AI lokal (OpenAI-compatible) yang menggabungkan **Groq + OpenRouter** dan memilih model coding gratis terbaik secara otomatis. Dirancang untuk plugin [Continue.dev](https://continue.dev/) — cukup arahkan endpoint ke `http://127.0.0.1:8765/v1`.

## ⚡ Cara Pakai (3 Langkah)

### 1. Isi API Key di `.env` (satu-satunya cara)

```bash
cp .env.example .env
```

Lalu edit `.env` dan isi minimal **satu** key (Groq dan/atau OpenRouter):

```env
GROQ_API_KEY=gsk-xxxxxxxx
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
```

> Dapatkan key gratis di: [Groq](https://console.groq.com/keys) · [OpenRouter](https://openrouter.ai/settings/keys)
> ❗ Tidak ada lagi input API key lewat terminal/CLI — semuanya dari file `.env`.

### 2. Klik untuk Menjalankan

| OS | Start (double-click) | Stop / Kill (double-click) |
|---|---|---|
| 🐧 Linux | `./start_router.sh` | `./stop_router.sh` |
| 🪟 Windows | `start_router.bat` | `stop_router.bat` |

Skrip start otomatis: membuat venv + install dependency, **kill proses router/test/mock lama** lalu start baru, dan menjalankan server di background. Skrip stop **kill semua proses** router, test, dan mock sekaligus. Server juga auto-stop sendiri setelah 5 menit tidak dipakai. Log server Linux tersimpan di `smart_router.log` di folder project.

### 3. Sambungkan ke Continue (`config.yaml`)

```yaml
models:
  - name: Smart Router
    provider: openai
    model: smart-router
    apiBase: http://127.0.0.1:8765/v1
    apiKey: dummy
```

Selesai! Chat & autocomplete langsung pakai pool model coding gratis terbaik.

## ✨ Fitur

- 🔄 **Dual Provider** — Groq + OpenRouter digabung, jalan dengan 1 atau 2 key (provider tanpa key otomatis dilewati).
- 🎯 **Smart Selection** — filter model non-coding, skor otomatis, prioritas kecepatan Groq.
- 🔁 **Auto-Retry** — ganti model otomatis saat timeout/error, lanjutkan stream di tengah jawaban.
- 🛡️ **Anti Hang** — per-chunk timeout; error rapi via SSE bila semua model habis.
- 💤 **Auto-Sleep** — mati sendiri setelah 5 menit idle, hemat resource.
- 🔐 **Aman** — API key hanya dibaca dari `.env` (tidak pernah diekspos/ditulis ke tempat lain).

## 🧪 Test Lokal (Tanpa API Key Asli)

```bash
python test_router.py
```

Menggunakan mock upstream — aman di-kill kapan saja lewat `stop_router.sh` / `stop_router.bat`.

## ❓ Troubleshooting

| Masalah | Solusi |
|---|---|
| "File .env tidak ditemukan" | Jalankan `cp .env.example .env` lalu isi key |
| Semua model gagal | Cek key valid & kuota provider masih ada |
| Port sibuk | Ubah `PORT` di `.env`, klik skrip start lagi (proses lama otomatis di-kill) |
| Mau berhenti total | Double-click `stop_router.sh` / `stop_router.bat` |

## 📄 License

MIT
