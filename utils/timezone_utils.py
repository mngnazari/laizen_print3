"""
ماژول مرکزی برای مدیریت timezone و تاریخ

این ماژول تمام عملیات مربوط به timezone و تبدیل تاریخ را مدیریت می‌کند.
رویکرد: همه datetime‌ها در UTC ذخیره می‌شوند و فقط برای نمایش به زمان ایران تبدیل می‌شوند.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
import jdatetime

# تعریف timezone ایران (UTC+3:30)
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def now_utc() -> datetime:
    """
    دریافت زمان فعلی UTC (naive datetime برای ذخیره در SQLite)

    Returns:
        datetime: زمان فعلی UTC بدون timezone info
    """
    return datetime.utcnow()


def now_iran() -> datetime:
    """
    دریافت زمان فعلی ایران (naive datetime با مقدار ایران)

    Returns:
        datetime: زمان فعلی ایران بدون timezone info
    """
    utc_now = datetime.now(timezone.utc)
    iran_now = utc_now.astimezone(IRAN_TZ)
    return iran_now.replace(tzinfo=None)


def utc_to_iran(dt: datetime) -> datetime:
    """
    تبدیل datetime از UTC به زمان ایران

    Args:
        dt: datetime object (می‌تواند naive یا timezone-aware باشد)

    Returns:
        datetime: زمان ایران به صورت naive
    """
    if dt is None:
        return None

    # اگر naive است، فرض می‌کنیم UTC است
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # تبدیل به UTC اگر timezone دیگری دارد
        dt = dt.astimezone(timezone.utc)

    # تبدیل به timezone ایران
    iran_dt = dt.astimezone(IRAN_TZ)

    # برگرداندن به صورت naive
    return iran_dt.replace(tzinfo=None)


def iran_to_utc(dt: datetime) -> datetime:
    """
    تبدیل datetime از زمان ایران به UTC

    Args:
        dt: datetime object با مقدار زمان ایران (naive)

    Returns:
        datetime: زمان UTC به صورت naive
    """
    if dt is None:
        return None

    # فرض می‌کنیم dt به زمان ایران است
    iran_dt = dt.replace(tzinfo=IRAN_TZ)

    # تبدیل به UTC
    utc_dt = iran_dt.astimezone(timezone.utc)

    # برگرداندن به صورت naive
    return utc_dt.replace(tzinfo=None)


def format_shamsi(dt: datetime, include_time: bool = True) -> str:
    """
    فرمت کردن datetime به تاریخ شمسی

    Args:
        dt: datetime object (فرض می‌شود UTC است)
        include_time: آیا ساعت هم نمایش داده شود؟

    Returns:
        str: تاریخ شمسی فرمت شده (مثل "1404/07/18" یا "1404/07/18 - 14:30")
    """
    if dt is None:
        return "نامشخص"

    try:
        # تبدیل به زمان ایران
        iran_dt = utc_to_iran(dt)

        # تبدیل به تاریخ شمسی
        jdate = jdatetime.datetime.fromgregorian(datetime=iran_dt)

        if include_time:
            return jdate.strftime('%Y/%m/%d - %H:%M')
        else:
            return jdate.strftime('%Y/%m/%d')

    except Exception as e:
        print(f"خطا در فرمت تاریخ شمسی: {e}")
        return "نامشخص"


def format_shamsi_short(dt: datetime) -> str:
    """
    فرمت کوتاه تاریخ شمسی (مثل "07/18-14:30")

    Args:
        dt: datetime object (فرض می‌شود UTC است)

    Returns:
        str: تاریخ شمسی کوتاه
    """
    if dt is None:
        return "نامشخص"

    try:
        # تبدیل به زمان ایران
        iran_dt = utc_to_iran(dt)

        # تبدیل به تاریخ شمسی
        jdate = jdatetime.datetime.fromgregorian(datetime=iran_dt)

        return jdate.strftime('%m/%d-%H:%M')

    except Exception as e:
        print(f"خطا در فرمت تاریخ شمسی: {e}")
        return "نامشخص"


def parse_shamsi_datetime(date_str: str, time_str: str) -> Optional[datetime]:
    """
    تبدیل تاریخ و ساعت شمسی به datetime UTC

    Args:
        date_str: تاریخ به فرمت "1404/07/18" یا "1404-07-18"
        time_str: ساعت به فرمت "14:30"

    Returns:
        datetime: زمان UTC به صورت naive
    """
    try:
        # جدا کردن اجزای تاریخ (پشتیبانی از / و -)
        date_str = date_str.replace('-', '/')
        year, month, day = map(int, date_str.split('/'))
        hour, minute = map(int, time_str.split(':'))

        # ایجاد تاریخ شمسی
        jdate = jdatetime.datetime(year, month, day, hour, minute, 0)

        # تبدیل به میلادی (زمان ایران)
        iran_dt = jdate.togregorian()

        # تبدیل به UTC
        return iran_to_utc(iran_dt)

    except Exception as e:
        print(f"خطا در parse تاریخ شمسی: {e}")
        return None


def format_time_only(dt: datetime) -> str:
    """
    فقط ساعت را برمی‌گرداند (مثل "14:30")

    Args:
        dt: datetime object (فرض می‌شود UTC است)

    Returns:
        str: ساعت فرمت شده
    """
    if dt is None:
        return ""

    try:
        # تبدیل به زمان ایران
        iran_dt = utc_to_iran(dt)

        return iran_dt.strftime('%H:%M')

    except Exception as e:
        print(f"خطا در فرمت ساعت: {e}")
        return ""


def get_current_iran_time_aware() -> datetime:
    """
    دریافت زمان فعلی با timezone ایران (timezone-aware)

    این تابع برای موارد خاصی که timezone-aware datetime نیاز است

    Returns:
        datetime: زمان فعلی ایران با timezone info
    """
    return datetime.now(IRAN_TZ)


def validate_datetime_range(start_dt: datetime, end_dt: datetime) -> tuple[bool, str]:
    """
    اعتبارسنجی بازه زمانی

    Args:
        start_dt: زمان شروع (UTC)
        end_dt: زمان پایان (UTC)

    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    current_time = now_utc()

    # چک کردن که زمان شروع در گذشته نباشد
    if start_dt < current_time:
        return False, "زمان شروع نمی‌تواند در گذشته باشد"

    # چک کردن که زمان پایان بعد از شروع باشد
    if end_dt <= start_dt:
        return False, "زمان پایان باید بعد از زمان شروع باشد"

    # چک کردن حداقل مدت زمان (مثلاً 1 ساعت)
    if (end_dt - start_dt).total_seconds() < 3600:
        return False, "حداقل مدت زمان باید 1 ساعت باشد"

    return True, ""


def is_time_in_range(start_dt: datetime, end_dt: datetime) -> bool:
    """
    بررسی اینکه آیا زمان فعلی در بازه مشخص شده است

    Args:
        start_dt: زمان شروع (UTC)
        end_dt: زمان پایان (UTC)

    Returns:
        bool: True اگر زمان فعلی در بازه باشد
    """
    current_time = now_utc()
    return start_dt <= current_time <= end_dt
