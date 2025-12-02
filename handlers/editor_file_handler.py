# handlers/editor_file_handler.py
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
import logging

import database.connection
import database.models
from utils.editor_state_manager import EditorStateManager
from keyboards.editor_status import get_editor_status_keyboard
from config import EDITORS_IDS
logger = logging.getLogger(__name__)




async def handle_editor_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت آپلود فایل‌های ادیتور"""
    user_id = update.effective_user.id

    # بررسی مجوز ادیتور
    if user_id not in EDITORS_IDS:
        await update.message.reply_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, user_id)

        # مدیریت فایل متنی (فایل نقشه)
        if update.message.document and update.message.document.file_name.lower().endswith('.txt'):
            await handle_mapping_file(update, context, state_manager, db)

        # مدیریت فایل‌های پردازش شده
        elif update.message.document:
            await handle_processed_file(update, context, state_manager, db)

        else:
            await update.message.reply_text("لطفاً فقط فایل آپلود کنید.")


async def handle_mapping_file(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              state_manager: EditorStateManager, db: Session):
    """مدیریت فایل نقشه"""
    try:
        # دانلود محتوای فایل
        file = await context.bot.get_file(update.message.document.file_id)
        file_content = await file.download_as_bytearray()
        content_text = file_content.decode('utf-8')

        filename = update.message.document.file_name

        # پردازش فایل نقشه
        success, message = state_manager.process_file_reception(filename, file.file_id, content_text)

        if success:
            await update.message.reply_text(
                f"✅ {message}",
                parse_mode="Markdown"
            )

            # ارسال کیبورد وضعیت
            keyboard = get_editor_status_keyboard(db, update.effective_user.id)
            await update.message.reply_text(
                "📊 **وضعیت شما به‌روزرسانی شد**",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ {message}")

    except Exception as e:
        logger.error(f"خطا در پردازش فایل نقشه: {e}")
        await update.message.reply_text("❌ خطا در پردازش فایل نقشه. لطفاً دوباره تلاش کنید.")


async def handle_processed_file(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                state_manager: EditorStateManager, db: Session):
    """مدیریت فایل‌های پردازش شده (STL, JPG, ZIP)"""
    try:
        filename = update.message.document.file_name
        file_id = update.message.document.file_id

        # پردازش فایل
        success, message = state_manager.process_file_reception(filename, file_id)

        if success:
            await update.message.reply_text(f"✅ {message}")

            # اگر همه فایل‌ها تکمیل شده، کیبورد اصلی ارسال کن
            if "تبریک" in message:
                from keyboards.editor import get_editor_main_keyboard
                keyboard = get_editor_main_keyboard()
                await update.message.reply_text(
                    "🎉 **کار شما تکمیل شد!**\n\nاکنون می‌توانید فایل‌های جدید دریافت کنید.",
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text(f"❌ {message}")

    except Exception as e:
        logger.error(f"خطا در پردازش فایل: {e}")
        await update.message.reply_text("❌ خطا در پردازش فایل. لطفاً دوباره تلاش کنید.")


async def show_editor_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت کامل ادیتور"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, user_id)
        status = state_manager.get_detailed_status()

        status_text = f"""📊 **وضعیت ادیتور**

🔹 **وضعیت فعلی:** {status['state_description']}

📈 **آمار کار:**
• فایل‌های اصلی دریافتی: {status['stats']['original_file_count']}
• کل فایل‌های مورد انتظار: {status['stats']['total_files']}
• فایل‌های تکمیل شده: {status['stats']['completed_files']}
• فایل‌های باقی‌مانده: {status['stats']['pending_files']}

🗺️ **فایل نقشه:** {'✅ دریافت شده' if status['stats']['mapping_received'] else '❌ دریافت نشده'}

🔄 **عملیات مجاز:**
• دریافت فایل جدید: {'✅' if status['can_receive_new_files'] else '❌'}
• ارسال فایل نقشه: {'✅' if status['can_receive_mapping'] else '❌'}
• ارسال فایل‌های پردازش شده: {'✅' if status['can_receive_processed_files'] else '❌'}"""

        keyboard = get_editor_status_keyboard(db, user_id)
        await query.edit_message_text(
            status_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def show_pending_files_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست فایل‌های باقی‌مانده"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, user_id)
        pending_list = state_manager.get_pending_files_list()

        keyboard = get_editor_status_keyboard(db, user_id)
        await query.edit_message_text(
            f"📋 **فایل‌های باقی‌مانده**\n\n{pending_list}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )


async def show_editor_status_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی وضعیت ادیتور"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        keyboard = get_editor_status_keyboard(db, user_id)
        await query.edit_message_text(
            "📊 **منوی وضعیت ادیتور**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )