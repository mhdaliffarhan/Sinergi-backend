from database import SessionLocal
import models
from sqlalchemy import create_engine

def check():
    try:
        # This will trigger mapper initialization
        from sqlalchemy.orm import configure_mappers
        configure_mappers()
        print("Mappers initialized successfully!")
        
        db = SessionLocal()
        print("Database session created successfully!")
        db.close()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check()
