# handlers/editor.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database.crud
import database.connection
import database.models
import database.editor_crud as editor_crud
from keyboards.editor import (
    get_editor_main_keyboard,
    get_editor_delivery_times_keyboard,
    get_editor_customers_keyboard,
    get_editor_reply_keyboard
)
from utils.editor_state_manager import EditorStateManager
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import joinedload
from utils.timezone_utils import format_shamsi_short, format_shamsi

# تنظیم لاگر
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EDITORS_IDS = [7045273026]


def get_shamsi_time_display(file_order):
    """تبدیل زمان به فرمت شمسی برای نمایش"""
    try:
        if file_order.edit_deadline:
            return format_shamsi_short(file_order.edit_deadline)
        elif file_order.delivery_datetime:
            # محاسبه 18 ساعت قبل از تحویل
            time_obj = file_order.delivery_datetime - timedelta(hours=18)
            return format_shamsi_short(time_obj)
        else:
            return "نامشخص"
    except Exception as e:
        logger.error(f"خطا در تبدیل تاریخ: {e}")
        return "نامشخص"


async def handle_editor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت منوی ادیتور"""
    logger.info(f"🎛️ درخواست منوی ادیتور از کاربر {update.effective_user.id}")

    if update.effective_user.id not in EDITORS_IDS:
        logger.warning(f"🚫 کاربر غیرمجاز {update.effective_user.id}")
        await update.message.reply_text("شما اجازه دسترسی به بخش ادیتور ندارید.")
        return

    logger.info(f"✅ کاربر {update.effective_user.id} مجاز برای دسترسی به بخش ادیتور")

    # ارسال کیبورد ثابت
    reply_keyboard = get_editor_reply_keyboard()
    await update.message.reply_text(
        "🔧 **خوش آمدید به بخش ادیتور**",
        reply_markup=reply_keyboard,

    )

    # ارسال منوی شیشه‌ای اصلی
    inline_keyboard = get_editor_main_keyboard()
    await update.message.reply_text(
        "🔧 **منوی ادیتور**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
        reply_markup=inline_keyboard,

    )
    logger.info("📤 منوی ادیتور ارسال شد")


async def handle_editor_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت آپلود فایل‌های ادیتور"""
    user_id = update.effective_user.id

    # بررسی مجوز ادیتور
    if user_id not in EDITORS_IDS:
        return  # رها کردن بدون پیام برای عدم تداخل

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, user_id)

        # مدیریت فایل متنی (فایل نقشه)
        if update.message.document and update.message.document.file_name.lower().endswith('.txt'):
            await handle_mapping_file(update, context, state_manager, db)

        # مدیریت فایل‌های پردازش شده
        elif update.message.document:
            await handle_processed_file(update, context, state_manager, db)


async def handle_mapping_file(update: Update, context: ContextTypes.DEFAULT_TYPE,
                              state_manager: EditorStateManager, db):
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
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")

    except Exception as e:
        logger.error(f"خطا در پردازش فایل نقشه: {e}")
        await update.message.reply_text("❌ خطا در پردازش فایل نقشه. لطفاً دوباره تلاش کنید.")


async def handle_processed_file(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                state_manager: EditorStateManager, db):
    """مدیریت فایل‌های پردازش شده (STL, JPG, ZIP)"""
    try:
        filename = update.message.document.file_name
        file_id = update.message.document.file_id

        # پردازش فایل
        success, message = state_manager.process_file_reception(filename, file_id)

        if success:
            await update.message.reply_text(f"✅ {message}")

            # اگر همه فایل‌ها تکمیل شده
            if "تبریک" in message:
                await update.message.reply_text(
                    "🎉 **کار شما تکمیل شد!**\n\nاکنون می‌توانید فایل‌های جدید دریافت کنید.",

                )
        else:
            await update.message.reply_text(f"❌ {message}")

    except Exception as e:
        logger.error(f"خطا در پردازش فایل: {e}")
        await update.message.reply_text("❌ خطا در پردازش فایل. لطفاً دوباره تلاش کنید.")


