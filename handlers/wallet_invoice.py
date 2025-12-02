# handlers/wallet_invoice.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database.crud
import database.connection
from database.models import User, Invoice
from keyboards.customer import get_customer_kb
import jdatetime
import logging
from handlers.transaction_viewer import show_transactions_list
logger = logging.getLogger(__name__)


def create_wallet_menu_keyboard():
    """ایجاد کیبورد شیشه‌ای کیف پول"""
    keyboard = [
        [
            InlineKeyboardButton("🧾 فاکتورها", callback_data="wallet_invoices"),
            InlineKeyboardButton("💸 تراکنش‌ها", callback_data="wallet_transactions")
        ],
        [
            InlineKeyboardButton("💳 ارسال رسید کارت به کارت", callback_data="submit_receipt")
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_customer_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_invoice_navigation_keyboard(current_index: int, total_count: int):
    """ایجاد کیبورد ناوبری فاکتورها"""
    keyboard = []

    # ردیف اول: دکمه‌های ناوبری
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"invoice_nav_prev_{current_index}"))

    # نمایش شماره فاکتور (دکمه غیرقابل کلیک)
    nav_buttons.append(InlineKeyboardButton(f"📄 {current_index + 1}/{total_count}", callback_data="noop"))

    if current_index < total_count - 1:
        nav_buttons.append(InlineKeyboardButton("➡️ بعدی", callback_data=f"invoice_nav_next_{current_index}"))

    keyboard.append(nav_buttons)

    # ردیف دوم: دکمه بازگشت
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")])

    return InlineKeyboardMarkup(keyboard)


def gregorian_to_jalali_with_time(gregorian_datetime):
    """تبدیل تاریخ و ساعت میلادی به شمسی"""
    try:
        j_datetime = jdatetime.datetime.fromtimestamp(gregorian_datetime.timestamp())
        return j_datetime.strftime('%Y/%m/%d - %H:%M')
    except:
        return gregorian_datetime.strftime('%Y/%m/%d - %H:%M')


