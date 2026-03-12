# 🚀 SATSET (Sarana Aktivitas Terpadu & Sinkronisasi Ekosistem Terdata) - Backend

**SATSET** adalah antarmuka Ceritanya (Backend API) yang mentransformasi manajemen aktivitas dan kolaborasi pegawai BPS Provinsi NTB menjadi ekosistem yang serba cepat dan tertata. Dibangun dengan FastAPI untuk performa tinggi dan sinkronisasi data yang akurat.

> **Tagline**: *"Kolaborasi Cepat, Dokumentasi Tertata"*

---

### ✨ Fitur Utama (Backend):
- **FastAPI Core**: Performa asinkronus yang sangat cepat dan dokumentasi API otomatis (Swagger).
- **Manajemen Kolaborasi**: Pengelolaan Tim, Proyek, dan Anggota secara fleksibel.
- **Tracking Aktivitas**: Monitoring tugas harian dengan sistem checklist dokumen wajib.
- **WhatsApp Notification**: Integrasi pengiriman notifikasi otomatis via WhatsApp (Anti-Bot Delay).
- **Export & Backup**: Fitur ekspor data ke Excel dan sinkronisasi file ke ZIP.
- **PINTU SSO Integrated**: Keamanan tingkat tinggi m menggunakan ekosistem SSO PINTU.

---

## 🛠 Persiapan Lokal

### 1. Prasyarat
- **Python 3.9+**
- **PostgreSQL** (atau database SQL lainnya)
- **Virtual Environment** (Direkomendasikan)

### 2. Instalasi
Clone repositori dan masuk ke direktori proyek:
```bash
git clone https://github.com/mhdaliffarhan/satset-backend.git
cd satset-backend
```

Buat dan aktifkan virtual environment:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

Instal dependensi:
```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Database
Buat database di PostgreSQL, lalu jalankan migrasi (jika menggunakan Alembic):
```bash
alembic upgrade head
```
Atau jalankan script inisialisasi jika tersedia.

### 4. Konfigurasi Environment (`.env`)
Salin `.env.example` (jika ada) atau buat file `.env` baru:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/nama_db_satset
SECRET_KEY=isi_random_string_panjang
ALGORITHM=HS256

# SSO PINTU
SSO_BASE_URL=https://auth.pintu.statsntb.id
SSO_CLIENT_ID=your_client_id
SSO_CLIENT_SECRET=your_client_secret
SSO_REDIRECT_URI=http://localhost:5173/auth/sso-callback
```

### 5. Jalankan Server
Gunakan Uvicorn untuk menjalankan server lokal:
```bash
uvicorn main:app --reload
```
API akan dapat diakses di `http://localhost:8000`. Dokumentasi Swagger tersedia di `/docs`.

---

## 🌐 Panduan Deployment (Gestrong/Hestia CP)

Untuk panduan lengkap pemasangan di server produksi, silakan baca:
👉 **[PANDUAN DEPLOYMENT](DEPLOYMENT.md)**

---

## 📜 Lisensi & Copyright
© 2026 **Tim IPDS Provinsi Nusa Tenggara Barat**
| Creator: **M Alif Farhan**