async def show_editor_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی ادیتور"""
    query = update.callback_query
    await query.answer()

    logger.info(f"🏠 نمایش منوی اصلی ادیتور برای کاربر {query.from_user.id}")

    keyboard = get_editor_main_keyboard()
    await query.edit_message_text(
        "🔧 **منوی ادیتور**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
        reply_markup=keyboard,

    )
    logger.info("✅ منوی اصلی ادیتور نمایش داده شد")


async def show_editor_pending_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش فایل‌های در انتظار ادیت - با فیلتر دسترسی"""
    query = update.callback_query
    await query.answer()

    logger.info(f"📋 ادیتور {query.from_user.id} درخواست فایل‌های pending کرد")

    try:
        with database.connection.SessionLocal() as db:
            # دریافت فایل‌های قابل دسترس
            accessible_files = editor_crud.get_accessible_files_for_editor(db, "pending")

            if not accessible_files:
                # چک کن آیا اصلاً فایل pending وجود داره
                all_pending_count = db.query(database.models.FileOrder).filter(
                    database.models.FileOrder.status == "pending"
                ).count()

                if all_pending_count > 0:
                    # فایل‌ها هستن ولی هنوز قابل دسترس نیستن
                    delay_minutes = int(database.crud.get_system_setting(
                        db, "editor_access_delay_minutes", "0"
                    ))

                    await query.edit_message_text(
                        f"⏳ **فایل‌های در انتظار ادیت**\n\n"
                        f"📊 تعداد کل فایل‌های pending: {all_pending_count}\n"
                        f"🔒 فایل‌های قابل دسترس: 0\n\n"
                        f"⏰ زمان تاخیر دسترسی: {delay_minutes} دقیقه\n\n"
                        f"💡 فایل‌ها بعد از سپری شدن زمان تعیین‌شده برای شما قابل مشاهده خواهند بود.",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="editor_pending_files")],
                            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="editor_main_menu")]
                        ])
                    )
                else:
                    await query.edit_message_text(
                        "✅ هیچ فایل pending وجود ندارد!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 منوی اصلی", callback_data="editor_main_menu")]
                        ])
                    )
                return

            # گروه‌بندی فایل‌ها بر اساس زمان تحویل
            from collections import defaultdict

            delivery_groups = defaultdict(list)
            for file_order in accessible_files:
                # استفاده از edit_deadline اصلی برای کلید
                if file_order.edit_deadline:
                    time_key = file_order.edit_deadline.strftime("%Y/%m/%d %H:%M")
                elif file_order.delivery_datetime:
                    edit_deadline = file_order.delivery_datetime - timedelta(hours=18)
                    time_key = edit_deadline.strftime("%Y/%m/%d %H:%M")
                else:
                    time_key = "نامشخص"

                delivery_groups[time_key].append(file_order)

            # ساخت کیبورد
            keyboard_buttons = []
            for time_key, files in sorted(delivery_groups.items()):
                count = len(files)

                # نمایش به صورت شمسی برای کاربر
                display_time = get_shamsi_time_display(files[0]) if files else time_key

                keyboard_buttons.append([
                    InlineKeyboardButton(
                        f"🕐 {display_time} ({count} فایل)",
                        callback_data=f"editor_delivery_{time_key}"  # فرمت میلادی کامل
                    )
                ])

            keyboard_buttons.append([
                InlineKeyboardButton("🏠 منوی اصلی", callback_data="editor_main_menu")
            ])

            keyboard = InlineKeyboardMarkup(keyboard_buttons)

            await query.edit_message_text(
                f"📋 **فایل‌های قابل دسترس برای ادیت**\n\n"
                f"📊 تعداد: {len(accessible_files)} فایل\n\n"
                "لطفاً زمان تحویل مورد نظر را انتخاب کنید:",
                reply_markup=keyboard
            )
            logger.info("✅ پیام فایل‌های pending ارسال شد")

    except Exception as e:
        logger.error(f"💥 خطا در نمایش فایل‌های pending: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            "❌ خطایی در بارگذاری فایل‌ها رخ داد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_main_menu")]
            ])
        )

