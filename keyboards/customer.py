
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton


def get_customer_kb(user_id: int) -> ReplyKeyboardMarkup:
    """کیبورد ثابت تک دکمه‌ای مشتری."""
    keyboard = [
        ["🏠 منوی اصلی"]
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_customer_inline_menu() -> InlineKeyboardMarkup:
    """کیبورد inline (شیشه‌ای) منوی اصلی مشتری."""
    keyboard = [
        [
            InlineKeyboardButton("💳 اعتبار و سفارش‌ها", callback_data="customer_credit_status"),
            InlineKeyboardButton("📂 آرشیو فایل‌ها", callback_data="customer_archive")
        ],
        [
            InlineKeyboardButton("💼 کیف پول و فاکتور", callback_data="customer_wallet"),
            InlineKeyboardButton("👥 زیرمجموعه‌ها", callback_data="customer_referrals")
        ],
        [
            InlineKeyboardButton("📊 آمار گروهی", callback_data="customer_group_stats"),
            InlineKeyboardButton("🎁 دعوت و کسب اعتبار", callback_data="customer_invite")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

