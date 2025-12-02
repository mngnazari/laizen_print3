# keyboards/receipt_management.py

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
import database.models


# keyboards/receipt_management.py

def get_receipts_list_keyboard(receipts: List[database.models.Receipt]) -> InlineKeyboardMarkup:
    """کیبورد شیشه‌ای نمایش لیست رسیدها"""
    keyboard = []

    for receipt in receipts:
        button_text = f"📄 {receipt.user.full_name} - {receipt.created_at.strftime('%m/%d')}"
        callback_data = f"admin_receipt_detail_{receipt.id}"  # تغییر callback_data
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="admin_main_menu")])

    return InlineKeyboardMarkup(keyboard)


def get_receipt_action_keyboard(receipt_id: int) -> InlineKeyboardMarkup:
    """کیبورد عملیات روی رسید"""
    keyboard = [
        [
            InlineKeyboardButton("✅ شارژ کیف پول", callback_data=f"admin_charge_receipt_{receipt_id}"),  # تغییر
            InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_reject_receipt_{receipt_id}")  # تغییر
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin_manage_receipts")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)