async def show_editor_delivery_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش مشتریان برای زمان تحویل مشخص"""
    query = update.callback_query
    await query.answer()

    logger.info(f"📋 ادیتور {query.from_user.id} درخواست مشتریان برای تحویل: {query.data}")

    delivery_time = query.data.replace("editor_delivery_", "")
    logger.info(f"🕐 زمان تحویل استخراج شده: {delivery_time}")

    try:
        keyboard = get_editor_customers_keyboard(delivery_time)

        # delivery_time از قبل به فرمت شمسی هست (مثل "1404/07/18 - 14:30")
        # برای نمایش همان را استفاده می‌کنیم
        display_time = delivery_time
        logger.info(f"📆 زمان تحویل برای نمایش: {display_time}")

        await query.edit_message_text(
            f"📂 **فایل‌های تحویل {display_time}**\n\n"
            "لطفاً مشتری مورد نظر را انتخاب کنید یا همه را دریافت کنید:",
            reply_markup=keyboard
        )
        logger.info("✅ پیام مشتریان ارسال شد")

    except Exception as e:
        logger.error(f"💥 خطا در نمایش مشتریان: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            "❌ خطایی در بارگذاری مشتریان رخ داد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_pending_files")]
            ])
        )


async def send_files_to_editor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال فایل‌ها به ادیتور - منطق ساده"""
    query = update.callback_query
    await query.answer()

    logger.info(f"📤 درخواست ارسال فایل: {query.data}")

    editor_id = query.from_user.id

    # بررسی وضعیت ادیتور قبل از ارسال
    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, editor_id)

        # اگر ادیتور در وضعیت 3 باشد (منتظر ارسال فایل‌ها)
        if not state_manager.can_receive_new_files():
            pending_files = state_manager.get_pending_files_list()
            await query.edit_message_text(
                f"⚠️ **شما نمی‌توانید فایل جدید دریافت کنید**\n\n"
                f"ابتدا باید فایل‌های باقی‌مانده را ارسال کنید:\n\n{pending_files}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_main_menu")]
                ]),

            )
            return

    # منطق قدیمی - بدون تغییر
    if "editor_send_all_" in query.data:
        delivery_time = query.data.replace("editor_send_all_", "")
        logger.info(f"📦 ارسال همه فایل‌های تحویل: {delivery_time}")
        await send_all_files_for_delivery(query, delivery_time, editor_id)

    elif "editor_send_customer_" in query.data:
        parts = query.data.split("_")
        customer_code = parts[3]
        delivery_time = "_".join(parts[4:])
        logger.info(f"👤 ارسال فایل‌های مشتری {customer_code} برای تحویل {delivery_time}")
        await send_customer_files_for_delivery(query, customer_code, delivery_time, editor_id)



