# utils/referral.py
import secrets
import string
from typing import Optional, List


def extract_referral_code(args: Optional[List[str]]) -> Optional[str]:
    """
    کد رفرال را از پارامترهای /start استخراج می‌کند

    Args:
        args: لیست آرگومان‌های دستور start (context.args)

    Returns:
        کد رفرال یا None
    """
    if args and len(args) > 0:
        referral_code = args[0].strip()

        # بررسی اعتبار کد (فقط حروف و اعداد، حداکثر 10 کاراکتر)
        if referral_code.isalnum() and len(referral_code) <= 10:
            return referral_code

    return None


def generate_referral_code(length: int = 8) -> str:
    """
    تولید کد رفرال تصادفی

    Args:
        length: طول کد (پیش‌فرض 8)

    Returns:
        کد رفرال تولید شده
    """
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for i in range(length))


def create_referral_link(bot_username: str, referral_code: str) -> str:
    """
    لینک دعوت را ایجاد می‌کند

    Args:
        bot_username: نام کاربری بات (بدون @)
        referral_code: کد رفرال

    Returns:
        لینک کامل دعوت
    """
    return f"https://t.me/{bot_username}?start={referral_code}"


def validate_referral_code_format(code: str) -> bool:
    """
    فرمت کد رفرال را بررسی می‌کند

    Args:
        code: کد رفرال

    Returns:
        True اگر فرمت صحیح باشد
    """
    if not code or not isinstance(code, str):
        return False

    # فقط حروف و اعداد، بین 4 تا 10 کاراکتر
    return code.isalnum() and 4 <= len(code) <= 10


def get_persian_datetime() -> str:
    """
    تاریخ و زمان فعلی به شمسی برمی‌گرداند

    Returns:
        رشته تاریخ و زمان فارسی
    """
    from datetime import datetime
    import jdatetime

    try:
        now = jdatetime.datetime.now()
        return now.strftime('%Y/%m/%d - %H:%M')
    except ImportError:
        # اگر jdatetime نصب نباشد، از datetime عادی استفاده کن
        now = datetime.now()
        return now.strftime('%Y-%m-%d %H:%M')
    except:
        return "نامشخص"