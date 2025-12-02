# keyboards/editor_status.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.orm import Session
import database.editor_crud as editor_crud


def get_editor_status_keyboard(db: Session, editor_id: int) -> InlineKeyboardMarkup:
    """کیبورد وضعیت و فایل‌های باقی‌مانده ادیتور"""
    from utils.editor_state_manager import EditorStateManager

    state_manager = EditorStateManager(db, editor_id)
    status = state_manager.get_detailed_status()

    keyboard = []

    # دکمه وضعیت من
    state_desc = status['state_description']
    keyboard.append([InlineKeyboardButton(f"📊 وضعیت من: {state_desc}", callback_data="editor_show_status")])

    # دکمه فایل‌های باقی‌مانده (فقط در حالت انتظار فایل‌ها)
    if status['can_receive_processed_files']:
        pending_count = status['stats']['pending_files']
        keyboard.append(
            [InlineKeyboardButton(f"📋 فایل‌های باقی‌مانده ({pending_count})", callback_data="editor_pending_list")])

    # دکمه بازگشت
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="editor_main_menu")])

    return InlineKeyboardMarkup(keyboard)


def get_editor_main_keyboard_updated(db: Session, editor_id: int) -> InlineKeyboardMarkup:
    """کیبورد اصلی ادیتور با وضعیت به‌روز"""
    from utils.editor_state_manager import EditorStateManager

    state_manager = EditorStateManager(db, editor_id)
    status = state_manager.get_detailed_status()

    keyboard = []

    # دکمه فایل‌های در انتظار ادیت
    if status['can_receive_new_files']:
        # شمارش فایل‌های جدید کل سیستم
        new_files_count = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending",
            database.models.FileOrder.assigned_editor_id.is_(None)
        ).count()
        keyboard.append([InlineKeyboardButton(f"📝 فایل‌های در انتظار ادیت ({new_files_count})",
                                              callback_data="editor_pending_files")])
    else:
        # نمایش وضعیت فعلی
        keyboard.append([InlineKeyboardButton(f"⏳ {status['state_description']}", callback_data="editor_show_status")])

    # دکمه وضعیت و فایل‌های باقی‌مانده
    keyboard.append([InlineKeyboardButton("📊 وضعیت من", callback_data="editor_status_menu")])

    return InlineKeyboardMarkup(keyboard)


def get_file_assignment_confirmation_keyboard(file_count: int, delivery_info: str) -> InlineKeyboardMarkup:
    """کیبورد تایید اختصاص فایل‌ها"""
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید", callback_data=f"editor_confirm_assignment_{delivery_info}"),
            InlineKeyboardButton("❌ انصراف", callback_data="editor_pending_files")
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_pending_files")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_editor_file_progress_keyboard(db: Session, editor_id: int) -> InlineKeyboardMarkup:
    """کیبورد نمایش پیشرفت کار"""
    keyboard = [
        [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="editor_show_status")],
        [InlineKeyboardButton("📋 فایل‌های باقی‌مانده", callback_data="editor_pending_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)