# keyboards/customer_management.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List
import database.models


def get_customers_list_keyboard(customers: List[database.models.User]) -> InlineKeyboardMarkup:
    """کیبورد نمایش لیست مشتریان با کد اختصاری و دایره وضعیت پیام"""
    keyboard = []

    for customer in customers:
        # دریافت وضعیت دریافت پیام
        status = customer.notification_status or "all"
        status_emoji = database.crud.get_notification_status_emoji(status)

        # نمایش: ایموجی + نام + کد + شماره
        button_text = f"{status_emoji} {customer.full_name} - {customer.customer_code} - {customer.phone_number}"
        callback_data = f"customer_mgmt_{customer.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

    # دکمه لغو
    keyboard.append([InlineKeyboardButton("❌ لغو", callback_data="cancel_customer_mgmt")])

    return InlineKeyboardMarkup(keyboard)


def get_customer_operations_keyboard(customer_id: int, notification_status: str = "all") -> InlineKeyboardMarkup:
    """کیبورد عملیات مدیریت مشتری با دکمه تغییر وضعیت پیام"""

    # دریافت ایموجی وضعیت فعلی
    status_emoji = database.crud.get_notification_status_emoji(notification_status)

    keyboard = [
        [
            InlineKeyboardButton("💰 شارژ کیف پول", callback_data=f"wallet_charge_{customer_id}"),
            InlineKeyboardButton("🎁 شارژ اعتبار تخفیف", callback_data=f"discount_charge_{customer_id}")
        ],
        [
            InlineKeyboardButton("💳 تعیین هزینه انجام کار", callback_data=f"set_work_price_{customer_id}")
        ],
        [
            InlineKeyboardButton(f"{status_emoji} تغییر وضعیت دریافت پیام",
                                 callback_data=f"toggle_notification_{customer_id}")
        ],
        [
            InlineKeyboardButton("📊 مشاهده تراکنش‌ها", callback_data=f"view_customer_transactions_{customer_id}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_customers_list")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def get_transaction_history_keyboard(customer_id: int) -> InlineKeyboardMarkup:
    """کیبورد مشاهده تراکنش‌ها"""
    keyboard = [
        [
            InlineKeyboardButton("💰 تراکنش‌های کیف پول", callback_data=f"wallet_transactions_{customer_id}"),
            InlineKeyboardButton("🎁 تراکنش‌های تخفیف", callback_data=f"discount_transactions_{customer_id}")
        ],
        [
            InlineKeyboardButton("📋 تمام تراکنش‌ها", callback_data=f"all_transactions_{customer_id}")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"customer_mgmt_{customer_id}")
        ]
    ]

    return InlineKeyboardMarkup(keyboard)