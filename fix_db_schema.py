from database import engine
from sqlalchemy import text

def update_schema():
    with engine.connect() as conn:
        print("--- Memulai Update Skema Database ---")
        
        # 1. Tambah kolom scheduled_at ke wa_queue
        try:
            conn.execute(text("ALTER TABLE wa_queue ADD COLUMN scheduled_at TIMESTAMP WITH TIME ZONE"))
            conn.commit()
            print("[OK] Kolom 'scheduled_at' berhasil ditambahkan ke 'wa_queue'")
        except Exception as e:
            if "already exists" in str(e):
                print("[SKIP] Kolom 'scheduled_at' sudah ada.")
            else:
                print(f"[ERROR] Gagal menambah 'scheduled_at': {e}")

        # 2. Tambah kolom aktivitas_id ke wa_queue
        try:
            conn.execute(text("ALTER TABLE wa_queue ADD COLUMN aktivitas_id INTEGER REFERENCES aktivitas(id) ON DELETE CASCADE"))
            conn.commit()
            print("[OK] Kolom 'aktivitas_id' berhasil ditambahkan ke 'wa_queue'")
        except Exception as e:
            if "already exists" in str(e):
                print("[SKIP] Kolom 'aktivitas_id' sudah ada.")
            else:
                print(f"[ERROR] Gagal menambah 'aktivitas_id': {e}")
        
        print("--- Update Skema Selesai ---")

if __name__ == "__main__":
    update_schema()
