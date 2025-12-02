# handlers/broadcast_handler.py
from telegram import Update, Message
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode
import database.connection
import database.crud
import database.broadcast_crud as broadcast_crud
from keyboards.broadcast_keyboards import (
    get_broadcast_main_keyboard,
    get_broadcast_preview_keyboard,
    get_broadcast_cancel_keyboard,
    get_broadcast_history_keyboard,
    get_broadcast_detail_keyboard
)
from utils.broadcast_utils import (
    parse_shamsi_datetime,
    format_shamsi_datetime,
    validate_datetime_range,
    is_discount_active,
    get_current_iran_time
)
from config import ADMIN_ID
import logging
import asyncio

logger = logging.getLogger(__name__)

# States
(
    BROADCAST_SELECT_TYPE,
    BROADCAST_GET_CONTENT,
    BROADCAST_GET_START_DATE,
    BROADCAST_GET_START_TIME,
    BROADCAST_GET_END_DATE,
    BROADCAST_GET_END_TIME,
    BROADCAST_CONFIRM,
) = range(7)


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ارسال پیام همگانی"""
    query = update.callback_query
    await query.answer()

    message_text = (
        "📣 **سیستم ارسال پیام همگانی**\n\n"
        "لطفاً نوع پیام را انتخاب کنید:\n\n"
        "📢 **پیام تبلیغاتی**: برای مشتریانی که پیام‌های تبلیغاتی را فعال کرده‌اند\n"
        "🎉 **تخفیف مناسبتی**: فقط برای مشتریانی که تمام پیام‌ها را فعال کرده‌اند\n\n"
        "⚠️ توجه: پیام به تمام مشتریان واجد شرایط ارسال خواهد شد."
    )

    keyboard = get_broadcast_main_keyboard()

    await query.edit_message_text(
        text=message_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END


async def select_broadcast_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """انتخاب نوع پیام (تبلیغاتی یا مناسبتی)"""
    query = update.callback_query
    await query.answer()

    # تشخیص نوع پیام
    if "promotional" in query.data:
        message_type = "promotional"
        type_name = "📢 تبلیغاتی"
        description = "این پیام برای مشتریانی ارسال می‌شود که:\n✅ همه پیام‌ها را فعال کرده‌اند\n✅ یا فقط پیام‌های تبلیغاتی را فعال کرده‌اند"
    else:
        message_type = "occasional"
        type_name = "🎉 تخفیف مناسبتی"
        description = "این پیام فقط برای مشتریانی ارسال می‌شود که:\n✅ همه پیام‌ها را فعال کرده‌اند"

    context.user_data['broadcast_type'] = message_type
    context.user_data['broadcast_type_name'] = type_name

    # محاسبه تعداد گیرندگان
    with database.connection.SessionLocal() as db:
        eligible_customers = database.crud.get_customers_for_notification(db, message_type)
        context.user_data['eligible_count'] = len(eligible_customers)

    message_text = (
        f"📝 **ساخت پیام {type_name}**\n\n"
        f"{description}\n\n"
        f"👥 تعداد مشتریان واجد شرایط: **{len(eligible_customers)} نفر**\n\n"
        "لطفاً پیام خود را ارسال کنید:\n\n"
        "✅ می‌توانید متن بفرستید\n"
        "✅ می‌توانید عکس + کپشن بفرستید\n"
        "✅ می‌توانید ویدیو + کپشن بفرستید\n"
        "✅ می‌توانید ویس/صوت بفرستید\n"
        "✅ می‌توانید فایل/سند بفرستید\n\n"
        "⚠️ فقط **یک** پیام ارسال کنید."
    )

    await query.edit_message_text(
        text=message_text,
        reply_markup=get_broadcast_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    return BROADCAST_GET_CONTENT


async def receive_broadcast_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت محتوای پیام از ادمین"""
    message = update.message

    # ذخیره اطلاعات پیام
    content_data = {
        'text': None,
        'media_file_id': None,
        'media_type': None
    }

    if message.text:
        content_data['text'] = message.text

    elif message.photo:
        # بزرگترین سایز عکس
        content_data['media_file_id'] = message.photo[-1].file_id
        content_data['media_type'] = 'photo'
        content_data['text'] = message.caption

    elif message.video:
        content_data['media_file_id'] = message.video.file_id
        content_data['media_type'] = 'video'
        content_data['text'] = message.caption

    elif message.audio:
        content_data['media_file_id'] = message.audio.file_id
        content_data['media_type'] = 'audio'
        content_data['text'] = message.caption

    elif message.voice:
        content_data['media_file_id'] = message.voice.file_id
        content_data['media_type'] = 'voice'
        content_data['text'] = message.caption

    elif message.document:
        content_data['media_file_id'] = message.document.file_id
        content_data['media_type'] = 'document'
        content_data['text'] = message.caption

    else:
        await message.reply_text(
            "❌ نوع پیام پشتیبانی نمی‌شود.\n"
            "لطفاً متن، عکس، ویدیو، صوت یا فایل ارسال کنید."
        )
        return BROADCAST_GET_CONTENT

    context.user_data['broadcast_content'] = content_data

    # اگر پیام تخفیف مناسبتی است، تاریخ شروع بگیر
    message_type = context.user_data.get('broadcast_type')
    if message_type == 'occasional':
        await message.reply_text(
            "📅 **تاریخ شروع تخفیف**\n\n"
            "لطفاً تاریخ شروع تخفیف را به فرمت شمسی وارد کنید:\n\n"
            "📝 فرمت: `1404/07/20` یا `1404-07-20`\n"
            "💡 مثال: 1404/07/25\n\n"
            "⚠️ توجه: تاریخ باید از امروز به بعد باشد.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_START_DATE

    # اگر پیام تبلیغاتی است، مستقیم به پیش‌نمایش برو
    await show_broadcast_preview(update, context)
    return BROADCAST_CONFIRM

async def get_discount_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تاریخ شروع تخفیف"""
    message = update.message
    date_str = message.text.strip()

    # اعتبارسنجی ساده فرمت
    if not (date_str.count('/') == 2 or date_str.count('-') == 2):
        await message.reply_text(
            "❌ فرمت تاریخ اشتباه است!\n\n"
            "لطفاً به فرمت زیر وارد کنید:\n"
            "📝 1404/07/25 یا 1404-07-25",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_START_DATE

    context.user_data['start_date'] = date_str

    await message.reply_text(
        "🕐 **ساعت شروع تخفیف**\n\n"
        "لطفاً ساعت شروع تخفیف را وارد کنید:\n\n"
        "📝 فرمت: `HH:MM` (24 ساعته)\n"
        "💡 مثال: 14:30 یا 08:00\n\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_broadcast_cancel_keyboard()
    )

    return BROADCAST_GET_START_TIME


async def get_discount_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ساعت شروع تخفیف"""
    message = update.message
    time_str = message.text.strip()

    # اعتبارسنجی ساده فرمت
    if time_str.count(':') != 1:
        await message.reply_text(
            "❌ فرمت ساعت اشتباه است!\n\n"
            "لطفاً به فرمت زیر وارد کنید:\n"
            "📝 14:30 یا 08:00",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_START_TIME

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.reply_text(
            "❌ ساعت یا دقیقه نامعتبر است!\n\n"
            "ساعت: 0 تا 23\n"
            "دقیقه: 0 تا 59",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_START_TIME

    context.user_data['start_time'] = time_str

    # تبدیل به datetime برای اعتبارسنجی
    start_date = context.user_data.get('start_date')
    start_dt = parse_shamsi_datetime(start_date, time_str)

    if not start_dt:
        await message.reply_text(
            "❌ خطا در تبدیل تاریخ!\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        context.user_data.pop('start_date', None)
        context.user_data.pop('start_time', None)
        return BROADCAST_GET_START_DATE

    # چک کردن که تاریخ شروع در گذشته نباشد
    current_time = get_current_iran_time()
    if start_dt < current_time:
        await message.reply_text(
            "❌ زمان شروع نمی‌تواند در گذشته باشد!\n\n"
            f"زمان فعلی: {format_shamsi_datetime(current_time)}\n"
            f"زمان شروع شما: {format_shamsi_datetime(start_dt)}\n\n"
            "لطفاً تاریخ و ساعت را مجدداً وارد کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_broadcast_cancel_keyboard()
        )
        context.user_data.pop('start_date', None)
        context.user_data.pop('start_time', None)
        return BROADCAST_GET_START_DATE

    context.user_data['start_datetime'] = start_dt

    await message.reply_text(
        f"✅ زمان شروع: {format_shamsi_datetime(start_dt)}\n\n"
        "📅 **تاریخ پایان تخفیف**\n\n"
        "لطفاً تاریخ پایان تخفیف را وارد کنید:\n\n"
        "📝 فرمت: `1404/07/20` یا `1404-07-20`\n"
        "💡 مثال: 1404/07/26\n\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_broadcast_cancel_keyboard()
    )

    return BROADCAST_GET_END_DATE


async def get_discount_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تاریخ پایان تخفیف"""
    message = update.message
    date_str = message.text.strip()

    # اعتبارسنجی ساده فرمت
    if not (date_str.count('/') == 2 or date_str.count('-') == 2):
        await message.reply_text(
            "❌ فرمت تاریخ اشتباه است!\n\n"
            "لطفاً به فرمت زیر وارد کنید:\n"
            "📝 1404/07/25 یا 1404-07-25",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_END_DATE

    context.user_data['end_date'] = date_str

    await message.reply_text(
        "🕐 **ساعت پایان تخفیف**\n\n"
        "لطفاً ساعت پایان تخفیف را وارد کنید:\n\n"
        "📝 فرمت: `HH:MM` (24 ساعته)\n"
        "💡 مثال: 23:59 یا 18:30\n\n",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_broadcast_cancel_keyboard()
    )

    return BROADCAST_GET_END_TIME


async def get_discount_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت ساعت پایان تخفیف"""
    message = update.message
    time_str = message.text.strip()

    # اعتبارسنجی ساده فرمت
    if time_str.count(':') != 1:
        await message.reply_text(
            "❌ فرمت ساعت اشتباه است!\n\n"
            "لطفاً به فرمت زیر وارد کنید:\n"
            "📝 23:59 یا 18:30",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_END_TIME

    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except:
        await message.reply_text(
            "❌ ساعت یا دقیقه نامعتبر است!\n\n"
            "ساعت: 0 تا 23\n"
            "دقیقه: 0 تا 59",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        return BROADCAST_GET_END_TIME

    context.user_data['end_time'] = time_str

    # تبدیل به datetime
    end_date = context.user_data.get('end_date')
    end_dt = parse_shamsi_datetime(end_date, time_str)

    if not end_dt:
        await message.reply_text(
            "❌ خطا در تبدیل تاریخ!\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_broadcast_cancel_keyboard()
        )
        context.user_data.pop('end_date', None)
        context.user_data.pop('end_time', None)
        return BROADCAST_GET_END_DATE

    context.user_data['end_datetime'] = end_dt

    # اعتبارسنجی بازه زمانی
    start_dt = context.user_data.get('start_datetime')
    is_valid, error_msg = validate_datetime_range(start_dt, end_dt)

    if not is_valid:
        await message.reply_text(
            f"❌ {error_msg}\n\n"
            f"زمان شروع: {format_shamsi_datetime(start_dt)}\n"
            f"زمان پایان: {format_shamsi_datetime(end_dt)}\n\n"
            "لطفاً تاریخ و ساعت پایان را مجدداً وارد کنید.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_broadcast_cancel_keyboard()
        )
        context.user_data.pop('end_date', None)
        context.user_data.pop('end_time', None)
        context.user_data.pop('end_datetime', None)
        return BROADCAST_GET_END_DATE

    # نمایش پیش‌نمایش
    await message.reply_text(
        f"✅ **بازه زمانی تخفیف تنظیم شد:**\n\n"
        f"🟢 شروع: {format_shamsi_datetime(start_dt)}\n"
        f"🔴 پایان: {format_shamsi_datetime(end_dt)}\n\n"
        "در حال آماده‌سازی پیش‌نمایش...",
        parse_mode=ParseMode.MARKDOWN
    )

    await show_broadcast_preview(update, context)

    return BROADCAST_CONFIRM

async def show_broadcast_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پیش‌نمایش پیام قبل از ارسال"""
    content_data = context.user_data.get('broadcast_content')
    message_type = context.user_data.get('broadcast_type')
    type_name = context.user_data.get('broadcast_type_name')
    eligible_count = context.user_data.get('eligible_count', 0)

    preview_text = (
        f"👁 **پیش‌نمایش پیام {type_name}**\n\n"
        f"👥 تعداد گیرندگان: **{eligible_count} نفر**\n"
    )

    # اگر تخفیف مناسبتی است، بازه زمانی را نمایش بده
    if message_type == 'occasional':
        start_dt = context.user_data.get('start_datetime')
        end_dt = context.user_data.get('end_datetime')

        if start_dt and end_dt:
            preview_text += (
                f"\n⏰ **بازه زمانی تخفیف:**\n"
                f"🟢 شروع: {format_shamsi_datetime(start_dt)}\n"
                f"🔴 پایان: {format_shamsi_datetime(end_dt)}\n"
            )

    preview_text += "\n━━━━━━━━━━━━━━━━━━━━\n**پیام شما:**\n"

    keyboard = get_broadcast_preview_keyboard(message_type)

    # ارسال پیش‌نمایش بسته به نوع
    if content_data['media_type'] == 'photo':
        caption = preview_text + (content_data['text'] or "")
        await update.message.reply_photo(
            photo=content_data['media_file_id'],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    elif content_data['media_type'] == 'video':
        caption = preview_text + (content_data['text'] or "")
        await update.message.reply_video(
            video=content_data['media_file_id'],
            caption=caption,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    elif content_data['media_type'] == 'audio':
        await update.message.reply_audio(
            audio=content_data['media_file_id'],
            caption=content_data['text'],
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(
            text=preview_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    elif content_data['media_type'] == 'voice':
        await update.message.reply_voice(
            voice=content_data['media_file_id']
        )
        await update.message.reply_text(
            text=preview_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    elif content_data['media_type'] == 'document':
        caption = content_data['text'] or ""
        await update.message.reply_document(
            document=content_data['media_file_id'],
            caption=caption,
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(
            text=preview_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )

    else:  # text only
        full_text = preview_text + "\n" + (content_data['text'] or "")
        await update.message.reply_text(
            text=full_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN
        )



async def confirm_and_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید و ارسال پیام به تمام مشتریان واجد شرایط"""
    query = update.callback_query
    await query.answer()

    content_data = context.user_data.get('broadcast_content')
    message_type = context.user_data.get('broadcast_type')
    admin_id = update.effective_user.id

    # دریافت تاریخ‌ها (فقط برای occasional)
    start_dt = context.user_data.get('start_datetime') if message_type == 'occasional' else None
    end_dt = context.user_data.get('end_datetime') if message_type == 'occasional' else None

    # ایجاد رکورد broadcast در دیتابیس
    with database.connection.SessionLocal() as db:
        broadcast = broadcast_crud.create_broadcast_message(
            db=db,
            message_type=message_type,
            content=content_data['text'],
            media_file_id=content_data['media_file_id'],
            media_type=content_data['media_type'],
            created_by=admin_id,
            start_datetime=start_dt,
            end_datetime=end_dt
        )
        broadcast_id = broadcast.id

        # دریافت لیست مشتریان واجد شرایط
        eligible_customers = database.crud.get_customers_for_notification(db, message_type)

    await query.edit_message_text(
        f"⏳ در حال ارسال پیام به {len(eligible_customers)} مشتری...\n"
        "لطفاً صبر کنید..."
    )

    # ارسال پیام‌ها
    successful = 0
    failed = 0

    for customer in eligible_customers:
        try:
            # ارسال بر اساس نوع محتوا
            sent_message = None

            if content_data['media_type'] == 'photo':
                sent_message = await context.bot.send_photo(
                    chat_id=customer.id,
                    photo=content_data['media_file_id'],
                    caption=content_data['text'],
                    parse_mode=ParseMode.MARKDOWN
                )

            elif content_data['media_type'] == 'video':
                sent_message = await context.bot.send_video(
                    chat_id=customer.id,
                    video=content_data['media_file_id'],
                    caption=content_data['text'],
                    parse_mode=ParseMode.MARKDOWN
                )

            elif content_data['media_type'] == 'audio':
                sent_message = await context.bot.send_audio(
                    chat_id=customer.id,
                    audio=content_data['media_file_id'],
                    caption=content_data['text'],
                    parse_mode=ParseMode.MARKDOWN
                )

            elif content_data['media_type'] == 'voice':
                sent_message = await context.bot.send_voice(
                    chat_id=customer.id,
                    voice=content_data['media_file_id']
                )

            elif content_data['media_type'] == 'document':
                sent_message = await context.bot.send_document(
                    chat_id=customer.id,
                    document=content_data['media_file_id'],
                    caption=content_data['text'],
                    parse_mode=ParseMode.MARKDOWN
                )

            else:  # text only
                sent_message = await context.bot.send_message(
                    chat_id=customer.id,
                    text=content_data['text'],
                    parse_mode=ParseMode.MARKDOWN
                )

            # ثبت موفقیت
            with database.connection.SessionLocal() as db:
                broadcast_crud.create_broadcast_log(
                    db=db,
                    broadcast_message_id=broadcast_id,
                    customer_id=customer.id,
                    status="sent",
                    telegram_message_id=sent_message.message_id if sent_message else None
                )
            successful += 1

            # تاخیر کوتاه برای جلوگیری از محدودیت تلگرام
            await asyncio.sleep(0.05)

        except Exception as e:
            logger.error(f"خطا در ارسال پیام به {customer.id}: {e}")

            # ثبت خطا
            with database.connection.SessionLocal() as db:
                status = "blocked" if "Forbidden" in str(e) else "failed"
                broadcast_crud.create_broadcast_log(
                    db=db,
                    broadcast_message_id=broadcast_id,
                    customer_id=customer.id,
                    status=status,
                    error_message=str(e)
                )
            failed += 1

            await asyncio.sleep(0.05)

    # بروزرسانی آمار
    with database.connection.SessionLocal() as db:
        broadcast_crud.update_broadcast_stats(
            db=db,
            broadcast_id=broadcast_id,
            total_recipients=len(eligible_customers),
            successful_sends=successful,
            failed_sends=failed
        )

    # نمایش نتیجه
    result_text = (
        "✅ **ارسال پیام تکمیل شد!**\n\n"
        f"📊 **آمار ارسال:**\n"
        f"👥 کل مشتریان: {len(eligible_customers)}\n"
        f"✅ ارسال موفق: {successful}\n"
        f"❌ ارسال ناموفق: {failed}\n"
        f"📈 نرخ موفقیت: {(successful / len(eligible_customers) * 100):.1f}%\n\n"
        f"🆔 شناسه ارسال: #{broadcast_id}"
    )

    # اضافه کردن بازه زمانی برای occasional
    if message_type == 'occasional' and start_dt and end_dt:
        result_text += (
            f"\n\n⏰ **بازه زمانی تخفیف:**\n"
            f"🟢 شروع: {format_shamsi_datetime(start_dt)}\n"
            f"🔴 پایان: {format_shamsi_datetime(end_dt)}"
        )

    await query.message.reply_text(
        text=result_text,
        reply_markup=get_broadcast_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

    # پاک کردن داده‌های موقت
    context.user_data.clear()

    return ConversationHandler.END

async def edit_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ویرایش پیام (شروع دوباره)"""
    query = update.callback_query
    await query.answer("🔄 لطفاً پیام جدید را ارسال کنید")

    message_type = context.user_data.get('broadcast_type')
    type_name = context.user_data.get('broadcast_type_name')

    await query.edit_message_text(
        f"📝 **ویرایش پیام {type_name}**\n\n"
        "لطفاً پیام جدید خود را ارسال کنید.",
        reply_markup=get_broadcast_cancel_keyboard()
    )

    return BROADCAST_GET_CONTENT


async def show_broadcast_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی ارسال پیام‌ها"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        stats = broadcast_crud.get_broadcast_statistics()

        # آمار مشتریان
        all_customers = database.crud.get_customers(db)
        customers_all = sum(1 for c in all_customers if c.notification_status == "all")
        customers_promo = sum(1 for c in all_customers if c.notification_status == "promotional_only")
        customers_none = sum(1 for c in all_customers if c.notification_status == "none")

    stats_text = (
        "📊 **آمار سیستم ارسال پیام**\n\n"
        "**📨 پیام‌های ارسالی:**\n"
        f"• کل پیام‌ها: {stats['total_broadcasts']}\n"
        f"• پیام‌های تبلیغاتی: {stats['promotional_count']}\n"
        f"• تخفیف‌های مناسبتی: {stats['occasional_count']}\n\n"
        "**📬 وضعیت ارسال:**\n"
        f"• موفق: {stats['total_sent']}\n"
        f"• ناموفق: {stats['total_failed']}\n\n"
        "**👥 وضعیت مشتریان:**\n"
        f"🟢 همه پیام‌ها: {customers_all} نفر\n"
        f"🟡 فقط تبلیغات: {customers_promo} نفر\n"
        f"🔴 هیچ پیامی: {customers_none} نفر\n\n"
        f"📊 کل مشتریان: {len(all_customers)} نفر"
    )

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="broadcast_main")]]

    await query.edit_message_text(
        text=stats_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def show_broadcast_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه پیام‌های ارسالی"""
    query = update.callback_query
    await query.answer()

    page = 0
    if "page" in query.data:
        page = int(query.data.split("_")[-1])

    with database.connection.SessionLocal() as db:
        broadcasts = broadcast_crud.get_all_broadcasts(db, limit=10)

    if not broadcasts:
        await query.edit_message_text(
            "📭 هیچ پیامی ارسال نشده است.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="broadcast_main")
            ]])
        )
        return

    keyboard = get_broadcast_history_keyboard(broadcasts, page)

    await query.edit_message_text(
        "📜 **تاریخچه پیام‌های ارسالی**\n\n"
        "برای مشاهده جزئیات هر پیام، روی آن کلیک کنید:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


async def show_broadcast_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک پیام ارسالی"""
    query = update.callback_query
    await query.answer()

    broadcast_id = int(query.data.split("_")[-1])

    with database.connection.SessionLocal() as db:
        broadcast = broadcast_crud.get_broadcast_by_id(db, broadcast_id)

        if not broadcast:
            await query.answer("❌ پیام یافت نشد", show_alert=True)
            return

        creator = database.crud.get_user(db, broadcast.created_by)

    type_emoji = "📢" if broadcast.message_type == "promotional" else "🎉"
    type_name = "تبلیغاتی" if broadcast.message_type == "promotional" else "تخفیف مناسبتی"

    detail_text = (
        f"{type_emoji} **جزئیات پیام {type_name}**\n\n"
        f"🆔 شناسه: #{broadcast.id}\n"
        f"👤 ارسال‌کننده: {creator.full_name if creator else 'نامشخص'}\n"
        f"📅 تاریخ: {broadcast.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**📊 آمار ارسال:**\n"
        f"👥 کل گیرندگان: {broadcast.total_recipients}\n"
        f"✅ موفق: {broadcast.successful_sends}\n"
        f"❌ ناموفق: {broadcast.failed_sends}\n"
        f"📈 نرخ موفقیت: {(broadcast.successful_sends / broadcast.total_recipients * 100):.1f}%\n\n"
    )

    if broadcast.content:
        detail_text += f"**💬 متن پیام:**\n{broadcast.content[:200]}"
        if len(broadcast.content) > 200:
            detail_text += "..."

    keyboard = get_broadcast_detail_keyboard(broadcast_id)

    await query.edit_message_text(
        text=detail_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )


async def show_broadcast_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لاگ‌های ارسال یک پیام"""
    query = update.callback_query
    await query.answer()

    broadcast_id = int(query.data.split("_")[-1])

    with database.connection.SessionLocal() as db:
        logs = broadcast_crud.get_broadcast_logs(db, broadcast_id, limit=50)
        broadcast = broadcast_crud.get_broadcast_by_id(db, broadcast_id)

    if not logs:
        await query.answer("❌ لاگی یافت نشد", show_alert=True)
        return

    log_text = f"📋 **لاگ‌های ارسال پیام #{broadcast_id}**\n\n"

    # گروه‌بندی بر اساس وضعیت
    sent_logs = [l for l in logs if l.status == "sent"]
    failed_logs = [l for l in logs if l.status == "failed"]
    blocked_logs = [l for l in logs if l.status == "blocked"]

    log_text += f"✅ **ارسال موفق:** {len(sent_logs)} نفر\n"
    if len(sent_logs) > 0 and len(sent_logs) <= 10:
        for log in sent_logs[:10]:
            with database.connection.SessionLocal() as db:
                customer = database.crud.get_user(db, log.customer_id)
            log_text += f"  • {customer.full_name if customer else 'نامشخص'}\n"

    log_text += f"\n❌ **ارسال ناموفق:** {len(failed_logs)} نفر\n"
    if len(failed_logs) > 0 and len(failed_logs) <= 5:
        for log in failed_logs[:5]:
            with database.connection.SessionLocal() as db:
                customer = database.crud.get_user(db, log.customer_id)
            log_text += f"  • {customer.full_name if customer else 'نامشخص'}\n"

    log_text += f"\n🚫 **بلاک شده:** {len(blocked_logs)} نفر\n"

    keyboard = [[
        InlineKeyboardButton("🔙 بازگشت", callback_data=f"broadcast_view_{broadcast_id}")
    ]]

    await query.edit_message_text(
        text=log_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند ارسال پیام"""
    query = update.callback_query
    await query.answer("❌ لغو شد")

    context.user_data.clear()

    await query.edit_message_text(
        "❌ **فرآیند ارسال پیام لغو شد.**",
        reply_markup=get_broadcast_main_keyboard()
    )

    return ConversationHandler.END


# ConversationHandler برای ارسال پیام تبلیغاتی
# این تابع را در انتهای فایل handlers/broadcast_handler.py جایگزین کنید:

def get_broadcast_conversation_handler():
    """دریافت ConversationHandler برای سیستم ارسال پیام"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                select_broadcast_type,
                pattern=r'^broadcast_(promotional|occasional)$'
            )
        ],
        states={
            BROADCAST_GET_CONTENT: [
                MessageHandler(
                    filters.TEXT | filters.PHOTO | filters.VIDEO |
                    filters.AUDIO | filters.VOICE | filters.Document.ALL,
                    receive_broadcast_content
                )
            ],
            BROADCAST_GET_START_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount_start_date)
            ],
            BROADCAST_GET_START_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount_start_time)
            ],
            BROADCAST_GET_END_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount_end_date)
            ],
            BROADCAST_GET_END_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_discount_end_time)
            ],
            BROADCAST_CONFIRM: [
                CallbackQueryHandler(
                    confirm_and_send_broadcast,
                    pattern=r'^broadcast_confirm_'
                ),
                CallbackQueryHandler(
                    edit_broadcast_message,
                    pattern=r'^broadcast_edit_'
                )
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cancel_broadcast, pattern=r'^broadcast_cancel$'),
            CommandHandler('cancel', cancel_broadcast)
        ]
    )