# database/broadcast_crud.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .broadcast_models import BroadcastMessage, BroadcastLog
from .models import User
import logging
from datetime import datetime, timezone, timedelta
logger = logging.getLogger(__name__)


def create_broadcast_message(
        db: Session,
        message_type: str,
        content: Optional[str],
        media_file_id: Optional[str],
        media_type: Optional[str],
        created_by: int
) -> BroadcastMessage:
    """ایجاد پیام جدید برای ارسال"""
    broadcast = BroadcastMessage(
        message_type=message_type,
        content=content,
        media_file_id=media_file_id,
        media_type=media_type,
        created_by=created_by,
        is_completed=False
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    return broadcast


def get_broadcast_by_id(db: Session, broadcast_id: int) -> Optional[BroadcastMessage]:
    """دریافت پیام براساس ID"""
    return db.query(BroadcastMessage).filter(BroadcastMessage.id == broadcast_id).first()


def update_broadcast_stats(
        db: Session,
        broadcast_id: int,
        total_recipients: int,
        successful_sends: int,
        failed_sends: int
) -> Optional[BroadcastMessage]:
    """بروزرسانی آمار ارسال پیام"""
    broadcast = get_broadcast_by_id(db, broadcast_id)
    if broadcast:
        broadcast.total_recipients = total_recipients
        broadcast.successful_sends = successful_sends
        broadcast.failed_sends = failed_sends
        broadcast.is_completed = True
        db.commit()
        db.refresh(broadcast)
    return broadcast


def create_broadcast_log(
        db: Session,
        broadcast_message_id: int,
        customer_id: int,
        status: str,
        telegram_message_id: Optional[int] = None,
        error_message: Optional[str] = None
) -> BroadcastLog:
    """ثبت لاگ ارسال پیام به یک مشتری"""
    log = BroadcastLog(
        broadcast_message_id=broadcast_message_id,
        customer_id=customer_id,
        status=status,
        telegram_message_id=telegram_message_id,
        error_message=error_message
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_broadcast_logs(db: Session, broadcast_id: int, limit: int = 100) -> List[BroadcastLog]:
    """دریافت لاگ‌های ارسال یک پیام"""
    return db.query(BroadcastLog).filter(
        BroadcastLog.broadcast_message_id == broadcast_id
    ).order_by(desc(BroadcastLog.sent_at)).limit(limit).all()


def get_all_broadcasts(db: Session, limit: int = 50) -> List[BroadcastMessage]:
    """دریافت تمام پیام‌های ارسالی"""
    return db.query(BroadcastMessage).order_by(
        desc(BroadcastMessage.created_at)
    ).limit(limit).all()


def get_broadcasts_by_type(db: Session, message_type: str, limit: int = 50) -> List[BroadcastMessage]:
    """دریافت پیام‌های ارسالی براساس نوع"""
    return db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == message_type
    ).order_by(desc(BroadcastMessage.created_at)).limit(limit).all()


def get_broadcast_statistics(db: Session) -> dict:
    """دریافت آمار کلی ارسال پیام‌ها"""
    total_broadcasts = db.query(BroadcastMessage).count()
    promotional_count = db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == "promotional"
    ).count()
    occasional_count = db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == "occasional"
    ).count()

    total_sent = db.query(BroadcastLog).filter(
        BroadcastLog.status == "sent"
    ).count()
    total_failed = db.query(BroadcastLog).filter(
        BroadcastLog.status == "failed"
    ).count()

    return {
        'total_broadcasts': total_broadcasts,
        'promotional_count': promotional_count,
        'occasional_count': occasional_count,
        'total_sent': total_sent,
        'total_failed': total_failed
    }


def get_customer_broadcast_history(db: Session, customer_id: int, limit: int = 20) -> List[BroadcastLog]:
    """دریافت تاریخچه پیام‌های دریافتی یک مشتری"""
    return db.query(BroadcastLog).filter(
        BroadcastLog.customer_id == customer_id
    ).order_by(desc(BroadcastLog.sent_at)).limit(limit).all()


# database/broadcast_crud.py
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .broadcast_models import BroadcastMessage, BroadcastLog
from .models import User
import logging

logger = logging.getLogger(__name__)


def create_broadcast_message(
        db: Session,
        message_type: str,
        content: Optional[str],
        media_file_id: Optional[str],
        media_type: Optional[str],
        created_by: int,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None
) -> BroadcastMessage:
    """ایجاد پیام جدید برای ارسال"""
    broadcast = BroadcastMessage(
        message_type=message_type,
        content=content,
        media_file_id=media_file_id,
        media_type=media_type,
        created_by=created_by,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        is_completed=False
    )
    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)
    return broadcast