async def show_wallet_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی کیف پول و اعتبار"""
    user_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)

        if not user:
            await update.message.reply_text(
                "شما هنوز ثبت‌نام نکرده‌اید. لطفاً ثبت‌نام کنید.",
                reply_markup=get_customer_kb(user_id)
            )
            return

        # آمار فاکتورها
        invoices_count = len(database.crud.get_customer_invoices(db, user_id))

        # محاسبه مجموع مبالغ فاکتورها
        total_invoice_amount = sum([inv.total_amount for inv in database.crud.get_customer_invoices(db, user_id)])

        message = (
            f"💼 **کیف پول و اعتبار شما**\n\n"
            f"💰 **موجودی کیف پول:** {int(user.wallet_balance)} دلار\n"
            f"🎁 **اعتبار تخفیف:** {int(user.discount_credit)} دلار\n"
            f"📊 **مجموع اعتبار:** {int(user.wallet_balance + user.discount_credit)} دلار\n\n"
            f"🧾 **آمار فاکتورها:**\n"
            f"📋 تعداد کل: {invoices_count}\n"
            f"💵 مجموع مبالغ: {int(total_invoice_amount)} دلار\n\n"
            f"💡 لطفاً گزینه مورد نظر را انتخاب کنید:"
        )

        keyboard = create_wallet_menu_keyboard()

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def show_invoice_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آرشیو فاکتورها"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    with database.connection.SessionLocal() as db:
        invoices = database.crud.get_customer_invoices(db, user_id)

        if not invoices:
            await query.edit_message_text(
                "❌ شما هنوز هیچ فاکتوری ندارید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="wallet_menu")]
                ])
            )
            return

        # ذخیره لیست فاکتورها در context
        context.user_data['customer_invoices'] = [inv.id for inv in invoices]
        context.user_data['current_invoice_index'] = 0

        # نمایش اولین فاکتور
        await show_invoice_by_index(query, context, 0, invoices[0])


async def show_invoice_by_index(query, context: ContextTypes.DEFAULT_TYPE, index: int, invoice=None):
    """نمایش فاکتور بر اساس ایندکس"""
    user_id = query.from_user.id

    if not invoice:
        with database.connection.SessionLocal() as db:
            invoice_ids = context.user_data.get('customer_invoices', [])
            if index >= len(invoice_ids):
                return

            invoice = db.query(Invoice).filter(
                Invoice.id == invoice_ids[index]
            ).first()

    if not invoice:
        return

    total_invoices = len(context.user_data.get('customer_invoices', []))

    # تبدیل تاریخ به شمسی
    created_at_jalali = gregorian_to_jalali_with_time(invoice.created_at)

    caption = (
        f"🧾 **فاکتور #{invoice.id}**\n\n"
        f"⚖️ **وزن:** {invoice.weight_grams} گرم\n"
        f"💰 **قیمت هر گرم:** {invoice.price_per_gram} دلار\n"
        f"💵 **مبلغ کل:** {invoice.total_amount} دلار\n"
        f"📅 **تاریخ صدور:** {created_at_jalali}\n\n"
        f"📊 **فاکتور {index + 1} از {total_invoices}**"
    )

    # ایجاد کیبورد ناوبری
    keyboard = create_invoice_navigation_keyboard(index, total_invoices)

    try:
        # حذف پیام قبلی و ارسال عکس جدید
        await query.delete_message()

        await context.bot.send_photo(
            chat_id=user_id,
            photo=invoice.photo_file_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"خطا در نمایش فاکتور: {str(e)}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"❌ خطا در نمایش فاکتور: {str(e)}",
            reply_markup=keyboard
        )


async def handle_invoice_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر ناوبری فاکتورها"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("invoice_nav_"):
        action = query.data.split("_")[2]  # prev یا next
        current_index = int(query.data.split("_")[3])

        invoice_ids = context.user_data.get('customer_invoices', [])
        total_invoices = len(invoice_ids)

        if action == "prev" and current_index > 0:
            new_index = current_index - 1
        elif action == "next" and current_index < total_invoices - 1:
            new_index = current_index + 1
        else:
            return

        context.user_data['current_invoice_index'] = new_index

        # نمایش فاکتور جدید
        with database.connection.SessionLocal() as db:
            invoice = db.query(Invoice).filter(
                Invoice.id == invoice_ids[new_index]
            ).first()

            await show_invoice_by_index(query, context, new_index, invoice)





async def handle_wallet_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلی برای callback های مربوط به کیف پول"""
    query = update.callback_query

    if query.data == "wallet_menu":
        await show_wallet_menu_callback(query, context)
    elif query.data == "wallet_invoices":
        await show_invoice_archive(update, context)
    elif query.data == "wallet_transactions":
        await show_transactions_list(update, context)
    elif query.data.startswith("invoice_nav_"):
        await handle_invoice_navigation(update, context)
    elif query.data == "back_to_customer_menu":
        await back_to_customer_menu(query, context)
    elif query.data == "noop":
        # دکمه‌ای که هیچ کاری نمی‌کند (نمایش شماره فاکتور)
        pass


async def show_wallet_menu_callback(query, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی کیف پول از طریق callback"""
    user_id = query.from_user.id

    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)

        if not user:
            await query.edit_message_text("خطا در بارگیری اطلاعات کاربر.")
            return

        # آمار فاکتورها
        invoices_count = len(database.crud.get_customer_invoices(db, user_id))
        total_invoice_amount = sum([inv.total_amount for inv in database.crud.get_customer_invoices(db, user_id)])

        message = (
            f"💼 **کیف پول و اعتبار شما**\n\n"
            f"💰 **موجودی کیف پول:** {int(user.wallet_balance)} دلار\n"
            f"🎁 **اعتبار تخفیف:** {int(user.discount_credit)} دلار\n"
            f"📊 **مجموع اعتبار:** {int(user.wallet_balance + user.discount_credit)} دلار\n\n"
            f"🧾 **آمار فاکتورها:**\n"
            f"📋 تعداد کل: {invoices_count}\n"
            f"💵 مجموع مبالغ: {int(total_invoice_amount)} دلار\n\n"
            f"💡 لطفاً گزینه مورد نظر را انتخاب کنید:"
        )

        keyboard = create_wallet_menu_keyboard()

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def back_to_customer_menu(query, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی اصلی مشتری"""
    await query.delete_message()
    user_id = query.from_user.id
    await context.bot.send_message(
        chat_id=user_id,
        text="🔙 بازگشت به منوی اصلی",
        reply_markup=get_customer_kb(user_id)
    )