# 🧠 Smart Router untuk Continue

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.md)

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

### 2. Jalankan — Semua Logic Ada di `smart_router.py`

Satu entry point untuk semua OS. `start_router.sh` / `start_router.bat` / `stop_router.sh` / `stop_router.bat` kini hanya **wrapper tipis** yang meneruskan ke `smart_router.py`, sehingga tidak ada logika yang duplikat:

| Perintah | Fungsi |
|---|---|
| `python smart_router.py` | ▶️ START (bisa dari terminal, double-click wrapper, atau task VS Code) |
| `./start_router.sh` / `start_router.bat` | ▶️ START — sama saja memanggil `python smart_router.py` |
| `python smart_router.py --stop` | ⏹️ STOP lintas-OS (TERM dulu, KILL kalau membandel) |
| `./stop_router.sh` / `stop_router.bat` | ⏹️ STOP — sama saja memanggil `python smart_router.py --stop` |

Saat START, `smart_router.py` otomatis: **validasi `.env` → cek dependency → kill proses router/test/mock lama → spawn instance di background (PID & log dikelola Python) → health check**. Karena instance background memasang *signal handler* (`SIGINT/SIGTERM/SIGHUP`, plus `SIGBREAK` di Windows), **menutup terminal/jendela apps langsung menghentikan router dengan rapi** dan membersihkan file PID — tanpa perlu skrip stop terpisah. Server juga auto-stop sendiri setelah idle (`IDLE_TIMEOUT`, default 300 detik). Log tersimpan di `smart_router.log`.

### 3. Sambungkan ke Continue (`config.yaml`)

Edit `~/.continue/config.yaml` (bagian `models:`) menjadi seperti ini:

```yaml
name: Continue Config
version: 1.0.0
models:
  - name: Smart Router (auto-best coding model)
    provider: openai
    model: smart-router          # nama bebas, router yang memutuskan model asli
    apiBase: http://127.0.0.1:8765/v1
    apiKey: not-needed           # key asli sudah ada di .env router
    roles:
      - chat
      - edit
```

Selesai! Pilih **"Smart Router (auto-best coding model)"** di dropdown model Continue — chat, edit, dan autocomplete langsung pakai pool model coding gratis terbaik.

> 💡 **VS Code / Cursor**: `.vscode/tasks.json` menyediakan task **"Start Smart Router"** dengan `runOn: folderOpen` — router nyala otomatis saat workspace dibuka (memanggil script yang benar per OS). Jika auto-task tidak jalan: `Ctrl+Shift+P` → *"Tasks: Manage Automatic Tasks"* → **Allow Automatic Tasks**.

## ✨ Fitur

- 🔄 **Dual Provider** — Groq + OpenRouter digabung, jalan dengan 1 atau 2 key (provider tanpa key otomatis dilewati).
- 🎯 **Smart Selection** — filter model non-coding, skor otomatis, prioritas kecepatan Groq.
- 🔁 **Auto-Retry** — ganti model otomatis saat timeout/error, lanjutkan stream di tengah jawaban.
- 🛡️ **Anti Hang** — per-chunk timeout; error rapi via SSE bila semua model habis.
- 💤 **Auto-Sleep** — mati sendiri setelah 5 menit idle, hemat resource.
- 🧩 **Satu Entry Point Lintas-OS** — start/stop cukup `smart_router.py` (+ flag `--stop`); `.sh`/`.bat` hanya wrapper. Tutup jendela apps = router berhenti rapi (signal handler + PID cleanup).
- 🔐 **Aman** — API key hanya dibaca dari `.env` (tidak pernah diekspos/ditulis ke tempat lain).

## 🧪 Test Lokal (Tanpa API Key Asli)

```bash
python test_router.py
```

Menggunakan mock upstream — aman di-kill kapan saja lewat `python smart_router.py --stop` (atau `stop_router.sh` / `stop_router.bat`).

## ❓ Troubleshooting

| Masalah | Solusi |
|---|---|
| "File .env tidak ditemukan" | Jalankan `cp .env.example .env` lalu isi key |
| Semua model gagal | Cek key valid & kuota provider masih ada |
| Port sibuk | Ubah `PORT` di `.env`, jalankan start lagi (proses lama otomatis di-kill) |
| Mau berhenti total | `python smart_router.py --stop` atau double-click `stop_router.sh` / `stop_router.bat` |
| Router sisa setelah crash | Jalankan start lagi — proses lama otomatis dibersihkan via PID file |

## 📄 License

Distribusikan di bawah lisensi **[MIT](LICENSE.md)** — klik badge/link untuk melihat isinya.
