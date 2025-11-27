import os
import shutil
import uuid
from datetime import datetime
import sys
from sqlalchemy import text

# Setup path agar bisa import models dan database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import models
    import database
    from sqlalchemy.orm import Session, joinedload
except ImportError as e:
    print(f"Error Import: {e}")
    print("Pastikan skrip ini dijalankan di root folder backend (sejajar dengan main.py)")
    sys.exit(1)

# Konfigurasi Folder
OLD_BASE_DIR = "dokumen" 
NEW_BASE_DIR = "storage"

def migrate_physical_files(db: Session):
    print("\n--- [FASE 1] MIGRASI FILE FISIK (Immutable Storage) ---")
    
    # Ambil semua dokumen bertipe FILE
    docs = db.query(models.Dokumen).filter(models.Dokumen.tipe == 'FILE').all()
    print(f"🔍 Memeriksa {len(docs)} dokumen...")
    
    success_count = 0
    error_count = 0
    skipped_count = 0

    for doc in docs:
        old_path = doc.path_atau_url
        
        if not old_path:
            skipped_count += 1
            continue
            
        # Normalisasi path (ganti backslash jadi slash)
        normalized_path = old_path.replace("\\", "/")
        
        # Cek apakah sudah format baru
        if normalized_path.startswith("storage/"):
            skipped_count += 1
            continue

        # Cek keberadaan file fisik lama
        real_old_path = old_path
        if not os.path.exists(real_old_path):
            # Coba cek relative terhadap current directory
            if os.path.exists(os.path.join(os.getcwd(), old_path)):
                real_old_path = os.path.join(os.getcwd(), old_path)
            else:
                print(f"❌ ID {doc.id}: File tidak ditemukan di '{old_path}'. Skip.")
                error_count += 1
                continue

        try:
            # 1. Tentukan Folder Tujuan
            tgl = doc.diunggah_pada if doc.diunggah_pada else datetime.now()
            year_str = str(tgl.year)
            month_str = f"{tgl.month:02d}"
            
            target_folder = os.path.join(NEW_BASE_DIR, year_str, month_str)
            if not os.path.exists(target_folder):
                os.makedirs(target_folder, exist_ok=True)
            
            # 2. Generate UUID Filename
            filename = os.path.basename(real_old_path)
            ext = filename.split('.')[-1] if '.' in filename else 'bin'
            new_filename = f"{uuid.uuid4()}.{ext}"
            target_path = os.path.join(target_folder, new_filename)
            
            # 3. Copy File
            shutil.copy2(real_old_path, target_path)
            
            # 4. Update Database Path
            relative_new_path = os.path.join(NEW_BASE_DIR, year_str, month_str, new_filename).replace("\\", "/")
            doc.path_atau_url = relative_new_path
            
            # Isi nama file asli jika kosong
            if not doc.nama_file_asli:
                doc.nama_file_asli = filename
            
            print(f"✅ ID {doc.id}: Dipindahkan ke -> {relative_new_path}")
            success_count += 1

        except Exception as e:
            print(f"❌ ID {doc.id}: Gagal migrasi. Error: {e}")
            error_count += 1
    
    db.commit()
    print(f"-> Fase 1 Selesai. Sukses: {success_count}, Skip: {skipped_count}, Gagal: {error_count}")


def reconnect_checklist_relations(db: Session):
    print("\n--- [FASE 2] REKONEKSI RELASI DOKUMEN & CHECKLIST ---")
    print("Mencocokkan 'Dokumen.keterangan' dengan 'DaftarDokumen.nama_dokumen'...")
    
    # 1. Ambil semua aktivitas yang memiliki dokumen
    # Kita load dokumen dan daftar_dokumen_wajib sekaligus untuk efisiensi
    activities = db.query(models.Aktivitas).options(
        joinedload(models.Aktivitas.dokumen),
        joinedload(models.Aktivitas.daftar_dokumen_wajib)
    ).all()
    
    linked_count = 0
    
    for activity in activities:
        # Skip jika tidak ada dokumen atau tidak ada checklist
        if not activity.dokumen or not activity.daftar_dokumen_wajib:
            continue
            
        # Loop semua dokumen di aktivitas ini
        for doc in activity.dokumen:
            # Hanya proses jika belum terhubung ke checklist
            if doc.daftar_dokumen_id is None and doc.keterangan:
                
                doc_keterangan_clean = doc.keterangan.strip().lower()
                
                # Cari item checklist yang namanya COCOK
                for checklist_item in activity.daftar_dokumen_wajib:
                    checklist_name_clean = checklist_item.nama_dokumen.strip().lower()
                    
                    if doc_keterangan_clean == checklist_name_clean:
                        # MATCH FOUND!
                        print(f"🔗 Match! Aktivitas ID {activity.id}: Dokumen '{doc.keterangan}' -> Checklist '{checklist_item.nama_dokumen}'")
                        
                        # Update relasi
                        doc.daftar_dokumen_id = checklist_item.id
                        
                        # Opsional: Update status pengecekan jadi True jika mau otomatis
                        # checklist_item.status_pengecekan = True 
                        
                        linked_count += 1
                        break # Pindah ke dokumen berikutnya setelah match
    
    db.commit()
    print(f"-> Fase 2 Selesai. Berhasil menautkan {linked_count} dokumen ke checklist.")


def main():
    db = database.SessionLocal()
    try:
        # Jalankan Fase 1: Pindah File
        migrate_physical_files(db)
        
        # Jalankan Fase 2: Perbaiki Relasi Database
        reconnect_checklist_relations(db)
        
        print("\n🎉 SEMUA PROSES MIGRASI SELESAI!")
        
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Pastikan engine database siap
    if not hasattr(database, 'engine'):
        pass 
    main()