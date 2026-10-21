# 🧠 Smart Router untuk Plugin Continue

<p align="center">
  <strong>🚀 Smart AI Model Routing untuk Plugin Continue.dev</strong>
  <br>
  Menggabungkan kecepatan Groq dan fleksibilitas OpenRouter untuk pengalaman coding AI yang lebih cerdas.
</p>

<p align="center">
  <a href="https://continue.dev/">
    <img src="https://img.shields.io/badge/Compatible%20with-Continue.dev-blue?style=for-the-badge" alt="Continue.dev">
  </a>
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Providers-Groq%20%2B%20OpenRouter-8A2BE2?style=for-the-badge" alt="AI Providers">
  <img src="https://img.shields.io/badge/License-MIT-2EA44F?style=for-the-badge" alt="MIT License">
</p>

---

## 🌟 Tentang Project

**Smart Router for Continue** adalah sistem routing AI otomatis yang dirancang untuk [Continue.dev](https://continue.dev/). Project ini membantu memilih model AI coding yang tersedia secara gratis dari **Groq** dan **OpenRouter** berdasarkan ketersediaan, karakteristik model, dan sistem penilaian yang digunakan.

Tujuannya sederhana: menghadirkan pengalaman coding berbantuan AI yang **gratis, cepat, ringan, praktis, dan minim pengulangan respons**.

### 💡 Mengapa Smart Router?

- ⚡ **Lebih Cepat** — Memprioritaskan Groq untuk memanfaatkan respons model yang cepat.
- 🧠 **Lebih Cerdas** — Menyeleksi dan mengurutkan model berdasarkan kriteria routing.
- 🔄 **Lebih Praktis** — Mengintegrasikan dua provider AI dalam satu sistem.
- 🪶 **Lebih Ringan** — Dirancang dengan konsumsi resource yang minimal.
- 🔐 **Lebih Aman** — Mendukung konfigurasi API key lokal tanpa menyimpannya di repository.

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|---|---|
| 🚀 **Dual Provider** | Mengintegrasikan Groq dan OpenRouter untuk pilihan model yang lebih luas. |
| ⚡ **Prioritas Kecepatan** | Memberikan bonus skor kepada model Groq sesuai mekanisme routing. |
| 🔄 **Stateful Continuation** | Dirancang untuk melanjutkan proses setelah kegagalan atau batas token jika mekanisme kelanjutan tersedia dan berhasil. |
| 🧹 **Prompt Optimization** | Mengompresi dan merapikan prompt untuk membantu menghemat token tanpa mengubah inti instruksi. |
| 🎯 **Smart Model Filter** | Menyaring model yang tidak sesuai untuk coding, seperti model embedding atau model khusus gambar. |
| 📊 **Dynamic Model Scoring** | Mengurutkan kandidat model berdasarkan skor dan kriteria yang ditetapkan. |
| 💤 **Auto-Sleep** | Server dirancang berhenti otomatis setelah 5 menit tidak digunakan. |
| 🪶 **Lightweight** | Ditujukan untuk penggunaan resource yang rendah. |


> **Catatan:** Ketersediaan model gratis, batas token, kecepatan, dan kuota API bergantung pada kebijakan masing-masing provider. Fitur lanjutan juga bergantung pada implementasi dan konfigurasi project.

---

## 🛠️ Teknologi

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Groq-F55036?style=flat-square" alt="Groq">
  <img src="https://img.shields.io/badge/OpenRouter-6467F2?style=flat-square" alt="OpenRouter">
  <img src="https://img.shields.io/badge/Continue.dev-1A1A1A?style=flat-square" alt="Continue.dev">
</p>

- **Bahasa:** Python
- **AI Provider:** Groq dan OpenRouter
- **IDE Integration:** Continue.dev
- **Konfigurasi:** CLI dan `.env`

---

## 🚀 Quick Start

### 1. 📥 Clone Repository

Buka terminal, lalu jalankan:

```bash
git clone https://github.com/anasfanu/smart-router-continue.git
cd smart-router-continue
```

### 2. 📦 Instal Dependencies

Pastikan Python sudah terinstal. Kemudian jalankan:

```bash
python -m pip install -r requirements.txt
```

Jika perintah `python` tidak tersedia, coba gunakan `python3` atau `py` sesuai sistem operasi.

### 3. 🔑 Konfigurasi API Key

Smart Router mendukung dua provider. Kamu dapat menggunakan salah satu atau keduanya.

#### ⭐ Cara A — Konfigurasi melalui CLI (Direkomendasikan)

Jalankan program utama:

```bash
python smart_router.py
```

Jika belum dikonfigurasi, program akan memandu proses memasukkan API key melalui terminal sesuai implementasi yang tersedia.

**Keuntungan:**
- Lebih praktis untuk pengguna baru.
- Tidak perlu mengedit konfigurasi secara manual.
- Dapat menyimpan key secara lokal jika mekanisme penyimpanan tersebut diaktifkan oleh program.

#### 💻 Cara B — Menggunakan file `.env`

Salin file konfigurasi contoh:

```bash
cp .env.example .env
```

Buka file `.env`, kemudian masukkan API key milikmu:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx
```

Dapatkan API key melalui halaman resmi:

- 🔗 [OpenRouter API Keys](https://openrouter.ai/settings/keys)
- 🔗 [Groq API Keys](https://console.groq.com/keys)

> 🔒 **Keamanan:** Jangan pernah membagikan API key atau mengunggah file `.env` ke GitHub. Pastikan file `.env` tercantum di `.gitignore`. Gunakan hanya key milikmu sendiri dan periksa konfigurasi sebelum melakukan commit.

---

## 🎯 Menjalankan Smart Router dengan Sekali Klik

Agar tidak perlu mengetik perintah setiap kali ingin mulai coding, kamu dapat membuat file launcher sesuai sistem operasi.

### 🪟 Windows — Launcher `.bat`

**Langkah 1.** Buka folder `smart-router-continue`.

**Langkah 2.** Buat file baru bernama:

```text
Start Smart Router.bat
```

Pastikan nama akhirnya benar-benar `.bat`, bukan `.bat.txt`.

**Langkah 3.** Buka file tersebut dengan Notepad, lalu masukkan kode berikut:

```bat
@echo off
title Smart Router for Continue

echo.
echo ========================================
echo       SMART ROUTER FOR CONTINUE
echo ========================================
echo.

:: Pindah ke folder tempat launcher berada
cd /d "%~dp0"

:: Jalankan Smart Router
python smart_router.py

:: Tahan jendela agar error dapat dibaca
echo.
echo Smart Router telah berhenti.
pause
```

**Langkah 4.** Simpan dengan `Ctrl + S`.

**Langkah 5.** Klik dua kali `Start Smart Router.bat` untuk menjalankannya.

> Jika perintah `python` tidak dikenali, pastikan Python sudah terinstal dan ditambahkan ke PATH Windows. Kamu juga dapat mencoba mengganti `python` dengan `py`.

### 🍎 macOS & 🐧 Linux — Launcher `.sh`

**Langkah 1.** Buat file bernama:

```text
Start Smart Router.sh
```

**Langkah 2.** Masukkan kode berikut:

```bash
#!/bin/bash

echo ""
echo "========================================"
echo "       SMART ROUTER FOR CONTINUE"
echo "========================================"
echo ""

# Pindah ke folder tempat launcher berada
cd "$(dirname "$0")" || exit 1

# Jalankan Smart Router
python3 smart_router.py

# Tahan terminal agar error dapat dibaca
echo ""
read -r -p "Tekan Enter untuk keluar..."
```

**Langkah 3.** Simpan file.

**Langkah 4.** Buka terminal pada folder project, kemudian jalankan:

```bash
chmod +x "Start Smart Router.sh"
```

**Langkah 5.** Jalankan launcher melalui terminal:

```bash
./"Start Smart Router.sh"
```

Pada lingkungan desktop yang mendukungnya, kamu juga dapat menjalankan file tersebut melalui aplikasi file manager setelah memberikan izin eksekusi.

---

## 🧪 Pengujian Lokal (Tanpa API Key)

Project ini dilengkapi **test suite otomatis** yang dapat dijalankan langsung di mesinmu — tanpa perlu API key asli dan tanpa koneksi ke Groq/OpenRouter. Cocok untuk memverifikasi hasil perubahan kode sebelum dipakai bersama Continue.dev.

### 📄 File Test

| File | Fungsi |
|---|---|
| `test_mock_upstream.py` | Mock server OpenAI-compatible lokal. Menjalankan 2 instance dalam satu proses: **port 9901 = upstream sehat** (echo respons SSE/JSON normal) dan **port 9902 = upstream sakit** (respons selalu hang, untuk menguji mekanisme rotasi model). |
| `test_router.py` | Test suite end-to-end. Men-mock daftar model provider, menjalankan `smart_router.py` sungguhan di **port 8799**, lalu menguji seluruh perilaku router lewat HTTP nyata. Otomatis men-start & menghentikan mock upstream sendiri. |

### ▶️ Cara Menjalankan

```bash
# dari folder project
python3 test_router.py        # Windows bisa pakai: python test_router.py
```

Output berakhir dengan ringkasan, contoh:

```text
===== HASIL =====
Lulus: 20 | Gagal: 0
```

Exit code `0` berarti semua test lulus; exit code `1` ada test yang gagal.

> 💡 Kamu cukup menjalankan `test_router.py` — file itu otomatis memanggil `test_mock_upstream.py`. Tidak perlu menjalankannya terpisah.

### ✅ Yang Diuji

| Test | Perilaku yang diverifikasi |
|---|---|
| T0 | Filter harga OpenRouter berbasis angka float (`pricing.prompt = 0.0` tetap dianggap gratis) + kuota per-provider di model pool |
| T1, T12 | `GET /health` merespons cepat tanpa hang (header `Content-Length` benar) |
| T2 | `GET /v1/models` tidak membocorkan API key |
| T3, T4 | Routing eksplisit: path tak dikenal → 404 JSON; body invalid → 400 JSON |
| T5, T5b | Chat non-stream berhasil; `temperature` & `max_tokens` dari client diteruskan ke upstream |
| T6 | Streaming SSE utuh sampai `data: [DONE]` |
| T7, T7b, T7c | Content multimodal (list) dipertahankan; default `temperature=0.4` terkirim saat client tidak mengatur; temperature client tidak ditimpa |
| T8 | `/health` tetap responsif selama streaming berjalan (ThreadingHTTPServer) |
| T9, T9b | Rotasi otomatis saat model pertama hang → stream tetap selesai; cache model tidak di-fetch ulang tiap request |
| T10, T10b | Semua model gagal → SSE error event + `[DONE]` (mode stream) dan 503 JSON seragam (mode non-stream) |
| T11 | Hasil filter kosong ikut ter-cache (tidak memicu loop refetch ke provider) |

### 🛠️ Troubleshooting Test

| Masalah | Solusi |
|---|---|
| `OSError: Address already in use` (port 8799/9901/9902) | Matikan proses sisa terlebih dahulu: Linux/macOS `pkill -f smart_router; pkill -f test_mock_upstream` — Windows `taskkill /F /IM python.exe` atau tutup terminal/jendela lama. |
| Test tampak menggantung | Pastikan tidak ada instance `smart_router.py` produksi yang memakai port yang sama; ubah sementara via env `PORT`. |
| `ModuleNotFoundError: requests` | Install dependencies: `python -m pip install -r requirements.txt`. |

### 🔎 Smoke Test Manual (dengan API key asli)

Setelah test suite lulus, kamu bisa mencoba terhadap provider sungguhan:

```bash
python3 smart_router.py            # jalankan router normal (terminal lain)

curl http://127.0.0.1:8765/health  # cek hidup
curl http://127.0.0.1:8765/v1/models   # cek model pool terpilih
curl -N http://127.0.0.1:8765/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"tulis fungsi fibonacci"}],"stream":true}'
```

---

## 🔌 Integrasi dengan Continue.dev

Setelah Smart Router berjalan, konfigurasikan Continue.dev agar terhubung ke endpoint dan port yang disediakan oleh aplikasi ini.

Pastikan hal-hal berikut:

1. Smart Router berhasil dijalankan tanpa error.
2. Endpoint dan port yang digunakan sesuai dengan konfigurasi project.
3. Konfigurasi model di Continue.dev mengarah ke endpoint Smart Router yang benar.
4. Model dan provider yang dipilih masih tersedia dan dapat diakses menggunakan API key milikmu.

> **Penting:** Gunakan alamat endpoint, port, dan format konfigurasi yang benar-benar ditentukan oleh source code project. Jangan menebak nilai endpoint atau port jika belum memeriksa implementasinya.

---

## 🧰 Troubleshooting

| Masalah | Kemungkinan Solusi |
|---|---|
| `ModuleNotFoundError` | Jalankan `python -m pip install -r requirements.txt`. |
| `python is not recognized` | Periksa instalasi Python dan PATH. Di Windows, coba `py smart_router.py`. |
| Continue menampilkan `Connection error` | Pastikan Smart Router masih berjalan dan endpoint serta port sudah sesuai. |
| API key tidak valid | Periksa kembali key, provider, dan konfigurasi `.env`. |

Jika masalah masih terjadi, periksa pesan error di terminal terlebih dahulu sebelum mengubah konfigurasi.

---

## 🔐 Keamanan

Smart Router menggunakan API key untuk mengakses provider AI. Jaga kerahasiaannya dengan mengikuti praktik berikut:

- Jangan menulis API key langsung ke source code.
- Jangan mengunggah `.env` ke repository publik.
- Tambahkan `.env` ke `.gitignore`.
- Gunakan placeholder dalam dokumentasi dan contoh konfigurasi.
- Jika API key terlanjur terpublikasi, segera cabut atau rotasi key tersebut melalui dashboard provider.

---

## 🤝 Kontribusi

Punya ide, menemukan bug, atau ingin meningkatkan fitur Smart Router?

Kontribusi sangat terbuka!

1. Fork repository ini.
2. Buat branch baru untuk perubahanmu.
3. Lakukan perubahan dan pengujian.
4. Kirim Pull Request dengan deskripsi yang jelas.

Setiap saran dan kontribusi dapat membantu project ini menjadi lebih baik.

---

## 📜 Lisensi

Project ini dirilis di bawah **MIT License**.

Lihat file [LICENSE](LICENSE) untuk informasi selengkapnya.

---

<p align="center">
  <strong>🧠 Smart Router for Continue</strong>
  <br>
  <em>Smarter Routing. Faster Coding. Less Hassle.</em>
  <br><br>
  Made with ❤️ for the developer community.
</p>
