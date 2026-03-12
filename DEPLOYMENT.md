# 🚀 Panduan Deployment SATSET Backend (Hestia CP)

Dokumen ini menjelaskan langkah-langkah detail untuk meng-hosting **SATSET Backend (FastAPI)** di server Hestia CP menggunakan alur Git Pull.

---

## 📋 Detail Server
- **Stack**: FastAPI (Python 3.9+) + PostgreSQL + Nginx (Reverse Proxy)
- **Domain API**: `api.satset.statsntb.id`
- **Database**: PostgreSQL 14+

---

## 🛠 Langkah-Langkah Instalasi

### 1. Persiapan Database (PostgreSQL)
- Masuk ke panel Hestia CP.
- Masuk ke menu **DB**.
- Klik **Add Database**.
- Pilih Type: **PostgreSQL**.
- Nama Database: `satset_db`.
- Username: `satset_user`.
- Password: *Gunakan password yang aman*.

### 2. Tambahkan Web Domain
- Masuk ke menu **Web**.
- Klik **Add Web Domain**.
- Domain: `api.satset.statsntb.id`.
- Aktifkan **SSL (Let's Encrypt)**.
- **PENTING**: Karena ini aplikasi Python (FastAPI), kita perlu mengatur Nginx sebagai Proxy Pass.

### 3. Setup Lingkungan Python via SSH
Login ke server dan jalankan perintah berikut:
```bash
cd /home/user/web/api.satset.statsntb.id/public_html
git clone https://github.com/mhdaliffarhan/satset-backend.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn uvicorn
```

### 4. Konfigurasi Environment (`.env`)
Buat file `.env` di server:
```env
DATABASE_URL=postgresql://satset_user:password@localhost:5432/satset_db
SECRET_KEY=kunci_rahasia_anda_disini
ALGORITHM=HS256
```

### 5. Konfigurasi Service (Systemd)
Agar API tetap berjalan di background, buat service systemd (Opsional jika ingin otomatis):
```bash
sudo nano /etc/systemd/system/satset-api.service
```
Isi dengan:
```ini
[Unit]
Description=Gunicorn instance to serve SATSET API
After=network.target

[Service]
User=spbe
Group=www-data
WorkingDirectory=/home/spbe/web/api.satset.statsntb.id/public_html
Environment="PATH=/home/spbe/web/api.satset.statsntb.id/public_html/venv/bin"
ExecStart=/home/spbe/web/api.satset.statsntb.id/public_html/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```
Jalankan service: `sudo systemctl start satset-api && sudo systemctl enable satset-api`.

### 6. Konfigurasi Nginx Proxy (Hestia CP)
Ubah template Nginx atau tambahkan manual di `/etc/nginx/conf.d/domains/api.satset.statsntb.id.conf`:
```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

---

## 🆘 Troubleshooting

| Gejala | Solusi |
| :--- | :--- |
| **502 Bad Gateway** | Cek apakah service Uvicorn/Gunicorn sudah berjalan (`systemctl status satset-api`). |
| **Gagal Koneksi DB** | Pastikan host PostgreSQL adalah `localhost` dan port `5432` terbuka. |
| **ModuleNotFoundError** | Pastikan virtual environment sudah aktif saat menjalankan `pip install`. |
| **Error JWT/Secret** | Pastikan `SECRET_KEY` di `.env` sudah diisi dengan benar. |

---

## 🔄 Pembaruan Berkelanjutan
Jika ada update kode:
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart satset-api
```

---

## 📜 Copyright
© 2026 **Tim IPDS Provinsi Nusa Tenggara Barat**
