# keyboards/admin.py - نسخه اصلاح شده

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
from typing import List
import database.models
import database.connection
import database.crud

def get_admin_main_menu():
    """کیبورد منوی اصلی ادمین - با دکمه Broadcast"""
    keyboard = [
        [
            InlineKeyboardButton("🔗 تولید لینک دعوت", callback_data="admin_generate_link"),
            InlineKeyboardButton("👥 مشاهده کاربران", callback_data="admin_view_users")
        ],
        [
            InlineKeyboardButton("🌳 ساختار درختی دعوت", callback_data="admin_referral_tree"),
            InlineKeyboardButton("⚙️ تنظیم سقف دعوت", callback_data="admin_set_limit")
        ],
        [
            InlineKeyboardButton("💼 مدیریت مشتریان", callback_data="admin_customer_mgmt"),
            InlineKeyboardButton("📄 رسیدهای دریافتی", callback_data="admin_receipts")
        ],
        [
            # دکمه جدید برای ارسال پیام همگانی
            InlineKeyboardButton("📣 ارسال پیام همگانی", callback_data="broadcast_main"),
            InlineKeyboardButton("💰 صندوق، درآمد، هزینه", callback_data="admin_vaults_menu")
        ],
        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings"),
            InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("👥 مدیریت کارکنان", callback_data="admin_staff_menu")
            ]
    ]
    return InlineKeyboardMarkup(keyboard)


# باقی توابع همان‌طور که قبلاً بودند...
def get_admin_kb() -> ReplyKeyboardMarkup:
    """کیبورد ادمین - نسخه سازگاری برای فایل‌های قدیمی."""
    keyboard = [
        ["تولید لینک دعوت 🔗", "مشاهده کاربران 👥"],
        ["نمایش ساختار دعوت 🌳", "تنظیم سقف دعوت ⚙️"],
        ["👥 مدیریت مشتریان", "🏆 تنظیمات گروه"],
        ["📣 ارسال پیام همگانی", "⚙️ تنظیمات"],
        ["📊 آمار کلی"],
    ]

    return ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_admin_back_button() -> InlineKeyboardMarkup:
    """دکمه بازگشت به منوی اصلی ادمین"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_main_menu")]
    ])


def get_customers_keyboard(customers: List[database.models.User]) -> InlineKeyboardMarkup:
    """کیبورد شیشه‌ای نمایش لیست مشتریان."""
    keyboard = []

    for customer in customers:
        button_text = f"{customer.full_name} - {customer.phone_number}"
        callback_data = f"customer_{customer.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel_customer_selection")])

    return InlineKeyboardMarkup(keyboard)


def get_wallet_management_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    """کیبورد مدیریت کیف پول مشتری."""
    keyboard = [
        [InlineKeyboardButton("💰 شارژ/تسویه کیف پول", callback_data=f"wallet_charge_{customer_id}")],
        [InlineKeyboardButton("💳 تنظیم قیمت پرینت", callback_data=f"set_price_{customer_id}")],
        [InlineKeyboardButton("📊 مشاهده تراکنش‌ها", callback_data=f"view_transactions_{customer_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_customers")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_wallet_management")]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_group_settings_keyboard() -> InlineKeyboardMarkup:
    """کیبورد تنظیمات گروه"""
    keyboard = [
        [
            InlineKeyboardButton("🥈 تنظیم نقره‌ای", callback_data="admin_group_silver"),
            InlineKeyboardButton("🥇 تنظیم طلایی", callback_data="admin_group_gold")
        ],
        [
            InlineKeyboardButton("📊 آمار گروه‌ها", callback_data="admin_group_stats"),
            InlineKeyboardButton("🔄 بازنشانی", callback_data="admin_group_reset")
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_main")]
    ]
    return InlineKeyboardMarkup(keyboard)