# utils/broadcast_utils.py
"""توابع کمکی برای سیستم broadcast"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import jdatetime

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def parse_shamsi_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    تبدیل تاریخ و ساعت شمسی به datetime با timezone ایران

    Args:
        date_str: تاریخ به فرمت "1404/07/18" یا "1404-07-18"
        time_str: ساعت به فرمت "14:30"

    Returns:
        datetime object با timezone ایران یا None در صورت خطا
    """
    try:
        # جدا کردن اجزای تاریخ (پشتیبانی از / و -)
        date_str = date_str.replace('-', '/')
        year, month, day = map(int, date_str.split('/'))
        hour, minute = map(int, time_str.split(':'))

        # ایجاد تاریخ شمسی
        jdate = jdatetime.datetime(year, month, day, hour, minute, 0)

        # تبدیل به میلادی
        gdate = jdate.togregorian()

        # اضافه کردن timezone ایران
        iran_datetime = gdate.replace(tzinfo=IRAN_TZ)

        return iran_datetime

    except Exception as e:
        print(f"خطا در parse تاریخ: {e}")
        return None


def format_shamsi_datetime(dt: datetime) -> str:
    """
    فرمت کردن datetime به نمایش شمسی

    Args:
        dt: datetime object

    Returns:
        رشته فرمت شده مثل "1404/07/18 - 14:30"
    """
    if not dt:
        return "تنظیم نشده"

    try:
        # تبدیل به timezone ایران اگر نیست
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        iran_dt = dt.astimezone(IRAN_TZ)

        # تبدیل به شمسی
        jdate = jdatetime.datetime.fromgregorian(datetime=iran_dt)

        return jdate.strftime('%Y/%m/%d - %H:%M')

    except Exception as e:
        print(f"خطا در فرمت تاریخ: {e}")
        return "نامشخص"


def get_current_iran_time() -> datetime:
    """
    دریافت زمان فعلی با timezone ایران

    Returns:
        datetime object با timezone ایران
    """
    return datetime.now(IRAN_TZ)


def validate_datetime_range(start_dt: datetime, end_dt: datetime) -> Tuple[bool, str]:
    """
    اعتبارسنجی بازه زمانی

    Args:
        start_dt: زمان شروع
        end_dt: زمان پایان

    Returns:
        (is_valid, error_message)
    """
    current_time = get_current_iran_time()

    # چک کردن که زمان شروع در گذشته نباشد
    if start_dt < current_time:
        return False, "زمان شروع نمی‌تواند در گذشته باشد"

    # چک کردن که زمان پایان بعد از شروع باشد
    if end_dt <= start_dt:
        return False, "زمان پایان باید بعد از زمان شروع باشد"

    # چک کردن حداقل مدت زمان (مثلاً 1 ساعت)
    if (end_dt - start_dt).total_seconds() < 3600:
        return False, "حداقل مدت زمان تخفیف باید 1 ساعت باشد"

    return True, ""


def is_discount_active(start_dt: datetime, end_dt: datetime) -> bool:
    """
    بررسی اینکه آیا تخفیف در حال حاضر فعال است

    Args:
        start_dt: زمان شروع تخفیف
        end_dt: زمان پایان تخفیف

    Returns:
        True اگر تخفیف فعال باشد
    """
    current_time = get_current_iran_time()
    return start_dt <= current_time <= end_dt


def format_shamsi_date_only(dt: datetime) -> str:
    """
    فقط تاریخ شمسی بدون ساعت

    Returns:
        مثل "1404/07/18"
    """
    if not dt:
        return ""

    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        iran_dt = dt.astimezone(IRAN_TZ)
        jdate = jdatetime.datetime.fromgregorian(datetime=iran_dt)

        return jdate.strftime('%Y/%m/%d')

    except Exception as e:
        return ""


def format_time_only(dt: datetime) -> str:
    """
    فقط ساعت

    Returns:
        مثل "14:30"
    """
    if not dt:
        return ""

    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        iran_dt = dt.astimezone(IRAN_TZ)

        return iran_dt.strftime('%H:%M')

    except Exception as e:
        return ""