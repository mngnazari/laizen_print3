# handlers/file_submission.py
import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import asyncio
import database.crud
import database.connection
from database import schemas
from keyboards.file_keyboards import create_initial_keyboard, create_count_keyboard, create_final_cancel_keyboard
from keyboards.customer import get_customer_kb
from .delivery_scheduler import calculate_delivery_time, calculate_file_times
from .holiday_manager import is_holiday, get_next_working_day
from utils.timezone_utils import now_utc, format_shamsi_short

DEFAULT_PRINT_COUNT = 1

logger = logging.getLogger(__name__)

ADMIN_ID = 2138687434
ALLOWED_FORMATS = {'.stl', '.zip', '.rar', '.3dm'}


# در file_submission.py، تابع اعلان به ادیتورها را اضافه کنید:

async def notify_editors_new_file(context, file_info):
    """ارسال اعلان فایل جدید به همه ادیتورها"""
    try:
        from handlers.editor import EDITORS_IDS

        # استفاده از تابع مرکزی برای فرمت تاریخ شمسی
        edit_deadline_str = format_shamsi_short(file_info['edit_deadline'])

        notification_text = (
            f"🆕 **فایل جدید دریافت شد**\n\n"
            f"📄 فایل: {file_info['file_name']}\n"
            f"👤 مشتری: {file_info['customer_code']}\n"
            f"🕐 ددتایم ادیت: {edit_deadline_str}\n"
            f"📝 توضیحات: {file_info['description'] or 'ندارد'}"
        )

        for editor_id in EDITORS_IDS:
            try:
                await context.bot.send_message(
                    chat_id=editor_id,
                    text=notification_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"خطا در ارسال اعلان به ادیتور {editor_id}: {e}")
    except Exception as e:
        logger.error(f"خطا کلی در اعلان ادیتورها: {e}")
# Helper functions
def is_allowed_file(filename: str) -> bool:
    """Check if file format is allowed."""
    if not filename:
        return False
    file_ext = os.path.splitext(filename.lower())[1]
    return file_ext in ALLOWED_FORMATS


def get_persian_datetime() -> str:
    """Get current Persian datetime string (deprecated - استفاده از timezone_utils)"""
    from utils.timezone_utils import format_shamsi, now_iran
    return format_shamsi(now_iran(), include_time=True)


