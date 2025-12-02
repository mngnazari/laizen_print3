# handlers/group_callbacks.py
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

import database.crud
import database.connection
from database.group_crud import (
    calculate_group_monthly_stats,
    check_group_discount_eligibility_advanced,
    get_group_performance_summary,
    get_user_referral_tree
)
from utils.group_analytics import (
    calculate_group_daily_stats,
    calculate_weekly_group_stats,
    format_group_stats_message
)
from keyboards.group_stats import (
    get_group_stats_keyboard,
    get_date_selection_keyboard,
    get_members_list_keyboard
)
from keyboards.customer import get_customer_kb


async def handle_group_stats_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های مربوط به آمار گروهی"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    # نمایش آمار امروز
    if data == "group_stats_today":
        await show_today_stats(query, context, user_id)

    # نمایش آمار هفتگی
    elif data == "group_stats_weekly":
        await show_weekly_stats(query, context, user_id)

    # نمایش آمار تفصیلی
    elif data == "group_stats_detailed":
        await show_detailed_stats_menu(query, context)

    # نمایش لیست اعضا
    elif data == "group_members_list":
        await show_members_list(query, context, user_id)

    # انتخاب تاریخ خاص
    elif data.startswith("group_stats_date_"):
        date_str = data.replace("group_stats_date_", "")
        await show_date_specific_stats(query, context, user_id, date_str)

    # صفحه‌بندی لیست اعضا
    elif data.startswith("members_page_"):
        page = int(data.replace("members_page_", ""))
        await show_members_list(query, context, user_id, page)

    # بازگشت به منوی آمار گروهی
    elif data == "group_stats_menu":
        await show_group_stats_main_menu(query, context)

    # بازگشت به منوی مشتری
    elif data == "back_to_customer_menu":
        await query.delete_message()
        await context.bot.send_message(
            chat_id=user_id,
            text="🔙 بازگشت به منوی اصلی",
            reply_markup=get_customer_kb(user_id)
        )


async def show_today_stats(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """نمایش آمار امروز"""
    with database.connection.SessionLocal() as db:
        stats = calculate_group_daily_stats(db, user_id)
        user = database.crud.get_user(db, user_id)

        if not user:
            await query.edit_message_text("❌ خطا در دریافت اطلاعات کاربر")
            return

        message = format_group_stats_message(stats, user.full_name)

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_group_stats_keyboard()
        )


async def show_weekly_stats(query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """نمایش آمار هفتگی"""
    with database.connection.SessionLocal() as db:
        weekly_stats = calculate_weekly_group_stats(db, user_id)
        user = database.crud.get_user(db, user_id)

        message = f"📊 **آمار هفتگی گروه {user.full_name}**\n\n"
        message += f"📂 **کل فایل‌های هفته:** {weekly_stats['total_files']}\n"
        message += f"🎯 **سهم شما:** {weekly_stats['user_files']} فایل\n\n"

        message += "📈 **تفکیک روزانه:**\n"
        for day_stats in weekly_stats['daily_breakdown']:
            date_str = day_stats['date'].strftime('%m/%d')
            message += f"   {date_str}: {day_stats['total_group_files']} فایل\n"

        # بررسی واجد شرایط بودن برای تخفیف
        discount_info = check_group_discount_eligibility_advanced(db, user_id)
        if discount_info['is_eligible']:
            message += f"\n🎉 **تخفیف این هفته:** {discount_info['discount_percentage']}%"
            message += f"\n✅ **روزهای واجد شرایط:** {discount_info['eligible_days']}/7"

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_group_stats_keyboard()
        )


async def show_detailed_stats_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی انتخاب تاریخ برای آمار تفصیلی"""
    await query.edit_message_text(
        "📅 **انتخاب تاریخ برای مشاهده آمار:**",
        parse_mode="Markdown",
        reply_markup=get_date_selection_keyboard()
    )


async def show_date_specific_stats(query, context: ContextTypes.DEFAULT_TYPE,
                                   user_id: int, date_str: str):
    """نمایش آمار تاریخ خاص"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        with database.connection.SessionLocal() as db:
            stats = calculate_group_daily_stats(db, user_id, target_date)
            user = database.crud.get_user(db, user_id)

            message = format_group_stats_message(stats, user.full_name)

            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_date_selection_keyboard()
            )

    except ValueError:
        await query.edit_message_text(
            "❌ خطا در تاریخ انتخابی",
            reply_markup=get_group_stats_keyboard()
        )


async def show_members_list(query, context: ContextTypes.DEFAULT_TYPE,
                            user_id: int, page: int = 0):
    """نمایش لیست اعضای گروه با صفحه‌بندی"""
    with database.connection.SessionLocal() as db:
        group_members = get_user_referral_tree(db, user_id)

        # تنظیمات صفحه‌بندی
        members_per_page = 5
        total_members = len(group_members)
        total_pages = (total_members + members_per_page - 1) // members_per_page
        start_idx = page * members_per_page
        end_idx = min(start_idx + members_per_page, total_members)

        page_members = group_members[start_idx:end_idx]

        message = f"👥 **اعضای گروه** (صفحه {page + 1} از {total_pages})\n\n"

        for i, member in enumerate(page_members, start=start_idx + 1):
            # محاسبه تعداد فایل‌های هر عضو
            member_files = db.query(database.models.FileOrder).filter(
                database.models.FileOrder.user_id == member.id
            ).count()

            status = "👑" if member.id == user_id else "👤"
            message += f"{status} **{i}.** {member.full_name}\n"
            message += f"   📱 {member.phone_number or 'نامشخص'}\n"
            message += f"   📂 {member_files} فایل\n"
            message += f"   📅 {member.created_at.strftime('%Y/%m/%d')}\n"
            message += "   ───────────\n"

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_members_list_keyboard(page, total_pages)
        )


async def show_group_stats_main_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی آمار گروهی"""
    user_id = query.from_user.id

    with database.connection.SessionLocal() as db:
        performance = get_group_performance_summary(db, user_id)
        user = database.crud.get_user(db, user_id)

        message = f"📊 **مرکز آمار گروه {user.full_name}**\n\n"
        message += f"👥 **تعداد اعضا:** {performance['total_members']} نفر\n"
        message += f"📂 **کل فایل‌ها:** {performance['total_files_all_time']}\n"
        message += f"📈 **میانگین فایل هر عضو:** {performance['avg_files_per_member']}\n"

        if performance['most_active_member']['user']:
            most_active = performance['most_active_member']
            message += f"🏆 **فعال‌ترین عضو:** {most_active['user'].full_name} "
            message += f"({most_active['files_count']} فایل)\n"

        message += "\n📋 **گزینه‌های موردنظر را انتخاب کنید:**"

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_group_stats_keyboard()
        )