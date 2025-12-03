
from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
import database.connection
import database.crud


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


def get_customer_inline_menu(user_id: int) -> InlineKeyboardMarkup:
    """کیبورد inline (شیشه‌ای) منوی اصلی مشتری."""

    # محاسبه تعداد فایل‌های در حال انجام
    with database.connection.SessionLocal() as db:
        in_progress_files = database.crud.get_customer_in_progress_files(db, user_id)
        in_progress_count = len(in_progress_files)

    # متن دکمه "در حال انجام" با تعداد
    in_progress_text = f"🔄 در حال انجام ({in_progress_count})"

    keyboard = [
        [
            InlineKeyboardButton("💳 اعتبار و سفارش‌ها", callback_data="customer_credit_status"),
            InlineKeyboardButton("📂 آرشیو فایل‌ها", callback_data="customer_archive")
        ],
        [
            InlineKeyboardButton(in_progress_text, callback_data="customer_in_progress"),
            InlineKeyboardButton("💼 کیف پول و فاکتور", callback_data="customer_wallet")
        ],
        [
            InlineKeyboardButton("👥 زیرمجموعه‌ها", callback_data="customer_referrals"),
            InlineKeyboardButton("📊 آمار گروهی", callback_data="customer_group_stats")
        ],
        [
            InlineKeyboardButton("🎁 دعوت و کسب اعتبار", callback_data="customer_invite")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)

