# database/create_editor_tables.py
"""اسکریپت ایجاد جداول جدید ادیتور"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

# Import کردن مدل‌های جدید
from .editor_models import EditorWorkSession, EditorOriginalFile, EditorFileMapping, ProcessedFile
from .connection import Base, DATABASE_URL

logger = logging.getLogger(__name__)


def create_editor_tables():
    """ایجاد جداول جدید ادیتور"""
    try:
        engine = create_engine(DATABASE_URL)

        # ایجاد جداول جدید
        logger.info("شروع ایجاد جداول ادیتور...")

        # ایجاد جداول بر اساس مدل‌ها
        Base.metadata.create_all(bind=engine, tables=[
            EditorWorkSession.__table__,
            EditorOriginalFile.__table__,
            EditorFileMapping.__table__,
            ProcessedFile.__table__
        ])

        logger.info("جداول ادیتور با موفقیت ایجاد شدند")
        return True

    except Exception as e:
        logger.error(f"خطا در ایجاد جداول ادیتور: {e}")
        return False


def update_file_orders_table():
    """به‌روزرسانی جدول file_orders برای اضافه کردن ستون‌های مربوط به ادیتور"""
    try:
        engine = create_engine(DATABASE_URL)

        with engine.connect() as connection:
            # بررسی وجود ستون‌های جدید و اضافه کردن آنها در صورت عدم وجود
            logger.info("بررسی و اضافه کردن ستون‌های جدید به file_orders...")

            # اضافه کردن ستون‌های مربوط به ادیتور
            try:
                connection.execute("ALTER TABLE file_orders ADD COLUMN assigned_editor_id BIGINT")
                logger.info("ستون assigned_editor_id اضافه شد")
            except Exception:
                logger.info("ستون assigned_editor_id از قبل وجود دارد")

            try:
                connection.execute("ALTER TABLE file_orders ADD COLUMN editor_status VARCHAR DEFAULT 'pending'")
                logger.info("ستون editor_status اضافه شد")
            except Exception:
                logger.info("ستون editor_status از قبل وجود دارد")

            try:
                connection.execute("ALTER TABLE file_orders ADD COLUMN editor_assigned_at TIMESTAMP")
                logger.info("ستون editor_assigned_at اضافه شد")
            except Exception:
                logger.info("ستون editor_assigned_at از قبل وجود دارد")

            try:
                connection.execute("ALTER TABLE file_orders ADD COLUMN editor_notes TEXT")
                logger.info("ستون editor_notes اضافه شد")
            except Exception:
                logger.info("ستون editor_notes از قبل وجود دارد")

        return True

    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی جدول file_orders: {e}")
        return False


if __name__ == "__main__":
    """اجرای مستقل برای ایجاد جداول"""
    logging.basicConfig(level=logging.INFO)

    print("شروع ایجاد جداول ادیتور...")

    # ایجاد جداول جدید
    if create_editor_tables():
        print("✅ جداول جدید ادیتور ایجاد شدند")
    else:
        print("❌ خطا در ایجاد جداول جدید")
        exit(1)

    # به‌روزرسانی جدول موجود
    if update_file_orders_table():
        print("✅ جدول file_orders به‌روزرسانی شد")
    else:
        print("❌ خطا در به‌روزرسانی جدول file_orders")
        exit(1)

    print("🎉 همه تغییرات دیتابیس با موفقیت اعمال شدند!")