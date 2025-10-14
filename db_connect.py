# db_connect.py
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    db_url = os.getenv("DB_URL")
    if not db_url:
        raise ValueError("❌ DB_URL not found in .env file")

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            print("✅ Database connection successful!")
        return engine
    except Exception as e:
        raise RuntimeError(f"❌ Database connection failed: {e}")
