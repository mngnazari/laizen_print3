# handlers/editor_status.py
from telegram import Update
from telegram.ext import ContextTypes
import logging

import database.connection
import database.models
import database.editor_crud as editor_crud
from utils.editor_state_manager import EditorStateManager
from keyboards.editor_status import get_editor_main_keyboard_updated
from config import EDITORS_IDS
logger = logging.getLogger(__name__)




async def assign_files_to_editor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختصاص فایل‌های جدید به ادیتور با بررسی وضعیت"""
    query = update.callback_query
    await query.answer()

    editor_id = query.from_user.id

    if editor_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, editor_id)

        # بررسی امکان دریافت فایل جدید
        if not state_manager.can_receive_new_files():
            status = state_manager.get_detailed_status()
            keyboard = get_editor_main_keyboard_updated(db, editor_id)

            await query.edit_message_text(
                f"❌ **امکان دریافت فایل جدید وجود ندارد**\n\n"
                f"وضعیت فعلی: {status['state_description']}\n\n"
                f"لطفاً ابتدا کار جاری را تکمیل کنید.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return

        # استخراج اطلاعات تحویل از callback data
        if "editor_confirm_assignment_" in query.data:
            delivery_info = query.data.replace("editor_confirm_assignment_", "")
            await confirm_file_assignment(query, editor_id, delivery_info, db)
        elif "editor_send_all_" in query.data:
            delivery_time = query.data.replace("editor_send_all_", "")
            await prepare_file_assignment(query, editor_id, delivery_time, "all", db)
        elif "editor_send_customer_" in query.data:
            parts = query.data.split("_")
            customer_code = parts[3]
            delivery_time = "_".join(parts[4:])
            await prepare_file_assignment(query, editor_id, delivery_time, customer_code, db)


async def prepare_file_assignment(query, editor_id: int, delivery_time: str, assignment_type: str, db):
    """آماده‌سازی اختصاص فایل با نمایش جزئیات"""
    try:
        from datetime import datetime, timedelta

        # دریافت فایل‌های مطابق
        if assignment_type == "all":
            matching_files = get_files_for_edit_deadline(db, delivery_time)
        else:
            matching_files = get_customer_files_for_edit_deadline(db, assignment_type, delivery_time)

        if not matching_files:
            await query.edit_message_text(
                "هیچ فایلی برای اختصاص یافت نشد.",
                reply_markup=get_editor_main_keyboard_updated(db, editor_id)
            )
            return

        # آماده‌سازی متن تایید
        file_list = []
        for i, file_order in enumerate(matching_files[:5], 1):  # نمایش حداکثر 5 فایل اول
            file_list.append(f"{i}. {file_order.file_name} ({file_order.user.customer_code})")

        if len(matching_files) > 5:
            file_list.append(f"... و {len(matching_files) - 5} فایل دیگر")

        confirmation_text = f"""📝 **تایید اختصاص فایل‌ها**

🔹 **تعداد فایل‌ها:** {len(matching_files)}
🔹 **نوع اختصاص:** {"همه فایل‌ها" if assignment_type == "all" else f"مشتری {assignment_type}"}
🔹 **ددتایم ادیت:** {delivery_time}

📋 **نمونه فایل‌ها:**
""" + "\n".join(file_list) + """

آیا مایل به دریافت این فایل‌ها هستید؟"""

        from keyboards.editor_status import get_file_assignment_confirmation_keyboard
        keyboard = get_file_assignment_confirmation_keyboard(len(matching_files), f"{assignment_type}_{delivery_time}")

        await query.edit_message_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"خطا در آماده‌سازی اختصاص فایل: {e}")
        await query.edit_message_text(
            "خطا در آماده‌سازی اختصاص فایل.",
            reply_markup=get_editor_main_keyboard_updated(db, editor_id)
        )


async def confirm_file_assignment(query, editor_id: int, assignment_info: str, db):
    """تایید نهایی اختصاص فایل‌ها"""
    try:
        # تجزیه اطلاعات اختصاص
        parts = assignment_info.split("_", 1)
        assignment_type = parts[0]
        delivery_time = parts[1]

        # دریافت فایل‌های مطابق
        if assignment_type == "all":
            matching_files = get_files_for_edit_deadline(db, delivery_time)
        else:
            matching_files = get_customer_files_for_edit_deadline(db, assignment_type, delivery_time)

        if not matching_files:
            await query.edit_message_text(
                "هیچ فایلی برای اختصاص یافت نشد.",
                reply_markup=get_editor_main_keyboard_updated(db, editor_id)
            )
            return

        # اختصاص فایل‌ها با استفاده از state manager
        state_manager = EditorStateManager(db, editor_id)
        success, message = state_manager.assign_new_files(matching_files)

        if success:
            await query.edit_message_text(f"✅ {message}")

            # ارسال فایل‌ها
            await send_assigned_files_to_editor(query, matching_files, editor_id)

            # نمایش کیبورد به‌روز
            keyboard = get_editor_main_keyboard_updated(db, editor_id)
            await query.message.reply_text(
                "📝 **فایل‌ها اختصاص یافت**\n\nاکنون باید فایل نقشه (.txt) را ارسال کنید.",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"❌ {message}",
                reply_markup=get_editor_main_keyboard_updated(db, editor_id)
            )

    except Exception as e:
        logger.error(f"خطا در تایید اختصاص فایل: {e}")
        await query.edit_message_text(
            "خطا در تایید اختصاص فایل.",
            reply_markup=get_editor_main_keyboard_updated(db, editor_id)
        )


async def send_assigned_files_to_editor(query, file_orders, editor_id: int):
    """ارسال فایل‌های اختصاص یافته به ادیتور"""
    try:
        await query.message.reply_text(f"📤 در حال ارسال {len(file_orders)} فایل...")

        for file_order in file_orders:
            caption = f"""📝 **فایل اختصاص یافته**

