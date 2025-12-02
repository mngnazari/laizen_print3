# database/group_crud.py
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from collections import defaultdict

from .models import User, FileOrder


def get_user_referral_tree(db: Session, user_id: int, max_depth: int = 2) -> List[User]:
    """دریافت درخت کامل ارجاعات کاربر تا عمق مشخص"""

    def get_referrals_recursive(current_user_id: int, current_depth: int) -> List[User]:
        if current_depth >= max_depth:
            return []

        direct_referrals = db.query(User).filter(User.referrer_id == current_user_id).all()
        all_referrals = list(direct_referrals)

        for referral in direct_referrals:
            sub_referrals = get_referrals_recursive(referral.id, current_depth + 1)
            all_referrals.extend(sub_referrals)

        return all_referrals

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []

    # شامل خود کاربر
    result = [user]

    # اضافه کردن زیرمجموعه‌ها
    referrals = get_referrals_recursive(user_id, 0)
    result.extend(referrals)

    # اگر کاربر خودش دعوت شده است، گروه اصلی را در نظر بگیر
    if user.referrer_id:
        main_referrer = db.query(User).filter(User.id == user.referrer_id).first()
        if main_referrer and main_referrer not in result:
            result.append(main_referrer)

            # سایر زیرمجموعه‌های هم‌سطح
            siblings = db.query(User).filter(
                User.referrer_id == user.referrer_id,
                User.id != user_id
            ).all()

            for sibling in siblings:
                if sibling not in result:
                    result.append(sibling)

    return result


def get_group_files_by_date_range(db: Session, user_id: int,
                                  start_date: datetime, end_date: datetime) -> List[FileOrder]:
    """دریافت فایل‌های گروه در بازه زمانی مشخص"""
    group_members = get_user_referral_tree(db, user_id)
    member_ids = [member.id for member in group_members]

    return db.query(FileOrder).filter(
        and_(
            FileOrder.user_id.in_(member_ids),
            FileOrder.created_at >= start_date,
            FileOrder.created_at < end_date
        )
    ).order_by(desc(FileOrder.created_at)).all()


def calculate_group_monthly_stats(db: Session, user_id: int) -> Dict:
    """محاسبه آمار ماهانه گروه"""
    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)

    group_members = get_user_referral_tree(db, user_id)
    member_ids = [member.id for member in group_members]

    if not member_ids:
        return {
            'total_files': 0,
            'user_files': 0,
            'daily_breakdown': {},
            'top_contributors': []
        }

    # فایل‌های کل ماه
    monthly_files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id.in_(member_ids),
            FileOrder.created_at >= month_start
        )
    ).all()

    # تفکیک روزانه
    daily_breakdown = defaultdict(int)
    user_files_count = 0
    member_contributions = defaultdict(int)

    for file_order in monthly_files:
        day_key = file_order.created_at.date().strftime('%Y-%m-%d')
        daily_breakdown[day_key] += 1
        member_contributions[file_order.user_id] += 1

        if file_order.user_id == user_id:
            user_files_count += 1

    # برترین مشارکت‌کنندگان
    top_contributors = []
    for member in group_members:
        contribution = member_contributions.get(member.id, 0)
        if contribution > 0:
            top_contributors.append({
                'user': member,
                'files_count': contribution
            })

    top_contributors.sort(key=lambda x: x['files_count'], reverse=True)

    return {
        'total_files': len(monthly_files),
        'user_files': user_files_count,
        'daily_breakdown': dict(daily_breakdown),
        'top_contributors': top_contributors[:5]  # ۵ نفر برتر
    }


def check_group_discount_eligibility_advanced(db: Session, user_id: int,
                                              threshold: int = 10) -> Dict:
    """بررسی پیشرفته واجد شرایط بودن گروه برای تخفیف"""
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)

    # بررسی آمار هفتگی
    weekly_stats = []
    eligible_days = 0

    for i in range(7):
        check_date = week_ago + timedelta(days=i)
        start_datetime = datetime.combine(check_date, datetime.min.time())
        end_datetime = start_datetime + timedelta(days=1)

        group_members = get_user_referral_tree(db, user_id)
        member_ids = [member.id for member in group_members]

        daily_files = db.query(FileOrder).filter(
            and_(
                FileOrder.user_id.in_(member_ids),
                FileOrder.created_at >= start_datetime,
                FileOrder.created_at < end_datetime
            )
        ).count()

        is_eligible = daily_files >= threshold
        if is_eligible:
            eligible_days += 1

        weekly_stats.append({
            'date': check_date,
            'files_count': daily_files,
            'is_eligible': is_eligible
        })

    # محاسبه درصد تخفیف بر اساس عملکرد
    discount_percentage = 0
    if eligible_days >= 5:  # ۵ روز از هفته
        discount_percentage = 15
    elif eligible_days >= 3:  # ۳ روز از هفته
        discount_percentage = 10
    elif eligible_days >= 1:  # حداقل یک روز
        discount_percentage = 5

    return {
        'eligible_days': eligible_days,
        'total_days': 7,
        'discount_percentage': discount_percentage,
        'weekly_stats': weekly_stats,
        'is_eligible': eligible_days > 0
    }


def get_group_performance_summary(db: Session, user_id: int) -> Dict:
    """خلاصه عملکرد کلی گروه"""
    group_members = get_user_referral_tree(db, user_id)

    # آمار کلی اعضا
    total_members = len(group_members)
    member_ids = [member.id for member in group_members]

    if not member_ids:
        return {
            'total_members': 0,
            'total_files_all_time': 0,
            'avg_files_per_member': 0,
            'most_active_member': None,
            'group_creation_date': None
        }

    # آمار فایل‌ها
    all_files = db.query(FileOrder).filter(
        FileOrder.user_id.in_(member_ids)
    ).all()

    total_files = len(all_files)
    avg_files_per_member = total_files / total_members if total_members > 0 else 0

    # فعال‌ترین عضو
    member_file_counts = defaultdict(int)
    for file_order in all_files:
        member_file_counts[file_order.user_id] += 1

    most_active_member = None
    if member_file_counts:
        most_active_id = max(member_file_counts, key=member_file_counts.get)
        most_active_member = db.query(User).filter(User.id == most_active_id).first()

    # تاریخ تشکیل گروه (قدیمی‌ترین عضو)
    creation_dates = [member.created_at for member in group_members if member.created_at]
    group_creation_date = min(creation_dates) if creation_dates else None

    return {
        'total_members': total_members,
        'total_files_all_time': total_files,
        'avg_files_per_member': round(avg_files_per_member, 1),
        'most_active_member': {
            'user': most_active_member,
            'files_count': member_file_counts.get(most_active_member.id, 0) if most_active_member else 0
        },
        'group_creation_date': group_creation_date
    }