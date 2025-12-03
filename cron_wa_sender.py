import sys
import os
import asyncio # Wajib untuk menjalankan fungsi async
import random
from datetime import datetime
from sqlalchemy.orm import Session

# Tambahkan direktori saat ini ke sys.path agar bisa import models dll
sys.path.append(os.getcwd())

import models
import database
import services_wa 

# Konfigurasi
BATCH_SIZE = 5       # Ambil 5 pesan per eksekusi
MIN_DELAY = 15       # Jeda minimal antar pesan (detik)
MAX_DELAY = 30       # Jeda maksimal antar pesan (detik)

async def process_wa_queue():
    print(f"--- [{datetime.now()}] Memulai Cron Job WA Sender ---")
    
    # Buka koneksi database (Sync Session tidak masalah di script sederhana ini)
    db = database.SessionLocal()
    
    try:
        # 1. Ambil pesan pending
        queue_items = db.query(models.WaQueue)\
            .filter(models.WaQueue.status == 'pending')\
            .order_by(models.WaQueue.created_at.asc())\
            .limit(BATCH_SIZE)\
            .all()

        if not queue_items:
            print("Tidak ada antrian pesan pending.")
            return

        print(f"Ditemukan {len(queue_items)} pesan untuk dikirim.")

        for index, item in enumerate(queue_items):
            try:
                print(f"[{index+1}/{len(queue_items)}] Mengirim ke {item.phone_number} (ID: {item.id})...")
                
                # --- PERBAIKAN UTAMA DI SINI ---
                # Gunakan 'await' karena services_wa.send_whatsapp_message adalah async
                await services_wa.send_whatsapp_message(item.phone_number, item.message)
                
                # Update Sukses
                item.status = 'sent'
                item.sent_at = datetime.now()
                print(f"   -> SUKSES TERKIRIM")

            except Exception as e:
                # Update Gagal
                item.status = 'failed'
                item.retry_count += 1
                item.error_log = str(e)
                print(f"   -> GAGAL: {e}")

            # Commit per item agar status tersimpan meskipun script berhenti di tengah
            db.commit()

            # --- THROTTLING & JITTER (Non-Blocking Sleep) ---
            if index < len(queue_items) - 1:
                delay = random.randint(MIN_DELAY, MAX_DELAY)
                print(f"   -> Menunggu {delay} detik sebelum pesan berikutnya...")
                # Gunakan asyncio.sleep agar flow async berjalan benar
                await asyncio.sleep(delay)

    except Exception as e:
        print(f"Critical Error pada Cron Job: {e}")
        db.rollback()
    finally:
        db.close()
        print(f"--- [{datetime.now()}] Selesai ---\n")

if __name__ == "__main__":
    # Menjalankan fungsi async di top-level script
    if sys.platform == 'win32':
        # Fix khusus Windows untuk event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(process_wa_queue())

