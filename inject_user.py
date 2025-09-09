# File: inject_user.py

from database import SessionLocal
from models import User
from security import get_password_hash

# Membuat koneksi ke database
db = SessionLocal()

# --- DATA DUMMY PENGGUNA ---
# Anda bisa mengubah data ini sesuai keinginan
username = "ketua.tim2"
password_asli = "password123" # Ini hanya untuk script ini, tidak akan disimpan
nama_lengkap_pengguna = "Ketua Tim Dua"

print("Mencoba membuat pengguna...")

# Cek apakah user sudah ada untuk menghindari duplikasi
user_exists = db.query(User).filter(User.username == username).first()

if not user_exists:
    # Enkripsi password menggunakan fungsi yang sudah kita buat di security.py
    hashed_password = get_password_hash(password_asli)

    # Buat objek user baru
    user_baru = User(
        username=username,
        hashed_password=hashed_password,
        nama_lengkap=nama_lengkap_pengguna,
        is_active=True
    )

    # Tambahkan ke database dan simpan
    db.add(user_baru)
    db.commit()

    print(f"✅ Pengguna '{username}' berhasil dibuat.")
    print(f"🔑 Password-nya adalah: '{password_asli}' (gunakan ini untuk login)")
else:
    print(f"⚠️ Pengguna '{username}' sudah ada di database.")

# Tutup koneksi
db.close()
print("Skrip selesai.")