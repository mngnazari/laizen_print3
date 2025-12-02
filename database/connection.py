# database/connection.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import contextlib

# برای تست محلی با SQLite
DATABASE_URL = 'sqlite:///print3d_orders.db'

engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """یک سشن دیتابیس جدید ایجاد و پس از اتمام کار آن را می‌بندد."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextlib.contextmanager
def get_db_context():
    """Context manager برای دیتابیس."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()