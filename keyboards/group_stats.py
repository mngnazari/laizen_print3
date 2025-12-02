# keyboards/group_stats.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_group_stats_keyboard() -> InlineKeyboardMarkup:
    """کیبورد برای منوی آمار گروهی"""
    keyboard = [
        [
            InlineKeyboardButton("📊 آمار امروز", callback_data="group_stats_today"),
            InlineKeyboardButton("📈 آمار هفتگی", callback_data="group_stats_weekly")
        ],
        [
            InlineKeyboardButton("📋 آمار تفصیلی", callback_data="group_stats_detailed"),
            InlineKeyboardButton("👥 لیست اعضا", callback_data="group_members_list")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_customer_menu")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_date_selection_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب تاریخ برای آمار"""
    from datetime import datetime, timedelta

    keyboard = []

    # دکمه‌های روزهای اخیر
    for i in range(7):
        date = datetime.now().date() - timedelta(days=i)
        date_str = date.strftime('%Y/%m/%d')
        day_name = "امروز" if i == 0 else f"{i} روز پیش"

        keyboard.append([
            InlineKeyboardButton(
                f"{day_name} ({date_str})",
                callback_data=f"group_stats_date_{date.strftime('%Y-%m-%d')}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="group_stats_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_members_list_keyboard(page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """کیبورد لیست اعضای گروه با صفحه‌بندی"""
    keyboard = []

    # دکمه‌های ناوبری
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"members_page_{page - 1}"))

    nav_buttons.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop"))

    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"members_page_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    # دکمه بازگشت
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت", callback_data="group_stats_menu")
    ])

    return InlineKeyboardMarkup(keyboard)