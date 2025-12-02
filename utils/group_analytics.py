# utils/group_analytics.py
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from database.models import User, FileOrder


def get_user_group_members(db: Session, user_id: int) -> List[User]:
    """دریافت تمام اعضای گروه کاربر (خودش + زیرمجموعه‌ها)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    # اگر کاربر خودش دعوت‌کننده است
    group_members = [user]  # خود کاربر

    # اضافه کردن زیرمجموعه‌های مستقیم
    direct_referrals = db.query(User).filter(User.referrer_id == user_id).all()
    group_members.extend(direct_referrals)

    # اگر کاربر خودش دعوت شده است
    if user.referrer_id:
        referrer = db.query(User).filter(User.id == user.referrer_id).first()
        if referrer and referrer not in group_members:
            group_members.append(referrer)

        # اضافه کردن سایر زیرمجموعه‌های دعوت‌کننده
        sibling_referrals = db.query(User).filter(
            User.referrer_id == user.referrer_id,
            User.id != user_id
        ).all()

        for sibling in sibling_referrals:
            if sibling not in group_members:
                group_members.append(sibling)

    return group_members


def calculate_group_daily_stats(db: Session, user_id: int, specific_date: Optional[datetime.date] = None) -> Dict:
    """محاسبه آمار روزانه گروه"""
    if specific_date is None:
        specific_date = datetime.now().date()

    # دریافت اعضای گروه
    group_members = get_user_group_members(db, user_id)
    group_member_ids = [member.id for member in group_members]

    if not group_member_ids:
        return {
            'total_group_files': 0,
            'user_files': 0,
            'group_members': [],
            'active_members': 0,
            'date': specific_date
        }

    # محاسبه تاریخ شروع و پایان روز
    start_date = datetime.combine(specific_date, datetime.min.time())
    end_date = start_date + timedelta(days=1)

    # شمارش فایل‌های کل گروه در آن روز
    total_group_files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id.in_(group_member_ids),
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).count()

    # شمارش فایل‌های خود کاربر در آن روز
    user_files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id == user_id,
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).count()

    # شمارش اعضای فعال (که حداقل یک فایل ارسال کرده‌اند)
    active_member_ids = db.query(FileOrder.user_id).filter(
        and_(
            FileOrder.user_id.in_(group_member_ids),
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).distinct().all()

    active_members = len(active_member_ids)

    return {
        'total_group_files': total_group_files,
        'user_files': user_files,
        'group_members': group_members,
        'active_members': active_members,
        'date': specific_date
    }


def calculate_weekly_group_stats(db: Session, user_id: int) -> Dict:
    """محاسبه آمار هفتگی گروه"""
    week_ago = datetime.now().date() - timedelta(days=7)
    today = datetime.now().date()

    group_members = get_user_group_members(db, user_id)
    group_member_ids = [member.id for member in group_members]

    if not group_member_ids:
        return {
            'total_files': 0,
            'user_files': 0,
            'daily_breakdown': []
        }

    # محاسبه تاریخ شروع و پایان هفته
    start_date = datetime.combine(week_ago, datetime.min.time())
    end_date = datetime.combine(today + timedelta(days=1), datetime.min.time())

    # فایل‌های کل هفته
    total_files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id.in_(group_member_ids),
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).count()

    # فایل‌های کاربر در هفته
    user_files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id == user_id,
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).count()

    # تفکیک روزانه
    daily_breakdown = []
    for i in range(7):
        day = week_ago + timedelta(days=i)
        day_stats = calculate_group_daily_stats(db, user_id, day)
        daily_breakdown.append(day_stats)

    return {
        'total_files': total_files,
        'user_files': user_files,
        'daily_breakdown': daily_breakdown
    }


def format_group_stats_message(stats: Dict, user_name: str) -> str:
    """فرمت کردن پیام آمار گروهی"""
    date_str = stats['date'].strftime('%Y/%m/%d')

    message = f"📊 **آمار گروه {user_name}**\n\n"
    message += f"📅 **تاریخ:** {date_str}\n\n"

    # آمار کلی
    message += f"👥 **اعضای گروه:** {len(stats['group_members'])} نفر\n"
    message += f"📂 **کل فایل‌های گروه امروز:** {stats['total_group_files']}\n"
    message += f"🎯 **سهم شما:** {stats['user_files']} فایل\n"
    message += f"⚡ **اعضای فعال امروز:** {stats['active_members']} نفر\n\n"

    # درصد مشارکت
    if stats['total_group_files'] > 0:
        participation_rate = (stats['user_files'] / stats['total_group_files']) * 100
        message += f"📈 **نرخ مشارکت شما:** {participation_rate:.1f}%\n\n"

    # لیست اعضای گروه
    message += "👥 **اعضای گروه:**\n"
    for i, member in enumerate(stats['group_members'][:5], 1):  # حداکثر 5 نفر
        message += f"   {i}. {member.full_name}\n"

    if len(stats['group_members']) > 5:
        remaining = len(stats['group_members']) - 5
        message += f"   ... و {remaining} نفر دیگر\n"

    # راهنمایی برای کسب تخفیف
    if stats['total_group_files'] >= 10:
        message += "\n🎉 **تبریک!** گروه شما امروز به حد نصاب تخفیف رسیده است!"
    else:
        remaining_files = 10 - stats['total_group_files']
        message += f"\n💡 **نکته:** برای کسب تخفیف، گروه شما {remaining_files} فایل دیگر نیاز دارد."

    return message


def check_group_discount_eligibility(db: Session, user_id: int, date: Optional[datetime.date] = None) -> bool:
    """بررسی واجد شرایط بودن گروه برای دریافت تخفیف"""
    if date is None:
        date = datetime.now().date()

    stats = calculate_group_daily_stats(db, user_id, date)

    # معیار: حداقل 10 فایل در روز برای کل گروه
    return stats['total_group_files'] >= 10