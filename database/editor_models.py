# database/editor_models.py
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import relationship, Mapped
from .connection import Base


class EditorWorkSession(Base):
    """جلسه کاری ادیتور - مدیریت وضعیت و فایل‌های در دست کار"""
    __tablename__ = "editor_work_sessions"

    id = Column(Integer, primary_key=True, index=True)
    editor_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False, default="idle")  # idle, working, completed
    original_file_count = Column(Integer, default=0)  # تعداد فایل‌های اصلی دریافتی
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    mapping_received_at = Column(DateTime, nullable=True)  # زمان دریافت فایل نقشه
    completed_at = Column(DateTime, nullable=True)  # زمان تکمیل همه فایل‌ها

    # روابط
    editor: Mapped["User"] = relationship("User", foreign_keys=[editor_id])
    original_files: Mapped[list["EditorOriginalFile"]] = relationship("EditorOriginalFile", back_populates="session",
                                                                      cascade="all, delete-orphan")
    file_mapping: Mapped["EditorFileMapping"] = relationship("EditorFileMapping", back_populates="session",
                                                             uselist=False, cascade="all, delete-orphan")


class EditorOriginalFile(Base):
    """فایل‌های اصلی که ادیتور دریافت کرده"""
    __tablename__ = "editor_original_files"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("editor_work_sessions.id"), nullable=False)
    file_order_id = Column(Integer, ForeignKey("file_orders.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    file_id = Column(String, nullable=False)  # Telegram File ID
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    session: Mapped["EditorWorkSession"] = relationship("EditorWorkSession", back_populates="original_files")
    file_order: Mapped["FileOrder"] = relationship("FileOrder")
    processed_files: Mapped[list["ProcessedFile"]] = relationship("ProcessedFile", back_populates="original_file",
                                                                  cascade="all, delete-orphan")


class EditorFileMapping(Base):
    """نقشه تبدیل فایل‌های اصلی به فایل‌های نهایی"""
    __tablename__ = "editor_file_mappings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("editor_work_sessions.id"), nullable=False)
    mapping_content = Column(Text, nullable=False)  # محتوای فایل نقشه
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    session: Mapped["EditorWorkSession"] = relationship("EditorWorkSession", back_populates="file_mapping")


class ProcessedFile(Base):
    """فایل‌های پردازش شده که باید از ادیتور دریافت شوند"""
    __tablename__ = "processed_files"

    id = Column(Integer, primary_key=True, index=True)
    original_file_id = Column(Integer, ForeignKey("editor_original_files.id"), nullable=False)
    original_filename = Column(String, nullable=False)  # نام فایل اصلی (مبدا)
    processed_filename = Column(String, nullable=False)  # نام فایل پردازش شده (مقصد)

    # فایل‌های مورد نیاز
    stl_required = Column(Boolean, default=True)  # آیا فایل STL مورد نیاز است
    jpg_required = Column(Boolean, default=True)  # آیا فایل JPG مورد نیاز است
    zip_required = Column(Boolean, default=True)  # آیا فایل ZIP مورد نیاز است

    # فایل‌های دریافت شده
    stl_file_id = Column(String, nullable=True)  # Telegram File ID فایل STL
    jpg_file_id = Column(String, nullable=True)  # Telegram File ID فایل JPG
    zip_file_id = Column(String, nullable=True)  # Telegram File ID فایل ZIP

    # وضعیت
    stl_received = Column(Boolean, default=False)
    jpg_received = Column(Boolean, default=False)
    zip_received = Column(Boolean, default=False)
    is_completed = Column(Boolean, default=False)  # آیا همه فایل‌های مورد نیاز دریافت شده

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    stl_received_at = Column(DateTime, nullable=True)
    jpg_received_at = Column(DateTime, nullable=True)
    zip_received_at = Column(DateTime, nullable=True)

    # روابط
    original_file: Mapped["EditorOriginalFile"] = relationship("EditorOriginalFile", back_populates="processed_files")

# اضافه کردن Import به فایل models.py اصلی
# این خط را به انتهای فایل database/models.py اضافه کنید:
# from .editor_models import EditorWorkSession, EditorOriginalFile, EditorFileMapping, ProcessedFile