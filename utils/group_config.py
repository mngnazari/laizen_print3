# utils/group_config.py
from typing import Dict, Optional
from sqlalchemy.orm import Session
import database.crud


class GroupDiscountConfig:
    """مدیریت تنظیمات تخفیف گروهی"""

    # کلیدهای تنظیمات در دیتابیس
    DAILY_THRESHOLD_KEY = "group_discount_daily_threshold"
    DISCOUNT_RATES_KEY = "group_discount_rates"
    FEATURE_ENABLED_KEY = "group_discount_enabled"

    @classmethod
    def get_daily_threshold(cls, db: Session) -> int:
        """دریافت حد نصاب روزانه فایل برای تخفیف"""
        threshold = database.crud.get_system_setting(
            db, cls.DAILY_THRESHOLD_KEY, "10"
        )
        return int(threshold)

    @classmethod
    def set_daily_threshold(cls, db: Session, threshold: int) -> None:
        """تنظیم حد نصاب روزانه فایل"""
        database.crud.set_system_setting(
            db,
            cls.DAILY_THRESHOLD_KEY,
            str(threshold),
            f"حداقل تعداد فایل روزانه گروه برای کسب تخفیف: {threshold}"
        )

    @classmethod
    def get_discount_rates(cls, db: Session) -> Dict[int, int]:
        """دریافت نرخ‌های تخفیف بر اساس روزهای فعال"""
        rates_str = database.crud.get_system_setting(
            db, cls.DISCOUNT_RATES_KEY, "1:5,3:10,5:15,7:20"
        )

        rates = {}
        try:
            for rate_pair in rates_str.split(','):
                days, percentage = rate_pair.split(':')
                rates[int(days)] = int(percentage)
        except (ValueError, IndexError):
            # در صورت خطا، مقادیر پیش‌فرض
            rates = {1: 5, 3: 10, 5: 15, 7: 20}

        return rates

    @classmethod
    def set_discount_rates(cls, db: Session, rates: Dict[int, int]) -> None:
        """تنظیم نرخ‌های تخفیف"""
        rates_str = ','.join([f"{days}:{percentage}" for days, percentage in rates.items()])
        database.crud.set_system_setting(
            db,
            cls.DISCOUNT_RATES_KEY,
            rates_str,
            "نرخ تخفیف گروهی بر اساس روزهای فعال"
        )

    @classmethod
    def is_feature_enabled(cls, db: Session) -> bool:
        """بررسی فعال بودن قابلیت تخفیف گروهی"""
        enabled = database.crud.get_system_setting(
            db, cls.FEATURE_ENABLED_KEY, "true"
        )
        return enabled.lower() == "true"

    @classmethod
    def enable_feature(cls, db: Session, enabled: bool = True) -> None:
        """فعال/غیرفعال کردن قابلیت تخفیف گروهی"""
        database.crud.set_system_setting(
            db,
            cls.FEATURE_ENABLED_KEY,
            "true" if enabled else "false",
            "وضعیت فعال/غیرفعال بودن سیستم تخفیف گروهی"
        )

    @classmethod
    def get_all_settings(cls, db: Session) -> Dict:
        """دریافت تمام تنظیمات تخفیف گروهی"""
        return {
            'daily_threshold': cls.get_daily_threshold(db),
            'discount_rates': cls.get_discount_rates(db),
            'feature_enabled': cls.is_feature_enabled(db)
        }

    @classmethod
    def reset_to_defaults(cls, db: Session) -> None:
        """بازنشانی تنظیمات به مقادیر پیش‌فرض"""
        cls.set_daily_threshold(db, 10)
        cls.set_discount_rates(db, {1: 5, 3: 10, 5: 15, 7: 20})
        cls.enable_feature(db, True)


def validate_discount_rates(rates: Dict[int, int]) -> bool:
    """اعتبارسنجی نرخ‌های تخفیف"""
    if not rates:
        return False

    for days, percentage in rates.items():
        # بررسی مقادیر منطقی
        if not (1 <= days <= 7):
            return False
        if not (0 <= percentage <= 100):
            return False

    return True


def format_discount_config_message(db: Session) -> str:
    """فرمت کردن پیام تنظیمات تخفیف گروهی"""
    config = GroupDiscountConfig.get_all_settings(db)

    message = "⚙️ **تنظیمات فعلی تخفیف گروهی:**\n\n"

    status = "✅ فعال" if config['feature_enabled'] else "❌ غیرفعال"
    message += f"🔘 وضعیت: {status}\n"
    message += f"📊 حد نصاب روزانه: {config['daily_threshold']} فایل\n\n"

    message += "💰 **نرخ تخفیف‌ها:**\n"
    for days, percentage in sorted(config['discount_rates'].items()):
        message += f"   {days} روز فعال = {percentage}% تخفیف\n"

    return message