# utils/discount_calculator.py
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session

from database.group_crud import check_group_discount_eligibility_advanced
import database.crud


class GroupDiscountCalculator:
    """کلاس محاسبه تخفیف گروهی"""

    # تنظیمات پیش‌فرض
    DEFAULT_DAILY_THRESHOLD = 10  # حداقل فایل در روز
    DISCOUNT_RATES = {
        1: 5,  # 1 روز واجد شرایط = 5%
        3: 10,  # 3 روز واجد شرایط = 10%
        5: 15,  # 5 روز واجد شرایط = 15%
        7: 20  # 7 روز واجد شرایط = 20%
    }

    @classmethod
    def calculate_weekly_discount(cls, db: Session, user_id: int,
                                  threshold: Optional[int] = None) -> Dict:
        """محاسبه تخفیف هفتگی بر اساس عملکرد گروه"""
        if threshold is None:
            threshold = cls.DEFAULT_DAILY_THRESHOLD

        eligibility_data = check_group_discount_eligibility_advanced(
            db, user_id, threshold
        )

        eligible_days = eligibility_data['eligible_days']

        # تعیین درصد تخفیف
        discount_percentage = 0
        for required_days in sorted(cls.DISCOUNT_RATES.keys(), reverse=True):
            if eligible_days >= required_days:
                discount_percentage = cls.DISCOUNT_RATES[required_days]
                break

        return {
            'eligible_days': eligible_days,
            'total_days': 7,
            'discount_percentage': discount_percentage,
            'is_eligible': eligible_days > 0,
            'threshold_used': threshold,
            'weekly_details': eligibility_data['weekly_stats']
        }

    @classmethod
    def apply_group_discount(cls, db: Session, user_id: int,
                             base_amount: float) -> Dict:
        """اعمال تخفیف گروهی به مبلغ"""
        discount_info = cls.calculate_weekly_discount(db, user_id)

        if not discount_info['is_eligible']:
            return {
                'original_amount': base_amount,
                'discount_amount': 0,
                'final_amount': base_amount,
                'discount_percentage': 0,
                'applied': False
            }

        discount_percentage = discount_info['discount_percentage']
        discount_amount = (base_amount * discount_percentage) / 100
        final_amount = base_amount - discount_amount

        return {
            'original_amount': base_amount,
            'discount_amount': discount_amount,
            'final_amount': final_amount,
            'discount_percentage': discount_percentage,
            'applied': True,
            'eligible_days': discount_info['eligible_days']
        }

    @classmethod
    def get_discount_status_message(cls, db: Session, user_id: int) -> str:
        """پیام وضعیت تخفیف گروهی"""
        discount_info = cls.calculate_weekly_discount(db, user_id)

        if discount_info['is_eligible']:
            message = f"🎉 تبریک! گروه شما واجد شرایط تخفیف است:\n"
            message += f"✅ روزهای واجد شرایط: {discount_info['eligible_days']}/7\n"
            message += f"💰 درصد تخفیف: {discount_info['discount_percentage']}%\n"
        else:
            message = f"⏳ گروه شما هنوز واجد شرایط تخفیف نیست:\n"
            message += f"❌ روزهای واجد شرایط: {discount_info['eligible_days']}/7\n"
            message += f"📈 برای کسب تخفیف، گروه شما باید در روز حداقل "
            message += f"{cls.DEFAULT_DAILY_THRESHOLD} فایل ارسال کند.\n"

        return message

    @classmethod
    def get_next_discount_tier_info(cls, db: Session, user_id: int) -> Optional[Dict]:
        """اطلاعات مرحله بعدی تخفیف"""
        current_discount = cls.calculate_weekly_discount(db, user_id)
        current_eligible_days = current_discount['eligible_days']

        # پیدا کردن مرحله بعدی
        next_tier = None
        for required_days in sorted(cls.DISCOUNT_RATES.keys()):
            if required_days > current_eligible_days:
                next_tier = {
                    'required_days': required_days,
                    'discount_percentage': cls.DISCOUNT_RATES[required_days],
                    'days_needed': required_days - current_eligible_days
                }
                break

        return next_tier


def format_discount_summary(discount_data: Dict) -> str:
    """فرمت کردن خلاصه تخفیف"""
    if not discount_data['applied']:
        return "❌ تخفیف گروهی اعمال نشد"

    message = f"💰 **تخفیف گروهی اعمال شد!**\n\n"
    message += f"💵 مبلغ اصلی: ${discount_data['original_amount']:.2f}\n"
    message += f"🎁 مبلغ تخفیف: ${discount_data['discount_amount']:.2f} "
    message += f"({discount_data['discount_percentage']}%)\n"
    message += f"✅ مبلغ نهایی: ${discount_data['final_amount']:.2f}\n\n"
    message += f"🏆 بر اساس {discount_data['eligible_days']} روز فعالیت گروهی"

    return message


def check_user_group_discount_eligibility(db: Session, user_id: int) -> bool:
    """بررسی سریع واجد شرایط بودن کاربر برای تخفیف گروهی"""
    calculator = GroupDiscountCalculator()
    discount_info = calculator.calculate_weekly_discount(db, user_id)
    return discount_info['is_eligible']