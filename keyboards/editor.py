# keyboards/editor.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from typing import Dict, List
import database.models
import database.connection
from utils.delivery_grouping import group_files_by_delivery_time
import logging
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from utils.timezone_utils import format_shamsi

def get_edit_deadline_or_calculate(file_order):
    """دریافت edit_deadline (همه datetime‌ها naive UTC هستند)"""
    if file_order.edit_deadline:
        return file_order.edit_deadline
    elif file_order.delivery_datetime:
        # محاسبه 18 ساعت قبل از تحویل
        return file_order.delivery_datetime - timedelta(hours=18)
    return None
# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_editor_reply_keyboard() -> ReplyKeyboardMarkup:
    """کیبورد ثابت ادیتور"""
    keyboard = [
        ["📝 منوی ادیتور"]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_editor_main_keyboard() -> InlineKeyboardMarkup:
    """کیبورد اصلی ادیتور - با فیلتر دسترسی"""
    import database.connection
    import database.editor_crud
    import logging

    logger = logging.getLogger(__name__)
    logger.info("🎨 ساخت کیبورد اصلی ادیتور...")

    # استفاده از فایل‌های قابل دسترس
    with database.connection.SessionLocal() as db:
        accessible_files = database.editor_crud.get_accessible_files_for_editor(db, "pending")
        logger.info(f"📊 تعداد فایل‌های قابل دسترس: {len(accessible_files)}")

        # فقط فایل‌هایی که به هیچ ادیتوری assign نشدن
        new_files = [f for f in accessible_files if f.assigned_editor_id is None]
        new_files_count = len(new_files)

        logger.info(f"📊 تعداد فایل‌های جدید (unassigned): {new_files_count}")

    keyboard = [
        [InlineKeyboardButton(f"📝 فایل‌های در انتظار ادیت ({new_files_count})", callback_data="editor_pending_files")],
        [InlineKeyboardButton("📋 فایل‌های باقی‌مانده", callback_data="editor_remaining_files")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_editor_customers_keyboard(edit_deadline_time: str) -> InlineKeyboardMarkup:
    """کیبورد مشتریان - با timezone handling درست"""
    logger.info(f"🔍 شروع ایجاد کیبورد مشتریان برای ددتایم: {edit_deadline_time}")

    with database.connection.SessionLocal() as db:
        try:
            # دریافت همه فایل‌های pending
            all_files = db.query(database.models.FileOrder).filter(
                database.models.FileOrder.status == "pending"
            ).options(joinedload(database.models.FileOrder.user)).all()

            logger.info(f"📊 کل فایل‌های pending: {len(all_files)}")

            # فیلتر فایل‌ها بر اساس ددتایم ادیت
            matching_files = []

            for file_order in all_files:
                file_edit_deadline = get_edit_deadline_or_calculate(file_order)

                logger.info(f"🔍 فایل: {file_order.file_name}")
                logger.info(f"   - edit_deadline در دیتابیس: {file_order.edit_deadline}")
                logger.info(f"   - delivery_datetime در دیتابیس: {file_order.delivery_datetime}")
                logger.info(f"   - محاسبه شده: {file_edit_deadline}")

                if file_edit_deadline:
                    file_edit_deadline_str = file_edit_deadline.strftime("%Y/%m/%d %H:%M")
                    logger.info(f"   - فرمت شده: '{file_edit_deadline_str}'")
                    logger.info(f"   - مقایسه با: '{edit_deadline_time}'")
                    logger.info(f"   - برابر است؟ {file_edit_deadline_str == edit_deadline_time}")

                    if file_edit_deadline_str == edit_deadline_time:
                        matching_files.append(file_order)
                        logger.info(f"✅ فایل {file_order.file_name} مطابقت دارد")

            logger.info(f"📊 فایل‌های مطابق: {len(matching_files)}")

            # گروه‌بندی بر اساس مشتری
            customer_groups = {}
            for file_order in matching_files:
                if file_order.user and file_order.user.customer_code:
                    customer_code = file_order.user.customer_code
                    if customer_code not in customer_groups:
                        customer_groups[customer_code] = []
                    customer_groups[customer_code].append(file_order)

            keyboard = []

            # محاسبه فایل‌های جدید کل
            total_new_files = sum(1 for f in matching_files if f.assigned_editor_id is None)
            logger.info(
                f"📊 کل فایل‌ها: {len(matching_files)}, تعداد مشتریان: {len(customer_groups)}, فایل‌های جدید: {total_new_files}")

            # دکمه همه
            if matching_files:
                keyboard.append([InlineKeyboardButton(
                    f"📦 همه ({total_new_files})",
                    callback_data=f"editor_send_all_{edit_deadline_time}"
                )])
                logger.info(f"🔘 دکمه همه اضافه شد: ({total_new_files})")

            # دکمه‌های مشتریان
            for customer_code, customer_files in customer_groups.items():
                if customer_files and customer_files[0].user:
                    new_files_count = sum(1 for f in customer_files if f.assigned_editor_id is None)

                    button_text = f"👤 {customer_code} ({new_files_count})"
                    callback_data = f"editor_send_customer_{customer_code}_{edit_deadline_time}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
                    logger.info(f"🔘 دکمه مشتری اضافه شد: {button_text}")

            if not matching_files:
                keyboard.append([InlineKeyboardButton("هیچ فایلی موجود نیست", callback_data="no_files")])

            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="editor_pending_files")])

            return InlineKeyboardMarkup(keyboard)

        except Exception as e:
            logger.error(f"💥 خطا در ایجاد کیبورد مشتریان: {e}", exc_info=True)
            keyboard = [
                [InlineKeyboardButton("خطا در بارگذاری", callback_data="no_files")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_pending_files")]
            ]
            return InlineKeyboardMarkup(keyboard)


def calculate_edit_deadline_from_delivery(delivery_datetime):
    """محاسبه ددتایم ادیت از روی زمان تحویل"""
    try:
        edit_deadline = delivery_datetime - timedelta(hours=18)
        return edit_deadline
    except:
        return delivery_datetime


def count_new_files_for_delivery_time(db, delivery_time: str) -> int:
    """محاسبه تعداد فایل‌های جدید (غیرتخصیص یافته) برای زمان مشخص"""
    all_files = db.query(database.models.FileOrder).filter(
        database.models.FileOrder.status == "pending",
        database.models.FileOrder.assigned_editor_id.is_(None),
        database.models.FileOrder.delivery_datetime.isnot(None)
    ).all()

    new_files_count = 0
    for file_order in all_files:
        file_delivery_str = file_order.delivery_datetime.strftime("%Y/%m/%d %H:%M")
        if file_delivery_str == delivery_time:
            new_files_count += 1

    return new_files_count


def get_editor_delivery_times_keyboard():
    """کیبورد زمان‌های تحویل - با فیلتر دسترسی"""
    from collections import defaultdict
    import database.connection
    import database.editor_crud

    with database.connection.SessionLocal() as db:
        accessible_files = database.editor_crud.get_accessible_files_for_editor(db, "pending")

        if not accessible_files:
            keyboard = [[InlineKeyboardButton("❌ فایلی موجود نیست", callback_data="no_files")]]
            keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="editor_main_menu")])
            return InlineKeyboardMarkup(keyboard)

        delivery_groups = defaultdict(list)

        for file_order in accessible_files:
            edit_deadline = get_edit_deadline_or_calculate(file_order)

            if edit_deadline:
                time_key = edit_deadline.strftime("%Y/%m/%d %H:%M")
                delivery_groups[time_key].append(file_order)

        keyboard = []

        for time_display, files in sorted(delivery_groups.items()):
            count = len(files)
            keyboard.append([
                InlineKeyboardButton(
                    f"🕐 {time_display} ({count} فایل)",
                    callback_data=f"editor_delivery_{time_display}"
                )
            ])

        keyboard.append([InlineKeyboardButton("🏠 منوی اصلی", callback_data="editor_main_menu")])

        return InlineKeyboardMarkup(keyboard)

from datetime import datetime, timedelta, timezone

IRAN_TZ = timezone(timedelta(hours=3, minutes=30))

def normalize_datetime_to_iran(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IRAN_TZ)

def get_edit_deadline_or_calculate(file_order):
    if file_order.edit_deadline:
        return normalize_datetime_to_iran(file_order.edit_deadline)
    elif file_order.delivery_datetime:
        delivery_iran = normalize_datetime_to_iran(file_order.delivery_datetime)
        return delivery_iran - timedelta(hours=18)
    return None