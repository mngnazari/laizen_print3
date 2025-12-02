# keyboards/operator_files.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Dict, List
import database.models
from utils.delivery_grouping import count_total_pending_files, count_pending_files_by_delivery, group_files_by_customer, \
    count_ready_files_by_delivery, count_total_ready_files
from utils.delivery_grouping import group_files_by_customer

def get_operator_files_main_keyboard() -> InlineKeyboardMarkup:
    """کیبورد اصلی فایل‌های اپراتور با آمار دقیق‌تر"""
    ready_files = count_total_ready_files()

    keyboard = [
        [InlineKeyboardButton(f"📁 فایل‌ها ({ready_files})", callback_data="operator_files_main")]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_delivery_times_keyboard() -> InlineKeyboardMarkup:
    """کیبورد زمان‌های تحویل با شمارش دقیق"""
    delivery_counts = count_ready_files_by_delivery()
    keyboard = []

    if not delivery_counts:
        keyboard.append([InlineKeyboardButton("هیچ فایلی آماده نیست", callback_data="no_files")])
    else:
        sorted_deliveries = sorted(delivery_counts.items())

        for delivery_time, count in sorted_deliveries:
            if count > 0:  # فقط زمان‌هایی که فایل دارند
                button_text = f"🕐 {delivery_time} ({count})"
                callback_data = f"operator_delivery_{delivery_time}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="operator_menu")])

    return InlineKeyboardMarkup(keyboard)


# در keyboards/operator_files.py تابع get_customers_by_delivery_keyboard را اصلاح کنید:



def get_customers_by_delivery_keyboard(delivery_time: str, context_data: dict = None) -> InlineKeyboardMarkup:
    """کیبورد مشتریان برای یک زمان تحویل خاص"""
    import database.connection
    import database.crud
    import jdatetime

    # دریافت اطلاعات tracking
    sent_files = context_data.get('sent_files', set()) if context_data else set()
    all_tracking_key = f"{delivery_time}_ALL"

    with database.connection.SessionLocal() as db:
        try:
            jd = jdatetime.datetime.strptime(delivery_time, "%Y/%m/%d %H:%M")
            gregorian_datetime = jd.togregorian()
            target_date = gregorian_datetime.strftime("%Y-%m-%d %H:%M")
        except:
            target_date = delivery_time

        files = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending",
            database.models.FileOrder.delivery_datetime.like(f"{target_date}%")
        ).options(database.crud.joinedload(database.models.FileOrder.user)).all()

        customer_groups = group_files_by_customer(files)
        keyboard = []

        total_files = sum(len(files) for files in customer_groups.values())

        # دکمه کل - بررسی tracking
        if total_files > 0:
            if all_tracking_key in sent_files:
                all_button_text = f"📦 همه (ارسال شده)"
            else:
                all_button_text = f"📦 همه ({total_files})"

            keyboard.append([InlineKeyboardButton(
                all_button_text,
                callback_data=f"operator_send_all_{delivery_time}"
            )])

        # دکمه‌های مشتریان - بررسی tracking
        for customer_code, customer_files in customer_groups.items():
            customer_name = customer_files[0].user.full_name
            customer_tracking = f"{delivery_time}_{customer_code}"

            if customer_tracking in sent_files:
                button_text = f"👤 {customer_code} - {customer_name} (ارسال شده)"
            else:
                button_text = f"👤 {customer_code} - {customer_name} ({len(customer_files)})"

            callback_data = f"operator_send_customer_{customer_code}_{delivery_time}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        if total_files == 0:
            keyboard.append([InlineKeyboardButton("هیچ فایلی موجود نیست", callback_data="no_files")])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="operator_files_main")])

    return InlineKeyboardMarkup(keyboard)
# در handlers/operator_files.py اضافه کنید:

