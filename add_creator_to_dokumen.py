import psycopg2
from database import DATABASE_URL

def migrate():
    print("Starting manual migration: Adding creator_user_id to dokumen...")
    try:
        # Parse connection string
        # DATABASE_URL = "postgresql://postgres:password@localhost:5432/sinergi_db"
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # 1. Add column
        print("Adding column creator_user_id to table 'dokumen'...")
        cur.execute("ALTER TABLE dokumen ADD COLUMN IF NOT EXISTS creator_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;")
        
        # 2. Populate old data (Optional: Try to link to activity creator if available)
        print("Populating creator_user_id for existing documents from activity creators...")
        cur.execute("""
            UPDATE dokumen d
            SET creator_user_id = a.creator_user_id
            FROM aktivitas a
            WHERE d.aktivitas_id = a.id AND d.creator_user_id IS NULL;
        """)

        conn.commit()
        cur.close()
        conn.close()
        print("Migration successful! ✅")
    except Exception as e:
        print(f"Migration failed: {e} ❌")

if __name__ == "__main__":
    migrate()
