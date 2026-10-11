# 🧠 Smart Router untuk Continue

Sistem routing AI otomatis untuk [Continue](https://continue.dev/) yang memilih 8 model coding gratis terbaik dari OpenRouter secara otomatis.

## ✨ Fitur

- ✅ **Auto-filter model gratis** dari OpenRouter
- ✅ **Filter coding high-to-low** berdasarkan skor kecerdasan
- ✅ **Ambil 8 terbaik** secara otomatis
- ✅ **Ultra-light**: <10MB RAM, 0% CPU saat idle
- ✅ **Auto-stop** setelah 5 menit idle
- ✅ **Cache 1 jam** untuk hemat API call
- ✅ **Support streaming** untuk Continue
- ✅ **API key aman** di `.env` (tidak ter-commit ke GitHub)

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/anasfanu/smart-router-continue.git
cd smart-router-continue

## 🔐 Setup API Key (Wajib)

Smart Router membutuhkan API key OpenRouter (gratis) untuk berjalan. Ada 2 cara setup:

### Cara 1: Via CLI (Paling Mudah - Direkomendasikan)
Cukup jalankan `python smart_router.py`. Jika belum ada API key, program akan otomatis meminta kamu input. Key akan disimpan aman di folder user profile kamu.

### Cara 2: Via File `.env` (Untuk Developer)
1. Salin `.env.example` ke `.env`:
   ```bash
   cp .env.example .env