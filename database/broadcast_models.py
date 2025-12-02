# database/broadcast_models.py
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, func, Text, Boolean
from sqlalchemy.orm import relationship, Mapped
from .connection import Base


class BroadcastMessage(Base):
    """جدول پیام‌های ارسالی (تبلیغاتی یا تخفیف مناسبتی)"""
    __tablename__ = "broadcast_messages"

    id = Column(Integer, primary_key=True, index=True)
    message_type = Column(String, nullable=False)  # "promotional" یا "occasional"
    content = Column(Text, nullable=True)  # متن پیام (اختیاری اگر فقط مدیا باشد)
    media_file_id = Column(String, nullable=True)  # File ID تلگرام (عکس/ویدیو/صوت/سند)
    media_type = Column(String, nullable=True)  # "photo", "video", "audio", "voice", "document"

    # فیلدهای جدید برای تخفیف مناسبتی
    start_datetime = Column(DateTime(timezone=True), nullable=True)  # تاریخ و ساعت شروع تخفیف
    end_datetime = Column(DateTime(timezone=True), nullable=True)  # تاریخ و ساعت پایان تخفیف

    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    total_recipients = Column(Integer, default=0)  # تعداد کل گیرندگان
    successful_sends = Column(Integer, default=0)  # تعداد ارسال موفق
    failed_sends = Column(Integer, default=0)  # تعداد ارسال ناموفق
    is_completed = Column(Boolean, default=False)  # آیا ارسال کامل شده

    # روابط
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    logs: Mapped[list["BroadcastLog"]] = relationship("BroadcastLog", back_populates="broadcast_message")


class BroadcastLog(Base):
    """جدول لاگ ارسال پیام به هر مشتری"""
    __tablename__ = "broadcast_logs"

    id = Column(Integer, primary_key=True, index=True)
    broadcast_message_id = Column(Integer, ForeignKey("broadcast_messages.id"), nullable=False)
    customer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(String, nullable=False)  # "sent", "failed", "blocked"
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
    error_message = Column(Text, nullable=True)  # در صورت خطا
    telegram_message_id = Column(Integer, nullable=True)  # شناسه پیام ارسالی در تلگرام

    # روابط
    broadcast_message: Mapped["BroadcastMessage"] = relationship("BroadcastMessage", back_populates="logs")
    customer: Mapped["User"] = relationship("User", foreign_keys=[customer_id])