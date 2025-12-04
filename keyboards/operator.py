# keyboards/operator.py
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
from database.models import User


def get_operator_main_inline_keyboard() -> InlineKeyboardMarkup:
    """کیبورد شیشه‌ای اصلی اپراتور - جایگزین کیبورد ثابت"""
    from utils.delivery_grouping import count_total_ready_files

    ready_files = count_total_ready_files()

    keyboard = [
        [InlineKeyboardButton("📋 صدور فاکتور", callback_data="operator_invoice_menu")]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_operator_invoice_submenu() -> InlineKeyboardMarkup:
    """زیرمنوی صدور فاکتور که شامل فایل‌ها و گزینه‌های قبلی است"""
    from utils.delivery_grouping import count_total_ready_files

    ready_files = count_total_ready_files()

    keyboard = [
        # گزینه فایل‌ها (از قبل موجود)
        [InlineKeyboardButton(f"📁 فایل‌ها ({ready_files})", callback_data="operator_files_main")],

        # گزینه‌های دیگر (تبدیل شده از کیبورد ثابت)
        [InlineKeyboardButton("📊 آمار کارهای من", callback_data="operator_my_stats")],
        [InlineKeyboardButton("👥 مشاهده مشتریان", callback_data="operator_view_customers")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="operator_settings")],

        # دکمه بازگشت
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="operator_main_menu")]
    ]

    return InlineKeyboardMarkup(keyboard)


# توابع قدیمی - برای سازگاری با کد فعلی نگه داشته شده‌اند
def get_operator_kb() -> ReplyKeyboardMarkup:
    """کیبورد ثابت اپراتور - DEPRECATED - فقط برای سازگاری"""
    keyboard = [
        ["🔙 منوی اصلی"]  # فقط یک دکمه برای بازگشت
    ]

    print(f"🔍 DEBUG get_operator_kb called - keyboard text: '{keyboard[0][0]}'")

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def create_customers_invoice_keyboard(customers: List[User]) -> InlineKeyboardMarkup:
    """ایجاد کیبورد شیشه‌ای برای انتخاب مشتری جهت صدور فاکتور"""
    keyboard = []

    # ایجاد دکمه برای هر مشتری - فقط کد اختصاری
    for customer in customers:
        button_text = customer.customer_code  # فقط کد اختصاری
        callback_data = f"select_customer_{customer.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # دکمه بازگشت به زیرمنوی صدور فاکتور
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="operator_invoice_menu")])

    return InlineKeyboardMarkup(keyboard)


def create_customer_files_keyboard(orders: List, customer_id: int) -> InlineKeyboardMarkup:
    """ایجاد کیبورد فایل‌های مشتری با وضعیت موفق/ناموفق"""
    keyboard = []

    print(f"🎹 DEBUG: Creating keyboard for {len(orders)} orders")

    for order in orders:
        # تعیین نام فایل با تعداد
        file_display = order.file_name
        if order.print_count > 1:
            file_display = f"X{order.print_count}-{order.file_name}"

        # تعیین ایموجی وضعیت (پیش‌فرض: دایره خالی)
        status_emoji = "⚪"  # دایره خالی
        if hasattr(order, 'print_status'):
            if order.print_status == "success":
                status_emoji = "🟢"  # دایره سبز
            elif order.print_status == "failed":
                status_emoji = "🔴"  # دایره قرمز

        button_text = f"{status_emoji} {file_display}"
        callback_data = f"toggle_file_{order.id}"

        print(f"🎹 DEBUG: Adding button - Text: '{button_text}', Callback: '{callback_data}'")

        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # دکمه صدور فاکتور
    keyboard.append([InlineKeyboardButton("🧾 صدور فاکتور", callback_data=f"issue_invoice_{customer_id}")])

    # دکمه بازگشت به لیست مشتریان
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست مشتریان", callback_data="back_to_customers_list")])

    print(f"🎹 DEBUG: Keyboard created with {len(keyboard)} rows")

    return InlineKeyboardMarkup(keyboard)


def create_invoice_navigation_keyboard(current_invoice: int, total_invoices: int) -> InlineKeyboardMarkup:
    """ایجاد کیبورد ناوبری برای فاکتورها"""
    keyboard = []

    navigation_buttons = []

    # دکمه قبلی
    if current_invoice > 0:
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ قبلی", callback_data=f"invoice_nav_prev_{current_invoice}")
        )

    # نمایش شماره فاکتور
    navigation_buttons.append(
        InlineKeyboardButton(f"{current_invoice + 1}/{total_invoices}", callback_data="noop")
    )

    # دکمه بعدی
    if current_invoice < total_invoices - 1:
        navigation_buttons.append(
            InlineKeyboardButton("➡️ بعدی", callback_data=f"invoice_nav_next_{current_invoice}")
        )

    if navigation_buttons:
        keyboard.append(navigation_buttons)

    # دکمه بازگشت
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_customer_menu")])

    return InlineKeyboardMarkup(keyboard)