📄 **نام فایل:** {file_order.file_name}
👤 **مشتری:** {file_order.user.customer_code} - {file_order.user.full_name}
📅 **زمان ددتایم ادیت:** {get_shamsi_time_display(file_order)}
📝 **توضیحات:** {file_order.description or 'ندارد'}

**⚠️ توجه:** پس از پردازش، ابتدا فایل نقشه (.txt) را ارسال کنید."""

            try:
                await query.message.reply_document(
                    document=file_order.file_id,
                    filename=file_order.file_name,
                    caption=caption,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"خطا در ارسال فایل {file_order.file_name}: {e}")

        await query.message.reply_text(
            "✅ **همه فایل‌ها ارسال شد**\n\n"
            "اکنون فایل‌ها را پردازش کنید و ابتدا فایل نقشه (.txt) را ارسال کنید."
        )

    except Exception as e:
        logger.error(f"خطا در ارسال فایل‌ها: {e}")


def get_files_for_edit_deadline(db, edit_deadline_time: str):
    """دریافت فایل‌های مطابق با ددتایم ادیت"""
    from datetime import datetime, timedelta

    all_files = db.query(database.models.FileOrder).filter(
        database.models.FileOrder.status == "pending",
        database.models.FileOrder.assigned_editor_id.is_(None)
    ).options(database.models.joinedload(database.models.FileOrder.user)).all()

    matching_files = []
    for file_order in all_files:
        file_edit_deadline = None

        if file_order.edit_deadline is not None:
            file_edit_deadline = file_order.edit_deadline
        elif file_order.delivery_datetime is not None:
            file_edit_deadline = file_order.delivery_datetime - timedelta(hours=18)

        if file_edit_deadline:
            file_edit_deadline_str = file_edit_deadline.strftime("%Y/%m/%d %H:%M")
            if file_edit_deadline_str == edit_deadline_time:
                matching_files.append(file_order)

    return matching_files


def get_customer_files_for_edit_deadline(db, customer_code: str, edit_deadline_time: str):
    """دریافت فایل‌های مشتری خاص برای ددتایم ادیت"""
    from datetime import datetime, timedelta

    all_files = db.query(database.models.FileOrder).join(database.models.User).filter(
        database.models.FileOrder.status == "pending",
        database.models.FileOrder.assigned_editor_id.is_(None),
        database.models.User.customer_code == customer_code
    ).options(database.models.joinedload(database.models.FileOrder.user)).all()

    matching_files = []
    for file_order in all_files:
        file_edit_deadline = None

        if file_order.edit_deadline is not None:
            file_edit_deadline = file_order.edit_deadline
        elif file_order.delivery_datetime is not None:
            file_edit_deadline = file_order.delivery_datetime - timedelta(hours=18)

        if file_edit_deadline:
            file_edit_deadline_str = file_edit_deadline.strftime("%Y/%m/%d %H:%M")
            if file_edit_deadline_str == edit_deadline_time:
                matching_files.append(file_order)

    return matching_files


def get_shamsi_time_display(file_order):
    """تبدیل زمان به فرمت شمسی برای نمایش"""
    try:
        import jdatetime
        from datetime import timedelta

        if file_order.edit_deadline:
            time_obj = file_order.edit_deadline
        elif file_order.delivery_datetime:
            time_obj = file_order.delivery_datetime - timedelta(hours=18)
        else:
            return "نامشخص"

        shamsi_time = jdatetime.datetime.fromtimestamp(time_obj.timestamp())
        return shamsi_time.strftime('%m/%d-%H:%M')
    except Exception as e:
        logger.error(f"خطا در تبدیل تاریخ: {e}")
        return "نامشخص"