# جایگزین کردن تابع handle_file در file_submission.py:

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles file uploads (documents), saving initial order to DB."""
    message = update.message
    user_id = message.from_user.id
    username = message.from_user.username
    file_obj = message.document

    with database.connection.SessionLocal() as db:
        db_user = database.crud.get_user(db, user_id)
        if not db_user:
            await update.message.reply_text(
                "شما هنوز ثبت‌نام نکرده‌اید. لطفاً ثبت‌نام کنید.",
                reply_markup=get_customer_kb(user_id)
            )
            return

    if not file_obj:
        await message.reply_text("❌ لطفاً یک فایل معتبر ارسال کنید.")
        return

    file_name = file_obj.file_name
    file_size = file_obj.file_size

    if not is_allowed_file(file_name):
        await message.reply_text(
            f"❌ فرمت فایل مجاز نیست!\n\n"
            f"فرمت‌های مجاز: {', '.join(ALLOWED_FORMATS)}"
        )
        return

    edit_deadline = None
    delivery_time = None

    try:
        edit_deadline, delivery_time = calculate_file_times()
        logger.info(f"محاسبه زمان‌ها موفق: ادیت={edit_deadline}, تحویل={delivery_time}")
    except Exception as e:
        logger.error(f"خطا در محاسبه زمان: {e}")
        now = datetime.now()
        delivery_time = now + timedelta(days=1, hours=13)
        edit_deadline = now + timedelta(days=1, hours=19)

    if edit_deadline is None or delivery_time is None:
        now = now_utc()
        delivery_time = now + timedelta(days=1, hours=13)
        edit_deadline = now + timedelta(days=1, hours=19)

    # message.date از تلگرام UTC است - تبدیل به UTC naive
    message_datetime = message.date.replace(tzinfo=None) if message.date.tzinfo else message.date

    order_data = schemas.FileOrderCreate(
        user_id=user_id,
        username=username,
        file_id=file_obj.file_id,
        file_name=file_name,
        file_size=file_size,
        message_id=message.message_id,
        delivery_datetime=delivery_time,
        edit_deadline=edit_deadline,
        print_count=1,
        created_at=message_datetime
    )

    db_order = None
    try:
        with database.connection.SessionLocal() as db:
            db_order = database.crud.create_file_order(db, order_data)
            context.user_data[f'order_user_msg_{message.message_id}'] = db_order.id
        logger.info(f"فایل در دیتابیس ذخیره شد: {db_order.id}")
    except Exception as e:
        logger.error(f"خطا در ذخیره دیتابیس: {e}")
        await message.reply_text("❌ خطا در ذخیره اطلاعات. لطفاً مجدداً تلاش کنید.")
        return

    try:
        # استفاده از تابع مرکزی برای فرمت تاریخ شمسی
        edit_deadline_display = format_shamsi_short(edit_deadline)
        delivery_time_display = format_shamsi_short(delivery_time)
    except Exception as e:
        logger.error(f"خطا در تبدیل تاریخ شمسی: {e}")
        edit_deadline_display = "نامشخص"
        delivery_time_display = "نامشخص"

    # محاسبه زمان باقی‌مانده برای ویرایش
    with database.connection.SessionLocal() as db:
        delay_minutes = int(database.crud.get_system_setting(db, "editor_access_delay_minutes", "1"))

    caption = (
        f"📄 فایل شما دریافت شد!\n\n"
        f"⏱ زمان ویرایش: **{delay_minutes} دقیقه**\n"
        f"🚚 زمان تحویل: {delivery_time_display}\n"
        f"📝 توضیحات: فاقد توضیحات\n\n"
        f"⚠️ شما {delay_minutes} دقیقه فرصت دارید تعداد را تغییر دهید یا سفارش را لغو کنید.\n"
        f"✏️ برای افزودن توضیحات، روی این پیام ریپلای کنید."
    )

    try:
        sent_message = await message.reply_document(
            document=file_obj.file_id,
            caption=caption,
            reply_markup=create_initial_keyboard(1)
        )

        with database.connection.SessionLocal() as db:
            updated_order = database.crud.update_file_order(
                db, db_order.id, message_id=sent_message.message_id
            )
            context.user_data[f'order_bot_msg_{sent_message.message_id}'] = updated_order.id

            if f'order_user_msg_{message.message_id}' in context.user_data:
                del context.user_data[f'order_user_msg_{message.message_id}']

        logger.info(f"فایل با موفقیت ارسال شد: {sent_message.message_id}")

        # نوتیفیکیشن به ادیتورها - با تاخیر یا فوری
        try:
            with database.connection.SessionLocal() as db:
                delay_minutes = int(database.crud.get_system_setting(db, "editor_access_delay_minutes", "0"))

                if delay_minutes == 0:
                    # حالت تست - نوتیفیکیشن فوری
                    from handlers.editor import EDITORS_IDS

                    notification_text = (
                        f"🆕 **فایل جدید دریافت شد**\n\n"
                        f"📄 فایل: {file_name}\n"
                        f"👤 مشتری: {db_user.customer_code}\n"
                        f"🕐 ددتایم ادیت: {edit_deadline_j.strftime('%m/%d-%H:%M')}\n"
                        f"📝 توضیحات: ندارد\n\n"
                        f"⚡ حالت تست فعال - فایل فوری قابل دسترس است"
                    )

                    for editor_id in EDITORS_IDS:
                        try:
                            await context.bot.send_message(
                                chat_id=editor_id,
                                text=notification_text,
                                parse_mode="Markdown"
                            )
                        except Exception as e:
                            logger.error(f"خطا در اعلان فوری به ادیتور {editor_id}: {e}")

                    logger.info("اعلان فوری به ادیتورها ارسال شد (حالت تست)")
                else:
                    # Schedule نوتیفیکیشن تاخیری با asyncio
                    from utils.notification_scheduler import schedule_editor_notification

                    job_data = {
                        'file_name': file_name,
                        'customer_code': db_user.customer_code,
                        'edit_deadline_display': edit_deadline_j.strftime('%m/%d-%H:%M'),
                        'description': None
                    }

                    # محاسبه delay به ثانیه
                    delay_seconds = delay_minutes * 60

                    # اجرای task در background
                    asyncio.create_task(
                        schedule_editor_notification(context.bot, delay_seconds, job_data)
                    )

                    logger.info(f"✅ نوتیفیکیشن برای {delay_minutes} دقیقه ({delay_seconds} ثانیه) بعد schedule شد")

        except Exception as e:
            logger.error(f"خطا در schedule نوتیفیکیشن: {e}")

    except Exception as e:
        logger.error(f"خطا در ارسال فایل: {e}")
        await message.reply_text("❌ خطا در ارسال فایل.")


# در handlers/file_submission.py - تابع handle_reply

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles reply messages for adding descriptions and updates the DB."""
    message = update.message

    if not message.reply_to_message:
        return

    reply_to = message.reply_to_message

    if (reply_to.from_user.id != context.bot.id or
            not reply_to.document or
            not reply_to.reply_markup):
        return

    user_id = message.from_user.id
    description = message.text

    order_id = context.user_data.get(f'order_bot_msg_{reply_to.message_id}')

    if not order_id:
        await message.reply_text("❌ سفارش مورد نظر یافت نشد یا منقضی شده است.")
        return

    try:
        with database.connection.SessionLocal() as db:
            db_order = database.crud.get_file_order_by_id(db, order_id)

            if not db_order or db_order.user_id != user_id:
                await message.reply_text("❌ سفارش مورد نظر یافت نشد.")
                return

            # چک کردن deadline ویرایش
            if db_order.edit_deadline:
                try:
                    now_utc = datetime.now(timezone.utc)

                    if db_order.edit_deadline.tzinfo is None:
                        deadline_utc = db_order.edit_deadline.replace(tzinfo=timezone.utc)
                    else:
                        deadline_utc = db_order.edit_deadline.astimezone(timezone.utc)

                    logger.info(f"Check deadline for reply: now={now_utc}, deadline={deadline_utc}")

                    if now_utc > deadline_utc:
                        time_passed = now_utc - deadline_utc
                        minutes_passed = int(time_passed.total_seconds() / 60)

                        await message.reply_text(
                            f"⏰ **زمان ویرایش به پایان رسید**\n\n"
                            f"متأسفانه فایل شما وارد مرحله پردازش شده و دیگه امکان تغییر توضیحات نیست\n\n"
                            f"📊 مدت زمان سپری شده: {minutes_passed} دقیقه\n\n"
                            f"💡 اگه نیاز به تغییری داری، با پشتیبانی تماس بگیر"
                        )
                        return
                except Exception as e:
                    logger.error(f"خطا در چک deadline: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            database.crud.update_file_order(db, order_id, description=description)

            # فرمت کردن زمان تحویل برای نمایش
            caption_delivery_time = format_shamsi_short(db_order.delivery_datetime) if db_order.delivery_datetime else "نامشخص"

            new_caption = (
                f"🕐 زمان تحویل: {caption_delivery_time}\n"
                f"📝 توضیحات: {description}\n\n"
                f"✏️ برای تغییر توضیحات، مجدداً ریپلای کنید."
            )

            await reply_to.edit_caption(
                caption=new_caption,
                reply_markup=create_initial_keyboard(db_order.print_count)
            )

            await message.reply_text("✅ توضیحات با موفقیت به‌روزرسانی شد.")

    except Exception as e:
        logger.error(f"Error updating description: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await message.reply_text("❌ خطا در به‌روزرسانی توضیحات.")





# در handlers/file_submission.py - تابع handle_callback_query

# در handlers/file_submission.py

# این تابع کامل را در file_submission.py جایگزین handle_callback_query کنید
# (خطوط 399 تا 542)

# ===== file_submission.py =====
# تابع handle_callback_query را با این جایگزین کنید:

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles inline keyboard callbacks and updates the DB."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    message = query.message
    data = query.data

    order_id = context.user_data.get(f'order_bot_msg_{message.message_id}')

    if not order_id:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("❌ سفارش منقضی شده است. لطفاً فایل را مجدداً ارسال کنید.")
        return

    try:
        with database.connection.SessionLocal() as db:
            db_order = database.crud.get_file_order_by_id(db, order_id)

            if not db_order or db_order.user_id != user_id:
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text("❌ سفارش یافت نشد.")
                return

            # چک کردن deadline ویرایش
            if db_order.edit_deadline:
                try:
                    # همه datetime ها در دیتابیس UTC هستن (naive)
                    now_utc_time = now_utc()
                    deadline_utc = db_order.edit_deadline

                    logger.info(f"🔍 چک deadline برای سفارش {order_id}:")
                    logger.info(f"  - فایل: {db_order.file_name}")
                    logger.info(f"  - زمان فعلی (UTC): {now_utc_time}")
                    logger.info(f"  - Edit Deadline (UTC): {deadline_utc}")

                    time_diff_seconds = (deadline_utc - now_utc_time).total_seconds()
                    time_diff_minutes = time_diff_seconds / 60
                    logger.info(f"  - تفاوت: {time_diff_minutes:.2f} دقیقه ({time_diff_seconds:.0f} ثانیه)")

                    if now_utc_time > deadline_utc:
                        minutes_passed = int((now_utc_time - deadline_utc).total_seconds() / 60)
                        logger.info(f"🔒 زمان ویرایش سپری شده - {minutes_passed} دقیقه پیش")

                        await query.answer("⏰ زمان ویرایش سفارش به پایان رسیده است!", show_alert=True)

                        # حذف کیبورد از پیام
                        try:
                            await query.edit_message_reply_markup(reply_markup=None)
                        except Exception as e:
                            logger.warning(f"نتوانست کیبورد را حذف کند: {e}")

                        await query.message.reply_text(
                            f"⏰ **زمان ویرایش به پایان رسید**\n\n"
                            f"فایل شما وارد مرحله پردازش شده و امکان تغییر وجود ندارد.\n\n"
                            f"📊 مدت سپری شده: {minutes_passed} دقیقه\n\n"
                            f"💡 اگر نیاز به تغییری دارید، با پشتیبانی تماس بگیرید.",
                            parse_mode="Markdown"
                        )
                        return
                    else:
                        logger.info(f"✅ هنوز قابل ویرایش است - {abs(time_diff_minutes):.2f} دقیقه مانده")

                except Exception as e:
                    logger.error(f"❌ خطا در چک deadline: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"⚠️ سفارش {order_id} edit_deadline ندارد!")

            temp_count_key = f'temp_print_count_{message.message_id}'

            if data == "edit_count":
                context.user_data[temp_count_key] = db_order.print_count
                await query.edit_message_reply_markup(reply_markup=create_count_keyboard(db_order.print_count))

            elif data == "decrease_count":
                current_temp_count = context.user_data.get(temp_count_key, db_order.print_count)
                if current_temp_count > 1:
                    context.user_data[temp_count_key] = current_temp_count - 1
                    await query.edit_message_reply_markup(
                        reply_markup=create_count_keyboard(context.user_data[temp_count_key]))

            elif data == "increase_count":
                current_temp_count = context.user_data.get(temp_count_key, db_order.print_count)
                context.user_data[temp_count_key] = current_temp_count + 1
                await query.edit_message_reply_markup(
                    reply_markup=create_count_keyboard(context.user_data[temp_count_key]))

            elif data == "show_count":
                pass

            elif data == "confirm_count":
                if temp_count_key in context.user_data:
                    new_count = context.user_data[temp_count_key]
                    database.crud.update_file_order(db, order_id, print_count=new_count)
                    del context.user_data[temp_count_key]
                    db_order.print_count = new_count

                delivery_dt_gregorian_from_db = db_order.delivery_datetime
                caption_delivery_time = format_shamsi_short(delivery_dt_gregorian_from_db) if delivery_dt_gregorian_from_db else "نامشخص"
                description_text = db_order.description or "فاقد توضیحات"
                new_caption = (
                    f"🕐 زمان تحویل: {caption_delivery_time}\n"
                    f"📝 توضیحات: {description_text}\n\n"
                    f"✏️ برای تغییر توضیحات، مجدداً ریپلای کنید."
                )
                await query.edit_message_caption(caption=new_caption,
                                                 reply_markup=create_initial_keyboard(db_order.print_count))

            elif data == "cancel_count_edit":
                if temp_count_key in context.user_data:
                    del context.user_data[temp_count_key]
                await query.edit_message_reply_markup(reply_markup=create_initial_keyboard(db_order.print_count))

            elif data == "cancel_order":
                await query.edit_message_reply_markup(reply_markup=create_final_cancel_keyboard())

            elif data == "confirm_delete":
                database.crud.update_file_order(db, order_id, status="cancelled")
                await query.delete_message()
                await context.bot.send_message(chat_id=user_id, text="❌ فایل و سفارش حذف شد.")
                if f'order_bot_msg_{message.message_id}' in context.user_data:
                    del context.user_data[f'order_bot_msg_{message.message_id}']
                if temp_count_key in context.user_data:
                    del context.user_data[temp_count_key]

            elif data == "back_to_initial":
                await query.edit_message_reply_markup(reply_markup=create_initial_keyboard(db_order.print_count))

    except Exception as e:
        logger.error(f"Callback processing error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.message.reply_text("❌ خطا در پردازش درخواست.")

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """این تابع دیگر استفاده نمی‌شود - handle_reply جایگزین آن شده است."""
    pass


async def cancel_file_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای لغو فرآیند ارسال فایل."""
    await update.message.reply_text("عملیات ارسال فایل لغو شد.",
                                    reply_markup=get_customer_kb(update.effective_user.id))
    return


# در handlers/file_submission.py - اضافه کن:

async def send_delayed_editor_notification(context: ContextTypes.DEFAULT_TYPE):
    """ارسال نوتیفیکیشن تاخیری به ادیتورها"""
    job_data = context.job.data

    try:
        from handlers.editor import EDITORS_IDS

        notification_text = (
            f"🆕 **فایل جدید قابل دسترس**\n\n"
            f"📄 فایل: {job_data['file_name']}\n"
            f"👤 مشتری: {job_data['customer_code']}\n"
            f"🕐 ددتایم ادیت: {job_data['edit_deadline_display']}\n"
            f"📝 توضیحات: {job_data['description'] or 'ندارد'}\n\n"
            f"💡 فایل اکنون آماده دریافت است."
        )

        for editor_id in EDITORS_IDS:
            try:
                await context.bot.send_message(
                    chat_id=editor_id,
                    text=notification_text,
                    parse_mode="Markdown"
                )
                logger.info(f"نوتیفیکیشن تاخیری به ادیتور {editor_id} ارسال شد")
            except Exception as e:
                logger.error(f"خطا در ارسال نوتیفیکیشن به ادیتور {editor_id}: {e}")

    except Exception as e:
        logger.error(f"خطا در ارسال نوتیفیکیشن تاخیری: {e}")