# ایجاد فایل جدید: keyboards/vault_management.py

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List
from database.models import Vault

def get_vaults_list_keyboard(vaults: List[Vault]) -> InlineKeyboardMarkup:
    """کیبورد لیست صندوق‌ها"""
    keyboard = []

    # سورت کردن صندوق‌ها از بیشترین درصد به کمترین
    sorted_vaults = sorted(vaults, key=lambda v: v.allocation_percentage, reverse=True)

    for vault in sorted_vaults:
        # انتخاب ایموجی بر اساس موجودی
        if vault.balance > 0:
            emoji = "💚"
        elif vault.balance < 0:
            emoji = "🔴"
        else:
            emoji = "💰"

        # فرمت: %درصد نام موجودی$
        button_text = f"%{int(vault.allocation_percentage)} {vault.name} ${int(vault.balance)}"

        keyboard.append([InlineKeyboardButton(
            f"{emoji} {button_text}",
            callback_data=f"vault_detail_{vault.id}"
        )])

    # دکمه ایجاد صندوق جدید
    keyboard.append([InlineKeyboardButton(
        "➕ ایجاد صندوق جدید",
        callback_data="vault_create_new"
    )])

    # دکمه بازگشت به منوی صندوق‌ها
    keyboard.append([InlineKeyboardButton(
        "🔙 بازگشت",
        callback_data="admin_vaults_menu"
    )])

    return InlineKeyboardMarkup(keyboard)


def get_vault_detail_keyboard(vault_id: int, vault_name: str = None) -> InlineKeyboardMarkup:
    """کیبورد جزئیات صندوق"""
    keyboard = []

    # اگر صندوق تنخواه گردان است
    if vault_name == "تنخواه گردان":
        keyboard.append([
            InlineKeyboardButton("💸 برداشت و توزیع", callback_data=f"vault_petty_withdraw_{vault_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("📜 ریز تراکنش‌ها", callback_data=f"vault_transactions_{vault_id}"),
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("📊 تنظیم درصد تخصیص", callback_data=f"vault_set_percent_{vault_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("💎 مدیریت دارایی طلا", callback_data=f"gold_menu_{vault_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("📜 ریز تراکنش‌ها", callback_data=f"vault_transactions_{vault_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("✏️ تغییر نام", callback_data=f"vault_rename_{vault_id}"),
        ])
        keyboard.append([
            InlineKeyboardButton("🗑 حذف صندوق", callback_data=f"vault_delete_{vault_id}"),
        ])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="vault_list")
    ])

    return InlineKeyboardMarkup(keyboard)

def get_vault_transactions_keyboard(vault_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """کیبورد نمایش تراکنش‌های صندوق"""
    keyboard = []

    # دکمه‌های صفحه‌بندی در صورت نیاز
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"vault_trans_page_{vault_id}_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"vault_trans_page_{vault_id}_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{vault_id}")])

    return InlineKeyboardMarkup(keyboard)





def get_expense_vault_selection_keyboard(vaults: List[Vault]) -> InlineKeyboardMarkup:
    """کیبورد انتخاب صندوق برای ثبت هزینه"""
    keyboard = []

    for vault in vaults:
        # نمایش همه صندوق‌ها بدون چک موجودی
        keyboard.append([InlineKeyboardButton(
            f"💰 {vault.name} (${vault.balance:.0f})",
            callback_data=f"expense_vault_{vault.id}"
        )])

    keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="vault_list")])

    return InlineKeyboardMarkup(keyboard)


def get_gold_menu_keyboard(vault_id: int) -> InlineKeyboardMarkup:
    """کیبورد منوی مدیریت طلا"""
    keyboard = [
        [
            InlineKeyboardButton("🛒 خرید طلا", callback_data=f"gold_buy_{vault_id}"),
            InlineKeyboardButton("💰 فروش طلا", callback_data=f"gold_sell_{vault_id}"),
        ],
        [
            InlineKeyboardButton("📊 موجودی و آمار", callback_data=f"gold_balance_{vault_id}"),
        ],
        [
            InlineKeyboardButton("📜 تاریخچه معاملات", callback_data=f"gold_history_{vault_id}"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به صندوق", callback_data=f"vault_detail_{vault_id}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_gold_history_keyboard(vault_id: int, page: int = 0) -> InlineKeyboardMarkup:
    """کیبورد تاریخچه معاملات طلا"""
    keyboard = []

    # دکمه‌های صفحه‌بندی در صورت نیاز
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"gold_history_page_{vault_id}_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"gold_history_page_{vault_id}_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"gold_menu_{vault_id}")])

    return InlineKeyboardMarkup(keyboard)