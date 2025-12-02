# keyboards/vault_menu.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_vaults_menu_keyboard():
    """کیبورد منوی صندوق‌ها، درآمد و هزینه‌ها"""
    keyboard = [
        [
            InlineKeyboardButton("💰 مدیریت صندوق‌ها", callback_data="vault_list"),
        ],
        [
            InlineKeyboardButton("➕ ثبت درآمد مستقل", callback_data="vault_independent_income"),
            InlineKeyboardButton("➖ ثبت هزینه", callback_data="vault_record_expense"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="back_to_admin_main")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)