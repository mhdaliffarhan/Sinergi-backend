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
BATCH_SIZE = 20      # Ambil 20 pesan per batch
MIN_DELAY = 10       # Jeda minimal antar pesan (detik)
MAX_DELAY = 20       # Jeda maksimal antar pesan (detik)
MAX_TOTAL_MESSAGES = 100 # Maksimal pesan per satu kali eksekusi cron agar tidak terlalu lama
MAX_RUN_TIME = 280   # Detik (sekitar 4.5 menit), anggap cron jalan tiap 5 menit

async def process_wa_queue():
    start_time = datetime.now()
    total_sent = 0
    print(f"--- [{start_time}] Memulai Cron Job WA Sender ---")
    
    db = database.SessionLocal()
    
    try:
        while total_sent < MAX_TOTAL_MESSAGES:
            # Cek durasi eksekusi
            if (datetime.now() - start_time).total_seconds() > MAX_RUN_TIME:
                print("Waktu eksekusi maksimal tercapai. Berhenti.")
                break

            # 1. Ambil pesan pending
            queue_items = db.query(models.WaQueue)\
                .filter(models.WaQueue.status == 'pending')\
                .order_by(models.WaQueue.created_at.asc())\
                .limit(BATCH_SIZE)\
                .all()

            if not queue_items:
                if total_sent == 0:
                    print("Tidak ada antrian pesan pending.")
                else:
                    print(f"Selesai. Total terkirim pada sesi ini: {total_sent}")
                break

            print(f"Batch Baru: Ditemukan {len(queue_items)} pesan untuk dikirim.")

            for index, item in enumerate(queue_items):
                try:
                    # Cek lagi durasi di tengah batch
                    if (datetime.now() - start_time).total_seconds() > MAX_RUN_TIME:
                        print("Waktu eksekusi maksimal tercapai di tengah batch.")
                        return

                    print(f"[{total_sent + 1}/{MAX_TOTAL_MESSAGES}] Mengirim ke {item.phone_number} (ID: {item.id})...")
                    
                    await services_wa.send_whatsapp_message(item.phone_number, item.message)
                    
                    item.status = 'sent'
                    item.sent_at = datetime.now()
                    total_sent += 1
                    print(f"   -> SUKSES TERKIRIM")

                except Exception as e:
                    item.status = 'failed'
                    item.retry_count += 1
                    item.error_log = str(e)
                    print(f"   -> GAGAL: {e}")

                db.commit()

                # Jitter antar pesan
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                await asyncio.sleep(delay)

            # Jeda kecil antar batch
            await asyncio.sleep(2)

    except Exception as e:
        print(f"Critical Error pada Cron Job: {e}")
        db.rollback()
    finally:
        db.close()
        print(f"--- [{datetime.now()}] Selesai. Total diproses: {total_sent} ---\n")

if __name__ == "__main__":
    # Menjalankan fungsi async di top-level script
    if sys.platform == 'win32':
        # Fix khusus Windows untuk event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(process_wa_queue())

