# handlers/file_archive.py - نسخه به‌روزرسانی شده
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database.crud
import database.connection
from database.models import FileOrder
from keyboards.customer import get_customer_kb
from datetime import datetime, timedelta
from sqlalchemy import and_
import jdatetime
import logging

logger = logging.getLogger(__name__)


def gregorian_to_jalali(gregorian_date):
    """تبدیل تاریخ میلادی به شمسی"""
    try:
        j_date = jdatetime.datetime.fromgregorian(datetime=gregorian_date)
        return j_date.strftime('%Y/%m/%d')
    except:
        return gregorian_date.strftime('%Y/%m/%d')


def gregorian_to_jalali_with_time(gregorian_datetime):
    """تبدیل تاریخ و ساعت میلادی به شمسی"""
    try:
        j_datetime = jdatetime.datetime.fromgregorian(datetime=gregorian_datetime)
        return j_datetime.strftime('%Y/%m/%d - %H:%M')
    except:
        return gregorian_datetime.strftime('%Y/%m/%d - %H:%M')


def get_file_archive_keyboard(weekly_count: int, monthly_count: int, total_count: int):
    """کیبورد شیشه‌ای آرشیو فایل‌ها با پیوند منحصر به فرد"""
    keyboard = [
        [
            InlineKeyboardButton(f"📅 هفته اخیر ({weekly_count})", callback_data="ARCHIVE_WEEK_7"),
            InlineKeyboardButton(f"📆 ماه اخیر ({monthly_count})", callback_data="ARCHIVE_MONTH_30"),
            InlineKeyboardButton(f"📋 کل ({total_count})", callback_data="ARCHIVE_ALL_FILES")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="ARCHIVE_BACK_MENU")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_file_archive_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی آرشیو فایل‌ها"""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested file archive menu")

    with database.connection.SessionLocal() as db:
        # محاسبه تاریخ‌ها
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # شمارش فایل‌ها در بازه‌های مختلف
        weekly_files = db.query(FileOrder).filter(
            and_(
                FileOrder.user_id == user_id,
                FileOrder.created_at >= week_ago
            )
        ).count()

        monthly_files = db.query(FileOrder).filter(
            and_(
                FileOrder.user_id == user_id,
                FileOrder.created_at >= month_ago
            )
        ).count()

        total_files = db.query(FileOrder).filter(
            FileOrder.user_id == user_id
        ).count()

        logger.info(f"User {user_id} file counts: weekly={weekly_files}, monthly={monthly_files}, total={total_files}")

        if total_files == 0:
            await update.message.reply_text(
                "📂 آرشیو فایل‌ها خالی است\n\n"
                "📝 شما هنوز هیچ فایلی ارسال نکرده‌اید.",
                reply_markup=get_customer_kb(user_id)
            )
            return

        # ایجاد کیبورد آرشیو
        archive_keyboard = get_file_archive_keyboard(weekly_files, monthly_files, total_files)

        message = (
            "📂 **آرشیو فایل‌های شما**\n\n"
            "🎯 لطفاً بازه زمانی مورد نظر خود را انتخاب کنید:\n\n"
            "📅 **هفته اخیر:** فایل‌های ارسالی در ۷ روز گذشته\n"
            "📆 **ماه اخیر:** فایل‌های ارسالی در ۳۰ روز گذشته\n"
            "📋 **کل:** تمام فایل‌های ارسالی شما\n\n"
            "✨ پس از انتخاب، فایل‌ها به تفکیک روز برای شما ارسال خواهند شد."
        )

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=archive_keyboard
        )


async def send_file_archive_version(context: ContextTypes.DEFAULT_TYPE, user_id: int, file_order: FileOrder,
                                    file_number: int):
    """ارسال فایل با کپشن اصلاح شده برای آرشیو - بدون عکس رندر"""
    # تعیین ایموجی وضعیت
    status_emojis = {
        "pending": "⏳",
        "confirmed": "✅",
        "cancelled": "❌",
        "invoiced": "🧾"
    }
    status_emoji = status_emojis.get(file_order.status, "❓")

    # تبدیل تاریخ ارسال به شمسی
    created_at_jalali = gregorian_to_jalali_with_time(file_order.created_at)

    # تبدیل تاریخ تحویل به شمسی (اگر موجود باشد)
    delivery_time_jalali = "نامشخص"
    if file_order.delivery_datetime:
        delivery_time_jalali = gregorian_to_jalali_with_time(file_order.delivery_datetime)

    # کپشن جدید با اطلاعات کامل
    file_caption = (
        f"📄 **فایل #{file_number}** از این روز\n\n"
        f"📋 **نام فایل:** {file_order.file_name}\n"
        f"🔢 **تعداد پرینت:** {file_order.print_count}\n"
        f"📅 **تاریخ ارسال:** {created_at_jalali}\n"
        f"🚚 **زمان تحویل:** {delivery_time_jalali}\n"
        f"{status_emoji} **وضعیت:** {file_order.status}"
    )

    # اضافه کردن توضیحات اگر موجود باشد
    if file_order.description:
        file_caption += f"\n💭 **توضیحات:** {file_order.description}"

    try:
        # ارسال فقط فایل اصلی (بدون عکس رندر)
        await context.bot.send_document(
            chat_id=user_id,
            document=file_order.file_id,
            caption=file_caption,
            parse_mode="Markdown"
        )
        logger.info(f"Archive file {file_order.file_name} sent to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending archive file {file_order.file_name}: {e}")
        # در صورت خطا، ارسال پیام جایگزین
        error_message = (
            f"⚠️ **خطا در ارسال فایل #{file_number}**\n\n"
            f"{file_caption}\n\n"
            f"❌ **خطا:** فایل قابل بازیابی نیست\n"
            f"💡 **راهکار:** با پشتیبانی تماس بگیرید"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=error_message,
            parse_mode="Markdown"
        )


async def handle_archive_callback_unique(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر منحصر به فرد callback های آرشیو"""
    query = update.callback_query

    # بررسی اینکه callback مربوط به آرشیو است یا نه
    if not query.data.startswith("ARCHIVE_"):
        return  # این callback مربوط به ما نیست

    await query.answer()
    logger.info(f"Archive callback received: {query.data}")

    user_id = query.from_user.id

    if query.data == "ARCHIVE_BACK_MENU":
        await query.delete_message()
        await context.bot.send_message(
            chat_id=user_id,
            text="🔙 بازگشت به منوی اصلی",
            reply_markup=get_customer_kb(user_id)
        )
        return

    # تعیین بازه زمانی
    if query.data == "ARCHIVE_WEEK_7":
        days_back = 7
        period_name = "هفته اخیر"
        period_emoji = "📅"
    elif query.data == "ARCHIVE_MONTH_30":
        days_back = 30
        period_name = "ماه اخیر"
        period_emoji = "📆"
    elif query.data == "ARCHIVE_ALL_FILES":
        days_back = None
        period_name = "کل دوره"
        period_emoji = "📋"
    else:
        logger.warning(f"Unknown archive callback: {query.data}")
        return

    await query.delete_message()

    # نمایش پیام "در حال بارگذاری"
    loading_message = await context.bot.send_message(
        chat_id=user_id,
        text="⏳ در حال بارگذاری فایل‌ها...\nلطفاً صبر کنید."
    )

    with database.connection.SessionLocal() as db:
        # دریافت فایل‌ها بر اساس بازه زمانی
        query_filter = FileOrder.user_id == user_id

        if days_back:
            date_limit = datetime.now() - timedelta(days=days_back)
            query_filter = and_(query_filter, FileOrder.created_at >= date_limit)

        files = db.query(FileOrder).filter(query_filter).order_by(
            FileOrder.created_at.asc()
        ).all()

        logger.info(f"Found {len(files)} files for user {user_id} in period {period_name}")

        if not files:
            await loading_message.edit_text(
                f"{period_emoji} **{period_name}**\n\n"
                "🔭 هیچ فایلی در این بازه زمانی یافت نشد.",
                parse_mode="Markdown"
            )
            return

        # حذف پیام بارگذاری
        await loading_message.delete()

        # گروه‌بندی فایل‌ها بر اساس تاریخ
        files_by_date = {}
        for file in files:
            file_date = file.created_at.date()
            if file_date not in files_by_date:
                files_by_date[file_date] = []
            files_by_date[file_date].append(file)

        # ارسال پیام آغاز آرشیو
        start_message = (
            f"🎯 **شروع نمایش آرشیو {period_name}**\n\n"
            f"📊 **آمار کلی:**\n"
            f"📝 تعداد فایل‌ها: {len(files)}\n"
            f"📅 تعداد روزها: {len(files_by_date)}\n\n"
            "📄 فایل‌ها به ترتیب زمانی ارسال می‌شوند..."
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=start_message,
            parse_mode="Markdown"
        )

        # ارسال فایل‌ها به تفکیک روز
        for i, (date, day_files) in enumerate(files_by_date.items()):
            # تبدیل تاریخ میلادی به شمسی
            jalali_date = gregorian_to_jalali(datetime.combine(date, datetime.min.time()))
            gregorian_date = date.strftime('%Y/%m/%d')

            # پیام تاریخ با استیکر و فاصله‌گذاری زیبا
            date_message = (
                f"{'─' * 40}\n"
                f"📅 **فایل‌های ارسالی در تاریخ:**\n"
                f"🌙 **{jalali_date} شمسی**\n"
                f"🌍 **{gregorian_date} میلادی**\n"
                f"📝 **تعداد فایل‌ها:** {len(day_files)}\n"
                f"{'─' * 40}"
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=date_message,
                parse_mode="Markdown"
            )

            # ارسال فایل‌های آن روز (بدون عکس رندر)
            for j, file_order in enumerate(day_files, 1):
                await send_file_archive_version(context, user_id, file_order, j)

            # فاصله بین روزها (فقط اگر روز آخر نباشد)
            if i < len(files_by_date) - 1:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🔻🔻🔻🔻🔻"
                )

        # پیام پایان آرشیو
        end_message = (
            f"🎉 **پایان نمایش آرشیو {period_name}**\n\n"
            f"📊 **خلاصه:**\n"
            f"✅ {len(files)} فایل با موفقیت نمایش داده شد\n"
            f"📅 در {len(files_by_date)} روز مختلف\n\n"
            f"💡 **نکته:** برای مشاهده آرشیو دوره‌های دیگر، از منوی اصلی استفاده کنید.\n\n"
            f"{'🌟' * 10}"
        )

        await context.bot.send_message(
            chat_id=user_id,
            text=end_message,
            parse_mode="Markdown",
            reply_markup=get_customer_kb(user_id)
        )