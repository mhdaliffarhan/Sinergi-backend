import models, database
from sqlalchemy.orm import Session
from datetime import datetime
import time

def process_reminders():
    db: Session = database.SessionLocal()
    try:
        from sqlalchemy import func
        now = datetime.now()
        print(f"[{now}] Checking for due reminders...")

        # Ambil reminder yang pending, aktif, dan sudah waktunya (scheduled_at <= func.now())
        due_reminders = (
            db.query(models.AktivitasReminder)
            .filter(
                models.AktivitasReminder.status == "pending",
                models.AktivitasReminder.is_active == True,
                models.AktivitasReminder.scheduled_at <= func.now()
            )
            .all()
        )

        if not due_reminders:
            print("No reminders to process.")
            return

        for rem in due_reminders:
            aktivitas = rem.aktivitas
            if not aktivitas:
                rem.status = "failed"
                db.commit()
                continue
            
            print(f"Processing reminder for activity: {aktivitas.nama_aktivitas} (Type: {rem.reminder_type})")
            
            # Persiapkan template pesan
            tgl_mulai = aktivitas.tanggal_mulai.strftime('%d %B %Y') if aktivitas.tanggal_mulai else "-"
            jam_mulai = aktivitas.jam_mulai.strftime('%H.%M') if aktivitas.jam_mulai else "-"
            
            # Link detail (sesuaikan dengan base url)
            base_url = "https://satset.statsntb.id"
            link_detail = f"{base_url}/aktivitas/detail/{aktivitas.id}"

            # Loop semua peserta aktivitas saat ini
            for user in aktivitas.users:
                if user.nohp:
                    message = (
                        f"⏰ *PENGINGAT AKTIVITAS*\n\n"
                        f"Halo {user.nama_lengkap},\n"
                        f"Mengingatkan kembali untuk aktivitas:\n\n"
                        f"📌 *{aktivitas.nama_aktivitas}*\n"
                        f"🗓️ Tanggal: {tgl_mulai}\n"
                        f"⏰ Waktu: {jam_mulai} WITA\n\n"
                        f"Mohon kehadirannya tepat waktu. Terimakasih.\n\n"
                        f"Cek detail:\n{link_detail}"
                    )

                    # Masukkan ke WaQueue
                    new_queue = models.WaQueue(
                        phone_number=user.nohp,
                        message=message,
                        status="pending",
                        scheduled_at=rem.scheduled_at,
                        aktivitas_id=aktivitas.id
                    )
                    db.add(new_queue)
            
            # Tandai reminder sudah diproses
            rem.status = "sent"
            db.commit()
            print(f"Successfully queued messages for {len(aktivitas.users)} participants.")

    except Exception as e:
        print(f"Error processing reminders: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    process_reminders()
