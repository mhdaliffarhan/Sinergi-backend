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
            
            # --- SKIP IF ALREADY FINISHED ---
            if aktivitas.status == "Selesai":
                rem.status = "skipped"
                db.commit()
                print(f"Skipping reminder for activity {aktivitas.id} as it is already 'Selesai'.")
                continue

            print(f"Processing reminder for activity: {aktivitas.nama_aktivitas} (Type: {rem.reminder_type})")
            
            # Persiapkan template pesan
            tgl_mulai = aktivitas.tanggal_mulai.strftime('%d %B %Y') if aktivitas.tanggal_mulai else "-"
            jam_mulai = aktivitas.jam_mulai.strftime('%H.%M') if aktivitas.jam_mulai else "-"
            
            # Link detail (sesuaikan dengan base url)
            base_url = "https://satset.statsntb.id"
            link_detail = f"{base_url}/aktivitas/detail/{aktivitas.id}"

            # --- CUSTOM MESSAGE BASED ON TYPE ---
            is_nudge = "deadline" in rem.reminder_type
            
            # Kumpulkan target penerima
            recipients = list(aktivitas.users)
            
            # Jika H+1 Terlewat (atau tipe tertentu yang menandakan overdue)
            # Kita anggap 'deadline' atau 'deadline_minus_0' dipicu setelah deadline terlewati atau tepat di hari H
            is_overdue = rem.reminder_type == "deadline" and aktivitas.status != "Menunggu Validasi"
            
            # Tambahkan Leader sebagai penerima jika overdue
            if is_overdue and aktivitas.team and aktivitas.team.ketua_tim:
                if aktivitas.team.ketua_tim not in recipients:
                    recipients.append(aktivitas.team.ketua_tim)

            for user in recipients:
                if not user.nohp: continue
                
                # Role Check for Message
                is_leader = aktivitas.team and user.id == aktivitas.team.ketua_tim_id
                
                if is_nudge:
                    if is_overdue and is_leader:
                        title = "🚨 *LAPORAN TUNGGAKAN*"
                        body = f"Aktivitas berikut telah *MELEWATI TENGGAT WAKTU* dan belum diselesaikan oleh anggota tim Anda:"
                    elif is_overdue:
                        title = "🔥 *PERINGATAN TENGGAT*"
                        body = f"Aktivitas ini sudah melewati deadline! Segera selesaikan dan minta validasi pimpinan."
                    else:
                        title = "⚠️ *PENGINGAT DEADLINE*"
                        body = f"Aktivitas ini mendekati tenggat waktu. Pastikan dokumen sudah lengkap ya!"
                else:
                    title = "⏰ *PENGINGAT AKTIVITAS*"
                    body = f"Mengingatkan kembali untuk aktivitas:"

                message = (
                    f"{title}\n\n"
                    f"Halo {user.nama_lengkap},\n"
                    f"{body}\n\n"
                    f"📌 *{aktivitas.nama_aktivitas}*\n"
                    f"🗓️ Deadline: {tgl_mulai}\n\n"
                    f"Mohon perhatiannya. Terimakasih.\n\n"
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
            print(f"Successfully queued messages for {len(recipients)} recipients.")

    except Exception as e:
        print(f"Error processing reminders: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    process_reminders()
