# utils/broadcast_utils.py
"""
توابع کمکی برای سیستم broadcast

این فایل deprecated شده و تمام توابع آن به timezone_utils منتقل شده‌اند.
برای backward compatibility نگه داشته شده است.
"""
from datetime import datetime
from typing import Optional, Tuple

# Import از ماژول مرکزی
from utils.timezone_utils import (
    parse_shamsi_datetime,
    format_shamsi,
    now_utc,
    validate_datetime_range,
    is_time_in_range,
    format_time_only
)


def format_shamsi_datetime(dt: datetime) -> str:
    """
    فرمت کردن datetime به نمایش شمسی (wrapper برای backward compatibility)
    """
    return format_shamsi(dt, include_time=True)


def get_current_iran_time() -> datetime:
    """
    دریافت زمان فعلی UTC (wrapper برای backward compatibility)
    """
    return now_utc()


def is_discount_active(start_dt: datetime, end_dt: datetime) -> bool:
    """
    بررسی اینکه آیا تخفیف در حال حاضر فعال است (wrapper)
    """
    return is_time_in_range(start_dt, end_dt)


def format_shamsi_date_only(dt: datetime) -> str:
    """
    فقط تاریخ شمسی بدون ساعت (wrapper)
    """
    return format_shamsi(dt, include_time=False)