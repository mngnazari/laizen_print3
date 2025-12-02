# handlers/test_handler.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database.connection
import database.editor_crud as editor_crud
from utils.editor_state_manager import EditorStateManager
import logging

logger = logging.getLogger(__name__)

EDITORS_IDS = [7045273026]  # همان ID ادیتور


async def handle_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر تست برای نمایش دکمه تست"""
    user_id = update.effective_user.id

    # بررسی دسترسی ادیتور
    if user_id not in EDITORS_IDS:
        await update.message.reply_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    # ایجاد کیبورد تست
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 تست - نمایش فایل‌های مورد انتظار", callback_data="test_show_expected_files")]
    ])

    await update.message.reply_text(
        "🧪 **منوی تست ادیتور**\n\nدکمه زیر را برای تست فایل‌های مورد انتظار بزنید:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback برای دکمه تست"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # بررسی دسترسی ادیتور
    if user_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    if query.data == "test_show_expected_files":
        await show_expected_files_test(query, user_id)


async def show_expected_files_test(query, editor_id: int):
    """نمایش فایل‌های مورد انتظار برای تست"""
    logger.info(f"🧪 شروع تست نمایش فایل‌های مورد انتظار برای ادیتور {editor_id}")

    try:
        with database.connection.SessionLocal() as db:
            # دریافت جلسه فعلی ادیتور
            session = editor_crud.get_editor_current_session(db, editor_id)

            if not session:
                await query.edit_message_text(
                    "❌ **هیچ جلسه کاری فعالی یافت نشد**\n\n"
                    "شما در حال حاضر هیچ فایلی برای ادیت دریافت نکرده‌اید."
                )
                return

            # دریافت وضعیت ادیتور
            state_manager = EditorStateManager(db, editor_id)
            current_state = state_manager.get_current_state()

            # دریافت فایل‌های مورد انتظار
            pending_files = editor_crud.get_pending_files_for_editor(db, editor_id)

            # تهیه پیام نتایج
            result_text = f"🧪 **نتایج تست فایل‌های مورد انتظار**\n\n"
            result_text += f"👤 ادیتور: {editor_id}\n"
            result_text += f"📊 وضعیت فعلی: {state_manager.get_state_description(current_state)}\n"
            result_text += f"🆔 شناسه جلسه: {session.id}\n\n"

            if not pending_files:
                result_text += "✅ **هیچ فایل در انتظار دریافت نیست**\n\n"

                # نمایش همه فایل‌ها (کامل و ناکامل)
                from database.editor_models import ProcessedFile, EditorOriginalFile
                all_files = db.query(ProcessedFile).join(EditorOriginalFile).filter(
                    EditorOriginalFile.session_id == session.id
                ).all()

                if all_files:
                    result_text += f"📋 **همه فایل‌های جلسه ({len(all_files)} مورد):**\n"
                    for i, pf in enumerate(all_files, 1):
                        status_icon = "✅" if pf.is_completed else "⏳"
                        result_text += f"{i}. {status_icon} `{pf.processed_filename}`\n"

                        # جزئیات نیازها
                        reqs = []
                        if pf.stl_required:
                            reqs.append(f"STL:{'✅' if pf.stl_received else '❌'}")
                        if pf.jpg_required:
                            reqs.append(f"JPG:{'✅' if pf.jpg_received else '❌'}")
                        if pf.zip_required:
                            reqs.append(f"ZIP:{'✅' if pf.zip_received else '❌'}")

                        if reqs:
                            result_text += f"   └ {' | '.join(reqs)}\n"

            else:
                result_text += f"⏳ **فایل‌های در انتظار دریافت ({len(pending_files)} مورد):**\n\n"

                # گروه‌بندی بر اساس نوع فایل
                stl_files = []
                jpg_files = []
                zip_files = []

                for pf in pending_files:
                    base_name = pf.processed_filename.rsplit('.', 1)[
                        0] if '.' in pf.processed_filename else pf.processed_filename

                    if pf.stl_required and not pf.stl_received:
                        stl_files.append(f"`{base_name}.stl`")
                    if pf.jpg_required and not pf.jpg_received:
                        jpg_files.append(f"`{base_name}.jpg`")
                    if pf.zip_required and not pf.zip_received:
                        zip_files.append(f"`{base_name}.zip`")

                if stl_files:
                    result_text += f"📄 **فایل‌های STL ({len(stl_files)} مورد):**\n"
                    for file in stl_files:
                        result_text += f"  • {file}\n"
                    result_text += "\n"

                if jpg_files:
                    result_text += f"📸 **فایل‌های JPG ({len(jpg_files)} مورد):**\n"
                    for file in jpg_files:
                        result_text += f"  • {file}\n"
                    result_text += "\n"

                if zip_files:
                    result_text += f"📦 **فایل‌های ZIP ({len(zip_files)} مورد):**\n"
                    for file in zip_files:
                        result_text += f"  • {file}\n"
                    result_text += "\n"

            # اضافه کردن جزئیات فنی برای debug
            result_text += f"🔧 **جزئیات فنی:**\n"
            result_text += f"• تعداد فایل‌های اصلی: {session.original_file_count}\n"
            result_text += f"• نقشه دریافت شده: {'✅' if session.file_mapping else '❌'}\n"

            if session.mapping_received_at:
                result_text += f"• زمان دریافت نقشه: {session.mapping_received_at.strftime('%Y-%m-%d %H:%M:%S')}\n"

            # دکمه بازگشت
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 بروزرسانی", callback_data="test_show_expected_files")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="test_main_menu")]
            ])

            await query.edit_message_text(
                result_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            logger.info(f"✅ تست فایل‌های مورد انتظار با موفقیت انجام شد")

    except Exception as e:
        logger.error(f"💥 خطا در تست فایل‌های مورد انتظار: {e}", exc_info=True)

        await query.edit_message_text(
            f"❌ **خطا در تست**\n\n"
            f"خطا در دریافت فایل‌های مورد انتظار:\n"
            f"`{str(e)}`\n\n"
            f"لطفاً لاگ‌ها را بررسی کنید.",
            parse_mode="Markdown"
        )


async def handle_test_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی تست"""
    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 تست - نمایش فایل‌های مورد انتظار", callback_data="test_show_expected_files")]
    ])

    await query.edit_message_text(
        "🧪 **منوی تست ادیتور**\n\nدکمه زیر را برای تست فایل‌های مورد انتظار بزنید:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


# برای اضافه کردن به main.py:
"""
# در main.py این خطوط را اضافه کنید:

from handlers.test_handler import handle_test_command, handle_test_callback, handle_test_main_menu

# Command handler
application.add_handler(CommandHandler("test", handle_test_command))

# Callback handlers
application.add_handler(CallbackQueryHandler(handle_test_callback, pattern="^test_show_expected_files$"))
application.add_handler(CallbackQueryHandler(handle_test_main_menu, pattern="^test_main_menu$"))
"""