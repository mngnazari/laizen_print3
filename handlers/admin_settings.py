# handlers/admin_settings.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, CommandHandler, \
    filters
from keyboards.admin_settings import get_admin_settings_keyboard
import database.connection
from database.models import DeliverySchedule
import logging

logger = logging.getLogger(__name__)


async def show_admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیمات ادمین"""
    if hasattr(update, 'callback_query') and update.callback_query:
        query = update.callback_query
        await query.answer()

        keyboard = get_admin_settings_keyboard()

        message = (
            "⚙️ **تنظیمات سیستم**\n\n"
            "💡 **گزینه‌های موجود:**\n"
            "📅 **روزهای تعطیل:** تعیین تقویم کاری\n"
            "⏰ **زمان‌بندی تحویل:** تنظیم ساعات تحویل\n"
            "📊 **آمار تنظیمات:** مشاهده وضعیت فعلی\n\n"
            "لطفاً گزینه مورد نظر را انتخاب کنید:"
        )

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        keyboard = get_admin_settings_keyboard()

        message = (
            "⚙️ **تنظیمات سیستم**\n\n"
            "💡 **گزینه‌های موجود:**\n"
            "📅 **روزهای تعطیل:** تعیین تقویم کاری\n"
            "⏰ **زمان‌بندی تحویل:** تنظیم ساعات تحویل\n"
            "📊 **آمار تنظیمات:** مشاهده وضعیت فعلی\n\n"
            "لطفاً گزینه مورد نظر را انتخاب کنید:"
        )

        await update.message.reply_text(
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def show_settings_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار تنظیمات"""
    query = update.callback_query
    await query.answer()

    try:
        from .holiday_manager import get_holiday_statistics
        holiday_stats = get_holiday_statistics()

        with database.connection.SessionLocal() as db:
            delivery_schedules = db.query(DeliverySchedule).filter(
                DeliverySchedule.is_active == True
            ).order_by(DeliverySchedule.delivery_number).all()

        message = (
            "📊 **آمار تنظیمات سیستم**\n\n"
            "📅 **روزهای تعطیل (90 روز آینده):**\n"
            f"🔴 تعطیلات: {holiday_stats['total_holidays_90_days']} روز\n"
            f"🟢 روزهای کاری: {holiday_stats['working_days_90_days']} روز\n\n"
            "⏰ **تنظیمات تحویل:**\n"
        )

        if delivery_schedules:
            message += f"🔢 تعداد تحویل روزانه: {len(delivery_schedules)} بار\n\n"

            for schedule in delivery_schedules:
                day_text = {0: "همان روز", -1: "روز قبل"}.get(schedule.cutoff_day_offset,
                                                              f"روز {schedule.cutoff_day_offset:+d}")

                message += f"**تحویل {schedule.delivery_number}:**\n"
                message += f"• مرجع: {schedule.cutoff_time} ({day_text})\n"
                message += f"• فاصله: {schedule.delivery_offset_hours} ساعت\n\n"
        else:
            message += "❌ هنوز تنظیم نشده\n\n"

        message += "💡 **راهنما:**\n"
        message += "• تنظیمات را از منوی بالا ویرایش کنید\n"
        message += "• تغییرات فوراً اعمال می‌شوند"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_settings_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_settings")]
        ])

        await query.edit_message_text(
            text=message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Error showing settings statistics: {e}")
        await query.edit_message_text(
            "❌ خطایی در بارگذاری آمار رخ داد.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_settings")]
            ])
        )


async def handle_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback های تنظیمات"""
    query = update.callback_query

    if query.data == "admin_holidays":
        from .holiday_manager import show_holiday_calendar
        await show_holiday_calendar(update, context)
    elif query.data == "admin_settings_stats":
        await show_settings_statistics(update, context)
    elif query.data == "back_to_admin_settings":
        await show_admin_settings(update, context)
    elif query.data.startswith("holiday_toggle_"):
        from .holiday_manager import toggle_holiday
        await toggle_holiday(update, context)
    else:
        await query.answer("گزینه نامشخص")


async def handle_delivery_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع conversation تنظیم تحویل"""
    from .delivery_scheduler import start_delivery_setup, GET_DELIVERY_COUNT
    return await start_delivery_setup(update, context)


