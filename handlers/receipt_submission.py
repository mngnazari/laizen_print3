# handlers/receipt_submission.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from utils.referral import get_persian_datetime

# وضعیت‌های conversation
RECEIPT_UPLOAD, RECEIPT_DESCRIPTION = range(200, 202)


async def start_receipt_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ارسال رسید کارت به کارت"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # بررسی اینکه کاربر مشتری باشد
    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)
        if not user or user.role != "customer":
            await query.edit_message_text("شما مجاز به استفاده از این قسمت نیستید.")
            return ConversationHandler.END

    # راهنمای ارسال رسید
    instruction_text = (
        "💳 **ارسال رسید کارت به کارت**\n\n"
        "لطفاً عکس یا عکس‌های رسید واریز کارت به کارت خود را ارسال کنید.\n\n"
        "📌 **راهنما:**\n"
        "• می‌توانید چندین عکس ارسال کنید\n"
        "• برای پایان ارسال، دستور `/end` را تایپ کنید\n"
        "• یا از دکمه \"پایان ارسال\" استفاده کنید\n\n"
        "⏳ **منتظر اولین رسید شما هستیم...**"
    )

    # کیبورد لغو
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_receipt_submission")]
    ])

    await query.edit_message_text(
        instruction_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

    # شروع conversation و ایجاد لیست برای ذخیره رسیدها
    context.user_data['receipts'] = []
    return RECEIPT_UPLOAD


async def handle_receipt_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دریافت عکس‌های رسید"""
    user_id = update.effective_user.id

    # بررسی اینکه پیام عکس باشد
    if not update.message.photo:
        await update.message.reply_text(
            "❌ لطفاً فقط عکس ارسال کنید.\n"
            "برای پایان ارسال دستور `/end` را تایپ کنید یا دکمه پایان را بزنید."
        )
        return RECEIPT_UPLOAD

    # گرفتن بهترین کیفیت عکس
    photo = update.message.photo[-1]
    file_id = photo.file_id
    file_size = photo.file_size

    # ذخیره در لیست موقت
    receipt_info = {
        'file_id': file_id,
        'file_size': file_size,
        'message_id': update.message.message_id
    }

    if 'receipts' not in context.user_data:
        context.user_data['receipts'] = []

    context.user_data['receipts'].append(receipt_info)

    receipt_count = len(context.user_data['receipts'])

    # تأیید دریافت و راهنمای ادامه
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ پایان ارسال", callback_data="finish_receipt_upload"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel_receipt_submission")
        ]
    ])

    await update.message.reply_text(
        f"✅ رسید {receipt_count} دریافت شد!\n\n"
        f"📊 تعداد رسیدهای ارسالی: {receipt_count}\n\n"
        f"💡 برای ارسال رسید بیشتر، عکس بعدی را ارسال کنید\n"
        f"💡 برای پایان ارسال، دکمه \"پایان ارسال\" را بزنید یا `/end` تایپ کنید",
        reply_markup=keyboard
    )

    return RECEIPT_UPLOAD


async def handle_end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت دستور /end"""
    receipts = context.user_data.get('receipts', [])

    if not receipts:
        await update.message.reply_text(
            "❌ شما هنوز هیچ رسیدی ارسال نکرده‌اید!\n"
            "لطفاً ابتدا عکس رسید خود را ارسال کنید."
        )
        return RECEIPT_UPLOAD

    return await finish_receipt_submission(update, context)


async def finish_receipt_submission(update, context: ContextTypes.DEFAULT_TYPE):
    """پایان فرآیند و درخواست توضیحات"""
    receipts = context.user_data.get('receipts', [])

    if not receipts:
        message = "❌ شما هنوز هیچ رسیدی ارسال نکرده‌اید!"
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message)
        else:
            await update.message.reply_text(message)
        return ConversationHandler.END

    receipt_count = len(receipts)

    instruction_text = (
        f"📝 **مرحله نهایی**\n\n"
        f"✅ تعداد رسیدهای دریافت شده: {receipt_count}\n\n"
        f"لطفاً توضیح کوتاهی در مورد این رسیدها بنویسید:\n"
        f"• مبلغ کل واریزی\n"
        f"• تاریخ واریز\n"
        f"• هر توضیح اضافی\n\n"
        f"💡 این توضیحات به ادمین کمک می‌کند تا رسیدهای شما را سریع‌تر بررسی کند."
    )

    # کیبورد لغو
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ لغو", callback_data="cancel_receipt_submission")]
    ])

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            instruction_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            instruction_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    return RECEIPT_DESCRIPTION


async def handle_receipt_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات و ذخیره نهایی رسیدها"""
    user_id = update.effective_user.id
    description = update.message.text.strip()
    receipts = context.user_data.get('receipts', [])

    if not description:
        await update.message.reply_text(
            "❌ لطفاً توضیحات رسید را وارد کنید.\n"
            "این توضیحات برای ادمین مهم است."
        )
        return RECEIPT_DESCRIPTION

    if not receipts:
        await update.message.reply_text("❌ خطا در پردازش رسیدها. لطفاً دوباره تلاش کنید.")
        context.user_data.clear()
        return ConversationHandler.END

    # ذخیره رسیدها در دیتابیس
    try:
        with database.connection.SessionLocal() as db:
            saved_receipts = []
            for i, receipt_info in enumerate(receipts, 1):
                receipt = database.crud.create_receipt(
                    db=db,
                    user_id=user_id,
                    file_id=receipt_info['file_id'],
                    file_name=f"receipt_{i}.jpg",
                    file_size=receipt_info.get('file_size'),
                    description=description
                )
                saved_receipts.append(receipt)

        success_text = (
            f"✅ **رسیدهای شما با موفقیت ثبت شد!**\n\n"
            f"📊 تعداد رسیدها: {len(saved_receipts)}\n"
            f"📝 توضیحات: {description}\n"
            f"🕐 زمان ثبت: {get_persian_datetime()}\n\n"
            f"📋 **وضعیت:** در انتظار بررسی ادمین\n"
            f"📱 پس از بررسی، از نتیجه مطلع خواهید شد."
        )

        # کیبورد بازگشت به منوی کیف پول
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت به کیف پول", callback_data="wallet_menu")]
        ])

        await update.message.reply_text(
            success_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        # اطلاع‌رسانی به ادمین (اختیاری)
        try:
            admin_notification = (
                f"🔔 **رسید جدید دریافت شد**\n\n"
                f"👤 کاربر: {update.effective_user.full_name}\n"
                f"📊 تعداد رسیدها: {len(saved_receipts)}\n"
                f"📝 توضیحات: {description}\n"
                f"🕐 زمان: {get_persian_datetime()}"
            )

            # ارسال به ادمین (ADMIN_ID باید import شود)
            ADMIN_ID = 2138687434
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_notification,
                parse_mode="Markdown"
            )
        except:
            pass  # اگر ارسال به ادمین نشد، مهم نیست

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ذخیره رسیدها: {str(e)}\n"
            "لطفاً دوباره تلاش کنید."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def handle_finish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback پایان ارسال"""
    query = update.callback_query
    await query.answer()

    if query.data == "finish_receipt_upload":
        return await finish_receipt_submission(update, context)
    elif query.data == "cancel_receipt_submission":
        await query.edit_message_text("❌ ارسال رسید لغو شد.")
        context.user_data.clear()
        return ConversationHandler.END

    return RECEIPT_UPLOAD


async def cancel_receipt_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند ارسال رسید"""
    await update.message.reply_text("❌ ارسال رسید لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END