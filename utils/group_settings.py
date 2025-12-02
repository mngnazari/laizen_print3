# utils/group_settings.py
from sqlalchemy.orm import Session
import database.crud


class GroupLevelSettings:
    """مدیریت تنظیمات سطح‌بندی گروه"""

    @classmethod
    def get_settings(cls, db: Session) -> dict:
        """دریافت تنظیمات فعلی"""
        return {
            'silver_threshold': float(database.crud.get_system_setting(db, "group_silver_threshold", "50")),
            'gold_threshold': float(database.crud.get_system_setting(db, "group_gold_threshold", "100")),
            'silver_discount': float(database.crud.get_system_setting(db, "group_silver_discount", "5")),
            'gold_discount': float(database.crud.get_system_setting(db, "group_gold_discount", "10"))
        }

    @classmethod
    def update_settings(cls, db: Session, settings: dict):
        """بروزرسانی تنظیمات"""
        database.crud.set_system_setting(db, "group_silver_threshold", str(settings['silver_threshold']))
        database.crud.set_system_setting(db, "group_gold_threshold", str(settings['gold_threshold']))
        database.crud.set_system_setting(db, "group_silver_discount", str(settings['silver_discount']))
        database.crud.set_system_setting(db, "group_gold_discount", str(settings['gold_discount']))

    @classmethod
    def get_group_level(cls, db: Session, daily_average: float) -> tuple:
        """تعیین سطح گروه بر اساس میانگین روزانه"""
        settings = cls.get_settings(db)

        if daily_average >= settings['gold_threshold']:
            return ("طلایی", "🥇", settings['gold_discount'])
        elif daily_average >= settings['silver_threshold']:
            return ("نقره‌ای", "🥈", settings['silver_discount'])
        else:
            return ("برنزی", "🥉", 0)