def get_delivery_schedule_conversation():
    """ایجاد ConversationHandler برای تنظیم زمان‌بندی تحویل"""
    from .delivery_scheduler import (
        get_delivery_count,
        get_cutoff_time,
        get_offset_hours,
        get_edit_deadline,  # اضافه شده
        cancel_delivery_setup,
        GET_DELIVERY_COUNT,
        GET_CUTOFF_TIME,
        GET_OFFSET_HOURS,
        GET_EDIT_DEADLINE  # اضافه شده
    )

    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                handle_delivery_start,
                pattern=r'^admin_delivery_schedule$'
            )
        ],
        states={
            GET_DELIVERY_COUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_delivery_count)
            ],
            GET_CUTOFF_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_cutoff_time)
            ],
            GET_OFFSET_HOURS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_offset_hours)
            ],
            GET_EDIT_DEADLINE: [  # اضافه شده
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_edit_deadline)
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_delivery_setup, pattern=r'^cancel_delivery_setup$'),
            CommandHandler('cancel', cancel_delivery_setup)
        ],
        conversation_timeout=300
    )

WAITING_EDITOR_DELAY = 100





# در handlers/admin_settings.py - تغییر تابع:

async def show_editor_delay_menu(query_or_update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیم تاخیر دسترسی ادیتورها"""

    with database.connection.SessionLocal() as db:
        current_delay = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

    message = (
        f"⚙️ **تنظیمات تاخیر دسترسی ادیتورها**\n\n"
        f"📊 **وضعیت فعلی:**\n"
        f"⏰ تاخیر: {current_delay} دقیقه\n\n"
    )

    if current_delay == "0":
        message += "⚡ **حالت تست فعال است**\nادیتورها فوری فایل‌ها را می‌بینند\n\n"
    else:
        message += f"🔒 ادیتورها {current_delay} دقیقه بعد فایل‌ها را می‌بینند\n\n"

    message += (
        "💡 **توضیحات:**\n"
        "• 0 = فوری (برای تست)\n"
        "• 1 = 1 دقیقه تاخیر\n"
        "• 5 = 5 دقیقه تاخیر\n"
        "• 60 = 1 ساعت تاخیر\n\n"
        "برای تغییر، دستور /setdelay را استفاده کنید"
    )

    from keyboards.admin_settings import get_admin_settings_keyboard
    keyboard = get_admin_settings_keyboard()

    # تشخیص اینکه callback query هست یا update
    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await query_or_update.message.reply_text(message, parse_mode="Markdown")

async def start_editor_delay_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند تنظیم تاخیر"""

    with database.connection.SessionLocal() as db:
        current_delay = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

    keyboard = [[KeyboardButton("❌ انصراف")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"⏰ **تنظیم تاخیر دسترسی ادیتورها**\n\n"
        f"📊 مقدار فعلی: **{current_delay} دقیقه**\n\n"
        f"لطفاً مقدار جدید را به **دقیقه** وارد کنید:\n\n"
        f"مثال‌ها:\n"
        f"• 0 (فوری - برای تست)\n"
        f"• 1 (1 دقیقه)\n"
        f"• 5 (5 دقیقه)\n"
        f"• 60 (1 ساعت)",
        reply_markup=reply_markup
    )

    return WAITING_EDITOR_DELAY


async def save_editor_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره مقدار تاخیر جدید"""

    text = update.message.text.strip()

    if text == "❌ انصراف":
        await update.message.reply_text("عملیات لغو شد.")
        return ConversationHandler.END

    try:
        delay = int(text)

        if delay < 0:
            await update.message.reply_text(
                "❌ مقدار نمی‌تواند منفی باشد!\n"
                "لطفاً یک عدد مثبت یا صفر وارد کنید."
            )
            return WAITING_EDITOR_DELAY

        # ذخیره در دیتابیس
        with database.connection.SessionLocal() as db:
            database.crud.set_system_setting(
                db,
                "editor_access_delay_minutes",
                str(delay),
                "تاخیر دسترسی ادیتورها به فایل‌های جدید (به دقیقه)"
            )

            # بررسی ذخیره‌سازی موفق
            saved_value = database.crud.get_system_setting(db, "editor_access_delay_minutes", "-1")

            if saved_value != str(delay):
                await update.message.reply_text(
                    f"❌ خطا در ذخیره‌سازی!\n"
                    f"مقدار وارد شده: {delay}\n"
                    f"مقدار ذخیره شده: {saved_value}"
                )
                return ConversationHandler.END

        # پیام موفقیت
        if delay == 0:
            status_msg = (
                "⚡ **حالت تست فعال شد**\n\n"
                "ادیتورها فایل‌ها را **فوری** می‌بینند\n"
                "نوتیفیکیشن‌ها **بلافاصله** ارسال می‌شوند\n"
                "مشتری‌ها **بدون محدودیت** می‌توانند ویرایش کنند"
            )
        else:
            status_msg = (
                f"🔒 **تاخیر دسترسی تنظیم شد**\n\n"
                f"⏰ تاخیر: **{delay} دقیقه**\n\n"
                f"📌 تأثیرات:\n"
                f"• ادیتورها {delay} دقیقه بعد فایل‌ها را می‌بینند\n"
                f"• نوتیفیکیشن‌ها {delay} دقیقه بعد ارسال می‌شوند\n"
                f"• مشتری‌ها تا {delay} دقیقه می‌توانند ویرایش کنند"
            )

        await update.message.reply_text(
            f"✅ **تنظیمات با موفقیت ذخیره شد!**\n\n{status_msg}"
        )

        logger.info(f"✅ تاخیر دسترسی ادیتورها به {delay} دقیقه تنظیم شد")

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text(
            "❌ **ورودی نامعتبر!**\n\n"
            "لطفاً یک عدد صحیح وارد کنید.\n"
            "مثال: 0 یا 1 یا 5 یا 60"
        )
        return WAITING_EDITOR_DELAY
    except Exception as e:
        logger.error(f"خطا در ذخیره تاخیر: {e}")
        await update.message.reply_text(
            f"❌ خطایی رخ داد:\n{str(e)}"
        )
        return ConversationHandler.END


async def cancel_editor_delay_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند تنظیم"""
    await update.message.reply_text("❌ عملیات لغو شد.")
    return ConversationHandler.END


# در handlers/admin_settings.py - اضافه کن:

from telegram import InlineKeyboardMarkup, InlineKeyboardButton


async def show_editor_delay_menu_inline(query, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیم تاخیر دسترسی ادیتورها - نسخه inline"""

    with database.connection.SessionLocal() as db:
        current_delay = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

    message = (
        f"⚙️ **تنظیمات تاخیر دسترسی ادیتورها**\n\n"
        f"📊 **وضعیت فعلی:**\n"
        f"⏰ تاخیر: {current_delay} دقیقه\n\n"
    )

    if current_delay == "0":
        message += "⚡ **حالت تست فعال است**\nادیتورها فوری فایل‌ها را می‌بینند\n\n"
    else:
        message += f"🔒 ادیتورها {current_delay} دقیقه بعد فایل‌ها را می‌بینند\n\n"

    message += (
        "💡 **توضیحات:**\n"
        "• 0 = فوری (برای تست)\n"
        "• 1 = 1 دقیقه تاخیر\n"
        "• 5 = 5 دقیقه تاخیر\n"
        "• 60 = 1 ساعت تاخیر\n\n"
        "⚡ **برای تغییر از دستور زیر استفاده کنید:**\n"
        "`/setdelay 1`"
    )

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data="admin_settings")
    ]])

    await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")


# در handlers/admin_settings.py

from config import ADMIN_ID


async def cmd_set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور مستقیم برای تنظیم تاخیر: /setdelay 5"""

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        if not context.args:
            with database.connection.SessionLocal() as db:
                current = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

            await update.message.reply_text(
                f"📊 مقدار فعلی: {current} دقیقه\n\n"
                f"برای تغییر:\n/setdelay 0\n/setdelay 1\n/setdelay 5"
            )
            return

        delay = int(context.args[0])

        if delay < 0:
            await update.message.reply_text("❌ عدد نباید منفی باشه!")
            return

        with database.connection.SessionLocal() as db:
            database.crud.set_system_setting(
                db,
                "editor_access_delay_minutes",
                str(delay),
                "تاخیر دسترسی ادیتورها"
            )

            # تست خواندن
            saved = database.crud.get_system_setting(db, "editor_access_delay_minutes", "-1")

        if saved == str(delay):
            await update.message.reply_text(
                f"✅ ذخیره شد!\n"
                f"⏰ تاخیر: {delay} دقیقه\n"
                f"🔍 تست خواندن: {saved} دقیقه"
            )
        else:
            await update.message.reply_text(
                f"❌ خطا!\n"
                f"وارد شده: {delay}\n"
                f"ذخیره شده: {saved}"
            )

    except (ValueError, IndexError):
        await update.message.reply_text("❌ استفاده: /setdelay 5")