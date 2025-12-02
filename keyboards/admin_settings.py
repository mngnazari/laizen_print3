# keyboards/admin_settings.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup





def get_admin_settings_keyboard():
    """کیبورد تنظیمات ادمین"""
    keyboard = [
        [
            InlineKeyboardButton("⏰ تاخیر دسترسی ادیتورها", callback_data="admin_editor_delay"),
            InlineKeyboardButton("📅 تعیین روزهای تعطیل", callback_data="admin_holidays")
        ],
        [
            InlineKeyboardButton("🕐 زمان‌بندی تحویل", callback_data="admin_delivery_schedule"),
            InlineKeyboardButton("📊 آمار تنظیمات", callback_data="admin_settings_stats")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="back_to_admin_main")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)
def get_delivery_setup_cancel_keyboard():
    """کیبورد لغو در حین تنظیم زمان‌بندی"""
    keyboard = [
        [InlineKeyboardButton("❌ لغو تنظیمات", callback_data="cancel_delivery_setup")]
    ]
    return InlineKeyboardMarkup(keyboard)