async def send_all_files_for_delivery(query, delivery_time_display: str, editor_id: int):
    """ارسال همه فایل‌های یک زمان تحویل - با فیلتر دسترسی"""
    logger.info(f"🚀 شروع ارسال همه فایل‌های زمان تحویل {delivery_time_display}")

    with database.connection.SessionLocal() as db:
        try:
            # دریافت فایل‌های قابل دسترس (به جای همه فایل‌ها)
            accessible_files = editor_crud.get_accessible_files_for_editor(db, "pending")

            logger.info(f"📊 کل فایل‌های قابل دسترس: {len(accessible_files)}")

            # فیلتر بر اساس delivery_datetime
            matching_files = []
            for file_order in accessible_files:
                if file_order.delivery_datetime:
                    # فرمت تاریخ شمسی برای مقایسه
                    file_delivery_display = format_shamsi(file_order.delivery_datetime, include_time=True)
                    logger.info(f"🔍 مقایسه: '{file_delivery_display}' با '{delivery_time_display}'")
                    if file_delivery_display == delivery_time_display:
                        matching_files.append(file_order)

            logger.info(f"📊 فایل‌های مطابق: {len(matching_files)}")

            if not matching_files:
                await query.edit_message_text("هیچ فایلی یافت نشد.")
                return

            await query.edit_message_text(f"📄 در حال ارسال {len(matching_files)} فایل...")

            # ایجاد session جدید برای ادیتور
            state_manager = EditorStateManager(db, editor_id)
            success, message = state_manager.assign_new_files(matching_files)

            if not success:
                await query.message.reply_text(f"❌ {message}")
                return

            # ارسال فایل‌ها
            assigned_count = 0
            already_assigned_count = 0

            for file_order in matching_files:
                if file_order.assigned_editor_id is None:
                    file_order.assigned_editor_id = editor_id
                    file_order.editor_status = "assigned"
                    file_order.editor_assigned_at = datetime.now()
                    assigned_count += 1
                    caption_prefix = "🆕 جدید"
                else:
                    already_assigned_count += 1
                    if file_order.assigned_editor_id == editor_id:
                        caption_prefix = "📄 شما"
                    else:
                        prev_editor = db.query(database.models.User).filter(
                            database.models.User.id == file_order.assigned_editor_id
                        ).first()
                        prev_editor_name = prev_editor.full_name if prev_editor else "ناشناس"
                        caption_prefix = f"👤 {prev_editor_name}"

                caption = (
                    f"{caption_prefix}\n\n"
                    f"📄 **{file_order.file_name}**\n"
                    f"👤 مشتری: {file_order.user.customer_code} - {file_order.user.full_name}\n"
                    f"🕐 ددتایم ادیت: {get_shamsi_time_display(file_order)}\n"
                    f"📝 توضیحات: {file_order.description or 'ندارد'}"
                )

                try:
                    await query.message.reply_document(
                        document=file_order.file_id,
                        filename=file_order.file_name,
                        caption=caption
                    )
                    logger.info(f"✅ فایل {file_order.file_name} ارسال شد")
                except Exception as e:
                    logger.error(f"❌ خطا در ارسال فایل {file_order.file_name}: {e}")

            db.commit()

            summary = f"✅ **ارسال کامل شد**\n\n"
            summary += f"📊 کل فایل‌ها: {len(matching_files)}\n"
            summary += f"🆕 جدید تخصیص داده شده: {assigned_count}\n"
            summary += f"📋 قبلاً تخصیص داده شده: {already_assigned_count}\n\n"
            summary += "**⚠️ مهم:** پس از پردازش فایل‌ها، ابتدا فایل نقشه (.txt) را ارسال کنید."

            await query.message.reply_text(summary)

        except Exception as e:
            logger.error(f"💥 خطا در ارسال همه فایل‌ها: {e}")
            import traceback
            logger.error(traceback.format_exc())

async def send_customer_files_for_delivery(query, customer_code: str, delivery_time_display: str, editor_id: int):
    """ارسال فایل‌های مشتری خاص - با فیلتر بر اساس delivery_datetime"""
    logger.info(f"👤 شروع ارسال فایل‌های مشتری {customer_code} برای زمان تحویل {delivery_time_display}")

    with database.connection.SessionLocal() as db:
        try:
            # دریافت فایل‌های قابل دسترس برای این مشتری
            accessible_files = editor_crud.get_accessible_files_for_editor(db, "pending")

            # فیلتر بر اساس customer_code
            customer_files = [f for f in accessible_files if f.user and f.user.customer_code == customer_code]

            logger.info(f"📊 کل فایل‌های قابل دسترس مشتری {customer_code}: {len(customer_files)}")

            # فیلتر بر اساس delivery_datetime
            matching_files = []
            for file_order in customer_files:
                if file_order.delivery_datetime:
                    # فرمت تاریخ شمسی برای مقایسه
                    file_delivery_display = format_shamsi(file_order.delivery_datetime, include_time=True)
                    logger.info(f"🔍 مقایسه: '{file_delivery_display}' با '{delivery_time_display}'")
                    if file_delivery_display == delivery_time_display:
                        matching_files.append(file_order)

            logger.info(f"📊 فایل‌های مطابق: {len(matching_files)}")

            if not matching_files:
                await query.edit_message_text(f"هیچ فایلی برای مشتری {customer_code} یافت نشد.")
                return

            await query.edit_message_text(f"📄 در حال ارسال {len(matching_files)} فایل...")

            # ایجاد session برای ادیتور
            state_manager = EditorStateManager(db, editor_id)
            success, message = state_manager.assign_new_files(matching_files)

            if not success:
                await query.message.reply_text(f"❌ {message}")
                return

            assigned_count = 0
            already_assigned_count = 0

            for file_order in matching_files:
                if file_order.assigned_editor_id is None:
                    file_order.assigned_editor_id = editor_id
                    file_order.editor_status = "assigned"
                    file_order.editor_assigned_at = datetime.now()
                    assigned_count += 1
                    caption_prefix = "🆕 جدید"
                else:
                    already_assigned_count += 1
                    if file_order.assigned_editor_id == editor_id:
                        caption_prefix = "📄 شما"
                    else:
                        prev_editor = db.query(database.models.User).filter(
                            database.models.User.id == file_order.assigned_editor_id
                        ).first()
                        prev_editor_name = prev_editor.full_name if prev_editor else "ناشناس"
                        caption_prefix = f"👤 {prev_editor_name}"

                caption = (
                    f"{caption_prefix}\n\n"
                    f"📄 **{file_order.file_name}**\n"
                    f"👤 مشتری: {file_order.user.customer_code} - {file_order.user.full_name}\n"
                    f"🕐 ددتایم ادیت: {get_shamsi_time_display(file_order)}\n"
                    f"📝 توضیحات: {file_order.description or 'ندارد'}"
                )

                try:
                    await query.message.reply_document(
                        document=file_order.file_id,
                        filename=file_order.file_name,
                        caption=caption,

                    )
                    logger.info(f"✅ فایل {file_order.file_name} ارسال شد")
                except Exception as e:
                    logger.error(f"❌ خطا در ارسال فایل {file_order.file_name}: {e}")

            db.commit()

            summary = f"✅ **ارسال کامل شد**\n\n"
            summary += f"👤 مشتری: {customer_code}\n"
            summary += f"📊 کل فایل‌ها: {len(matching_files)}\n"
            summary += f"🆕 جدید تخصیص داده شده: {assigned_count}\n"
            summary += f"📋 قبلاً تخصیص داده شده: {already_assigned_count}\n\n"
            summary += "**⚠️ مهم:** پس از پردازش فایل‌ها، ابتدا فایل نقشه (.txt) را ارسال کنید."

            await query.message.reply_text(summary)

        except Exception as e:
            logger.error(f"💥 خطا در ارسال فایل‌های مشتری {customer_code}: {e}")
            await query.edit_message_text(f"❌ خطایی در ارسال فایل‌های مشتری {customer_code} رخ داد.")