def get_broadcast_by_id(db: Session, broadcast_id: int) -> Optional[BroadcastMessage]:
    """دریافت پیام براساس ID"""
    return db.query(BroadcastMessage).filter(BroadcastMessage.id == broadcast_id).first()


def update_broadcast_stats(
        db: Session,
        broadcast_id: int,
        total_recipients: int,
        successful_sends: int,
        failed_sends: int
) -> Optional[BroadcastMessage]:
    """بروزرسانی آمار ارسال پیام"""
    broadcast = get_broadcast_by_id(db, broadcast_id)
    if broadcast:
        broadcast.total_recipients = total_recipients
        broadcast.successful_sends = successful_sends
        broadcast.failed_sends = failed_sends
        broadcast.is_completed = True
        db.commit()
        db.refresh(broadcast)
    return broadcast


def create_broadcast_log(
        db: Session,
        broadcast_message_id: int,
        customer_id: int,
        status: str,
        telegram_message_id: Optional[int] = None,
        error_message: Optional[str] = None
) -> BroadcastLog:
    """ثبت لاگ ارسال پیام به یک مشتری"""
    log = BroadcastLog(
        broadcast_message_id=broadcast_message_id,
        customer_id=customer_id,
        status=status,
        telegram_message_id=telegram_message_id,
        error_message=error_message
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_broadcast_logs(db: Session, broadcast_id: int, limit: int = 100) -> List[BroadcastLog]:
    """دریافت لاگ‌های ارسال یک پیام"""
    return db.query(BroadcastLog).filter(
        BroadcastLog.broadcast_message_id == broadcast_id
    ).order_by(desc(BroadcastLog.sent_at)).limit(limit).all()


def get_all_broadcasts(db: Session, limit: int = 50) -> List[BroadcastMessage]:
    """دریافت تمام پیام‌های ارسالی"""
    return db.query(BroadcastMessage).order_by(
        desc(BroadcastMessage.created_at)
    ).limit(limit).all()


def get_broadcasts_by_type(db: Session, message_type: str, limit: int = 50) -> List[BroadcastMessage]:
    """دریافت پیام‌های ارسالی براساس نوع"""
    return db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == message_type
    ).order_by(desc(BroadcastMessage.created_at)).limit(limit).all()


def get_broadcast_statistics(db: Session) -> dict:
    """دریافت آمار کلی ارسال پیام‌ها"""
    total_broadcasts = db.query(BroadcastMessage).count()
    promotional_count = db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == "promotional"
    ).count()
    occasional_count = db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == "occasional"
    ).count()

    total_sent = db.query(BroadcastLog).filter(
        BroadcastLog.status == "sent"
    ).count()
    total_failed = db.query(BroadcastLog).filter(
        BroadcastLog.status == "failed"
    ).count()

    return {
        'total_broadcasts': total_broadcasts,
        'promotional_count': promotional_count,
        'occasional_count': occasional_count,
        'total_sent': total_sent,
        'total_failed': total_failed
    }


def get_customer_broadcast_history(db: Session, customer_id: int, limit: int = 20) -> List[BroadcastLog]:
    """دریافت تاریخچه پیام‌های دریافتی یک مشتری"""
    return db.query(BroadcastLog).filter(
        BroadcastLog.customer_id == customer_id
    ).order_by(desc(BroadcastLog.sent_at)).limit(limit).all()


def get_active_discounts(db: Session) -> List[BroadcastMessage]:
    """
    دریافت تخفیف‌های مناسبتی فعال (که در بازه زمانی آنها هستیم)
    """
    from datetime import datetime, timezone, timedelta
    from utils.broadcast_utils import get_current_iran_time

    current_time = get_current_iran_time()

    return db.query(BroadcastMessage).filter(
        BroadcastMessage.message_type == "occasional",
        BroadcastMessage.start_datetime <= current_time,
        BroadcastMessage.end_datetime >= current_time,
        BroadcastMessage.is_completed == True
    ).all()


def get_discount_by_id(db: Session, discount_id: int) -> Optional[BroadcastMessage]:
    """دریافت یک تخفیف خاص با ID"""
    return db.query(BroadcastMessage).filter(
        BroadcastMessage.id == discount_id,
        BroadcastMessage.message_type == "occasional"
    ).first()


def is_discount_currently_active(db: Session, discount_id: int) -> bool:
    """بررسی اینکه آیا یک تخفیف در حال حاضر فعال است"""
    from utils.broadcast_utils import get_current_iran_time

    discount = get_discount_by_id(db, discount_id)
    if not discount or not discount.start_datetime or not discount.end_datetime:
        return False

    current_time = get_current_iran_time()
    return discount.start_datetime <= current_time <= discount.end_datetime