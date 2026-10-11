# 🧠 Smart Router untuk Continue

Selamat datang di **Smart Router**, sistem routing AI otomatis untuk [Continue](https://continue.dev/) yang secara cerdas memilih **8 model coding gratis terbaik** dari OpenRouter secara *real-time*. 

Project ini dibangun untuk memberikan pengalaman *coding* AI yang **gratis, cepat, ringan, dan tanpa ribet**.

![License](https://img.shields.io/badge/License-MIT-green.svg)
![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Free-orange.svg)

---

## ✨ Fitur Utama

- 🎯 **Auto-Filter Cerdas:** Otomatis menyaring model gratis yang spesifik untuk *coding* (mengabaikan model gambar, embedding, atau safety).
- 📊 **Skor Kecerdasan:** Mengurutkan model dari performa tertinggi ke terendah (*high-to-low*).
- ⚡ **Ultra-Lightweight:** Konsumsi resource minimal (<10MB RAM, 0% CPU saat *idle*).
- 💤 **Auto-Sleep:** Server otomatis mati setelah 5 menit tidak digunakan untuk menghemat resource laptop.
- 🔄 **Smart Fallback:** Jika model utama mengalami *rate-limit* atau *down*, otomatis pindah ke model cadangan berikutnya.
- 🔒 **Keamanan Terjamin:** API key tidak pernah di-*commit* ke GitHub (mendukung input CLI lokal yang aman atau file `.env`).

---

## 🚀 Quick Start

### 1. Clone Repository
Buka terminal Anda dan jalankan perintah berikut:
```bash
git clone https://github.com/anasfanu/smart-router-continue.git
cd smart-router-continue
```

### 2. Setup API Key
Smart Router membutuhkan API Key dari OpenRouter (Gratis). Anda bisa memilih salah satu dari dua cara di bawah ini:

#### 🌟 Cara A: Via CLI (Paling Mudah - Direkomendasikan)
Cukup jalankan script utama:
```bash
python smart_router.py
```
Jika belum ada konfigurasi, program akan otomatis memandu Anda untuk memasukkan API Key melalui terminal. Key akan disimpan dengan aman di folder profil user lokal Anda.

#### 💻 Cara B: Via File .env (Untuk Developer)
1. Salin file contoh:
   ```bash
   cp .env.example .env
   ```
2. Buka file `.env` yang baru dibuat, lalu tempel API Key Anda:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
   ```

---

## 🎯 Tutorial Membuat Launcher Otomatis

Agar Anda tidak perlu mengetik perintah di terminal setiap kali ingin ngoding, Anda bisa membuat file launcher (pintasan). Cukup double-click, server langsung jalan!

### 🪟 Untuk Pengguna Windows (.bat)
1. Buka folder project `smart-router-continue` di File Explorer.
2. Klik kanan di area kosong → **New** → **Text Document**.
3. Beri nama file: `Start Smart Router.bat`  
   *⚠️ **PENTING:** Pastikan akhiran filenya benar-benar `.bat`, bukan `.bat.txt`. (Aktifkan "File name extensions" di tab View File Explorer jika perlu).*
4. Klik kanan file `Start Smart Router.bat` tersebut, pilih **Edit** (atau buka dengan Notepad).
5. Copy dan Paste kode berikut ke dalamnya:
   ```cmd
   @echo off
   title Smart Router for Continue
   echo 🚀 Starting Smart Router...
   
   :: Pindah ke folder tempat file ini berada secara dinamis
   cd /d "%~dp0"
   
   :: Jalankan script Python
   python smart_router.py
   
   :: Jendela tetap terbuka jika ada error, agar pesan error bisa dibaca
   pause
   ```
6. Simpan (Ctrl + S) dan tutup. Sekarang, cukup double-click file ini setiap kali Anda mau mulai ngoding.

### 🍎 / 🐧 Untuk Pengguna macOS & Linux (.sh)
1. Buka folder project `smart-router-continue`.
2. Buat file baru bernama `Start Smart Router.sh`.
3. Buka file tersebut dengan text editor (seperti TextEdit, Gedit, atau nano di terminal).
4. Copy dan Paste kode berikut ke dalamnya:
   ```bash
   #!/bin/bash
   echo "🚀 Starting Smart Router..."
   
   # Pindah ke folder tempat file ini berada secara dinamis
   cd "$(dirname "$0")"
   
   # Jalankan script Python
   python3 smart_router.py
   
   # Tahan terminal agar pesan error bisa dibaca jika terjadi masalah
   read -p "Tekan Enter untuk keluar..."
   ```
5. Simpan file (Ctrl + S, atau Ctrl + O lalu Enter jika pakai nano).
6. **PENTING:** Berikan izin eksekusi pada file tersebut. Buka terminal di dalam folder project, lalu jalankan:
   ```bash
   chmod +x "Start Smart Router.sh"
   ```
7. Selesai! Sekarang Anda bisa menjalankan server cukup dengan double-click file `Start Smart Router.sh` tersebut (pilih "Run" atau "Execute" jika diminta oleh sistem).

---

## 📜 Lisensi (MIT License)

Project ini dirilis di bawah lisensi MIT License.

### ✅ Yang BOLEH Anda lakukan:
- Menggunakan software ini untuk tujuan pribadi maupun komersial.
- Memodifikasi, mengubah, atau mengembangkan kode ini.
- Mendistribusikan atau menjual produk yang menggunakan kode ini.
- Menggunakan kode ini di project tertutup (*closed-source*).

### ❌ Batasan & Tanggung Jawab:
- Penulis tidak memberikan garansi apapun (software disediakan "APA ADANYA" / *as is*).
- Penulis tidak bertanggung jawab atas kerusakan, kehilangan data, atau masalah hukum yang mungkin timbul akibat penggunaan software ini.
- Anda tetap harus menyertakan salinan lisensi MIT dan hak cipta asli jika Anda mendistribusikan ulang kode ini.

---
Dibuat dengan ❤️ untuk komunitas developer yang ingin memaksimalkan AI coding secara gratis, efisien, dan aman.