def escape_markdown(text: str) -> str:
    """Escape کردن کاراکترهای خاص Markdown"""
    # کاراکترهای خاص که باید escape شوند
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in escape_chars:
        text = text.replace(char, f'\\{char}')

    return text


async def show_remaining_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش فایل‌های باقی‌مانده - دکمه جدید"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if user_id not in EDITORS_IDS:
        await query.edit_message_text("شما مجاز به استفاده از این بخش نیستید.")
        return

    with database.connection.SessionLocal() as db:
        state_manager = EditorStateManager(db, user_id)
        pending_list = state_manager.get_pending_files_list()

        # Escape کردن متن برای جلوگیری از خطای parsing
        escaped_pending_list = escape_markdown(pending_list)

        await query.edit_message_text(
            f"📋 **فایل‌های باقی‌مانده**\n\n{escaped_pending_list}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="editor_main_menu")]
            ]),
            parse_mode="MarkdownV2"  # استفاده از MarkdownV2 برای escape بهتر
        )


async def handle_editor_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback های ادیتور"""
    query = update.callback_query
    logger.info(f"📘 Editor callback دریافت شد: {query.data} از کاربر {query.from_user.id}")

    if query.from_user.id not in EDITORS_IDS:
        logger.warning(f"🚫 کاربر غیرمجاز {query.from_user.id}")
        await query.answer("شما اجازه دسترسی ندارید!")
        return

    try:
        if query.data == "editor_main_menu":
            await show_editor_main_menu(update, context)

        elif query.data == "editor_pending_files":
            await show_editor_pending_files(update, context)

        elif query.data.startswith("editor_delivery_"):
            await show_editor_delivery_customers(update, context)

        elif query.data.startswith("editor_send_"):
            await send_files_to_editor(update, context)

        elif query.data == "editor_remaining_files":  # دکمه جدید
            await show_remaining_files(update, context)

        elif query.data == "no_files":
            await query.answer("هیچ فایلی موجود نیست!")

        else:
            logger.warning(f"❓ گزینه ناشناخته: {query.data}")
            await query.answer("گزینه نامشخص")

    except Exception as e:
        logger.error(f"💥 خطا در پردازش callback ادیتور {query.data}: {e}")
        await query.answer("خطایی رخ داد!")
        await query.edit_message_text(
            "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="editor_main_menu")]
            ])
        )