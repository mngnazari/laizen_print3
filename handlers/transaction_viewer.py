# handlers/transaction_viewer.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database.crud
import database.connection
from database.models import WalletTransaction, Invoice
import jdatetime
from datetime import datetime, timedelta
from database.crud import IRAN_TZ
import logging

logger = logging.getLogger(__name__)

# تعداد تراکنش در هر صفحه
TRANSACTIONS_PER_PAGE = 10


def gregorian_to_jalali_full(gregorian_datetime):
    """تبدیل کامل تاریخ و ساعت میلادی به شمسی"""
    try:
        if gregorian_datetime.tzinfo is None:
            gregorian_datetime = gregorian_datetime.replace(tzinfo=IRAN_TZ)
        else:
            gregorian_datetime = gregorian_datetime.astimezone(IRAN_TZ)

        j_datetime = jdatetime.datetime.fromgregorian(datetime=gregorian_datetime)
        return j_datetime.strftime('%Y/%m/%d - %H:%M')
    except Exception as e:
        logger.error(f"خطا در تبدیل تاریخ: {e}")
        return gregorian_datetime.strftime('%Y/%m/%d - %H:%M')


def create_transaction_filters_keyboard(current_filter="all", current_page=0):
    """کیبورد فیلترهای تراکنش - فقط نوع تراکنش"""
    keyboard = []

    # فقط فیلترهای نوع تراکنش
    filter_row = []
    filters = [
        ("📊 همه", "all"),
        ("💰 واریز", "deposit"),
        ("💸 برداشت", "withdrawal")
    ]

    for label, filter_type in filters:
        if current_filter == filter_type:
            filter_row.append(InlineKeyboardButton(
                f"✅ {label}",
                callback_data="noop"
            ))
        else:
            filter_row.append(InlineKeyboardButton(
                label,
                callback_data=f"trans_filter_{filter_type}_0"
            ))

    keyboard.append(filter_row)

    # دکمه بازگشت
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به کیف پول", callback_data="wallet_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def create_transaction_navigation_keyboard(current_page, total_pages, filter_type="all"):
    """کیبورد ناوبری صفحات تراکنش"""
    keyboard = []

    # ردیف اول: فیلترهای نوع (همیشه نمایش داده شود)
    filter_row = []
    filters = [
        ("📊 همه", "all"),
        ("💰 واریز", "deposit"),
        ("💸 برداشت", "withdrawal")
    ]

    for label, ftype in filters:
        if filter_type == ftype:
            filter_row.append(InlineKeyboardButton(
                f"✅ {label}",
                callback_data="noop"
            ))
        else:
            filter_row.append(InlineKeyboardButton(
                label,
                callback_data=f"trans_filter_{ftype}_0"
            ))

    keyboard.append(filter_row)

    # ردیف دوم: ناوبری (فقط اگر بیشتر از 1 صفحه داشته باشیم)
    if total_pages > 1:
        nav_row = []

        # دکمه قبلی
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(
                "⬅️ قبلی",
                callback_data=f"trans_page_{filter_type}_{current_page - 1}"
            ))

        # نمایش صفحه فعلی
        nav_row.append(InlineKeyboardButton(
            f"📄 {current_page + 1}/{total_pages}",
            callback_data="noop"
        ))

        # دکمه بعدی
        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(
                "➡️ بعدی",
                callback_data=f"trans_page_{filter_type}_{current_page + 1}"
            ))

        keyboard.append(nav_row)

    # ردیف آخر: بازگشت
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به کیف پول", callback_data="wallet_menu")
    ])

    return InlineKeyboardMarkup(keyboard)


def get_transaction_emoji_and_type(transaction_type):
    """دریافت ایموجی و نوع فارسی تراکنش"""
    transaction_types = {
        "admin_adjustment": ("⚙️", "تنظیم کیف پول"),
        "referral_bonus": ("🎁", "پاداش دعوت"),
        "invoice_payment": ("💸", "پرداخت فاکتور"),
        "discount_credit_adjustment": ("🎟", "تنظیم اعتبار تخفیف"),
        "receipt_charge": ("💳", "شارژ از رسید"),
        "system_bonus": ("🎉", "پاداش سیستم")
    }

    return transaction_types.get(transaction_type, ("💰", "تراکنش"))


async def show_transactions_list(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 filter_type="all", page=0):
    """نمایش لیست تراکنش‌های خود مشتری"""
    query = update.callback_query
    if query:
        await query.answer()

    user_id = query.from_user.id if query else update.effective_user.id

    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)

        if not user:
            text = "❌ خطا در بارگیری اطلاعات کاربر"
            if query:
                await query.edit_message_text(text)
            return

        # دریافت تراکنش‌های کیف پول
        wallet_transactions = database.crud.get_user_wallet_transactions(db, user_id, limit=1000)

        # دریافت فاکتورها برای نمایش برداشت‌ها
        invoices = database.crud.get_customer_invoices(db, user_id)

        # ترکیب تراکنش‌ها
        all_transactions = []

        # اضافه کردن تراکنش‌های کیف پول
        for trans in wallet_transactions:
            all_transactions.append({
                'type': 'wallet',
                'data': trans,
                'created_at': trans.created_at,
                'amount': trans.amount
            })

        # اضافه کردن فاکتورها به عنوان برداشت
        for inv in invoices:
            all_transactions.append({
                'type': 'invoice',
                'data': inv,
                'created_at': inv.created_at,
                'amount': -inv.total_amount  # منفی چون برداشت است
            })

        # مرتب‌سازی بر اساس تاریخ (جدیدترین اول)
        all_transactions.sort(key=lambda x: x['created_at'], reverse=True)

        # فیلتر بر اساس نوع
        if filter_type == "deposit":
            filtered_trans = [t for t in all_transactions if t['amount'] > 0]
        elif filter_type == "withdrawal":
            filtered_trans = [t for t in all_transactions if t['amount'] < 0]
        else:
            filtered_trans = all_transactions

        # اگر تراکنشی نباشد
        if not filtered_trans:
            message = (
                "📊 **تاریخچه تراکنش‌ها**\n\n"
                f"💰 موجودی فعلی: {user.wallet_balance:,.0f} دلار\n"
                f"🎁 اعتبار تخفیف: {user.discount_credit:,.0f} دلار\n\n"
                "❌ هیچ تراکنشی با این فیلتر یافت نشد."
            )

            keyboard = create_transaction_filters_keyboard(filter_type, page)

            if query:
                await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
            else:
                await update.message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)
            return

        # محاسبه موجودی بعد از هر تراکنش (معکوس از آخر به اول)
        current_balance = user.wallet_balance
        for trans in filtered_trans:
            trans['balance_after'] = current_balance
            current_balance -= trans['amount']

        # Pagination
        total_count = len(filtered_trans)
        total_pages = max(1, (total_count + TRANSACTIONS_PER_PAGE - 1) // TRANSACTIONS_PER_PAGE)

        if page >= total_pages:
            page = total_pages - 1
        if page < 0:
            page = 0

        start_idx = page * TRANSACTIONS_PER_PAGE
        end_idx = min(start_idx + TRANSACTIONS_PER_PAGE, total_count)
        page_transactions = filtered_trans[start_idx:end_idx]

        # ساخت پیام
        filter_names = {
            "all": "همه تراکنش‌ها",
            "deposit": "واریزی‌ها",
            "withdrawal": "برداشت‌ها"
        }

        message = (
            f"📊 **تاریخچه تراکنش‌ها**\n"
            f"🔍 فیلتر: {filter_names.get(filter_type, 'همه')}\n\n"
            f"💰 موجودی فعلی: {user.wallet_balance:,.0f} دلار\n"
            f"🎁 اعتبار تخفیف: {user.discount_credit:,.0f} دلار\n"
            f"📈 تعداد تراکنش‌ها: {total_count}\n\n"
            "─────────────────\n\n"
        )

        # اضافه کردن تراکنش‌های صفحه
        # اضافه کردن تراکنش‌های صفحه (شماره‌گذاری معکوس: قدیمی‌ترین = 1)
        for idx, trans_item in enumerate(page_transactions):
            i = total_count - start_idx - idx
            trans_type = trans_item['type']
            trans_data = trans_item['data']
            amount = trans_item['amount']
            balance_after = trans_item['balance_after']
            created_at_jalali = gregorian_to_jalali_full(trans_item['created_at'])

            # تعیین عنوان و ایموجی بر اساس نوع
            if trans_type == 'wallet':
                transaction_type = trans_data.transaction_type

                if amount > 0:  # واریز
                    if transaction_type == "admin_adjustment":
                        title = f"💰 واریز +{amount:,.0f} دلار"
                    elif transaction_type == "referral_bonus":
                        title = f"🎁 پاداش معرفی +{amount:,.0f} دلار"
                    elif transaction_type == "receipt_charge":
                        title = f"💳 شارژ از رسید +{amount:,.0f} دلار"
                    elif transaction_type == "system_bonus":
                        title = f"🎉 جایزه سیستمی +{amount:,.0f} دلار"
                    elif transaction_type == "discount_credit_adjustment":
                        title = f"🎁 شارژ اعتبار تخفیف +{amount:,.0f} دلار"
                    else:
                        title = f"💰 واریز +{amount:,.0f} دلار"
                else:  # برداشت
                    if transaction_type == "admin_adjustment":
                        title = f"💸 برداشت {amount:,.0f} دلار"
                    elif transaction_type == "invoice_payment":
                        title = f"🧾 پرداخت فاکتور {amount:,.0f} دلار"
                    elif transaction_type == "discount_credit_adjustment":
                        title = f"🎟 کسر اعتبار تخفیف {amount:,.0f} دلار"
                    else:
                        title = f"💸 برداشت {amount:,.0f} دلار"

                desc = trans_data.description or "بدون توضیحات"

            elif trans_type == 'invoice':
                title = f"💸 پرداخت فاکتور #{trans_data.id} ({amount:,.0f} دلار)"
                desc = f"وزن: {trans_data.weight_grams}g | قیمت: {trans_data.price_per_gram} دلار/گرم"

            # ساخت پیام تراکنش
            message += (
                f"**{i}.** {title} | موجودی پس از تراکنش: {balance_after:,.0f} دلار\n"
                f"   📝 {desc}\n"
                f"   📅 {created_at_jalali}\n"
                "   ─────────────────\n\n"
            )

        message += f"\n📄 صفحه {page + 1} از {total_pages}"

        # کیبورد - همیشه فیلترها نمایش داده شود
        keyboard = create_transaction_navigation_keyboard(page, total_pages, filter_type)

        if query:
            await query.edit_message_text(message, parse_mode="Markdown", reply_markup=keyboard)
        else:
            await update.message.reply_text(message, parse_mode="Markdown", reply_markup=keyboard)


async def handle_transaction_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback های تراکنش‌های مشتری"""
    query = update.callback_query

    # trans_filter_TYPE_PAGE
    if query.data.startswith("trans_filter_"):
        parts = query.data.split("_")
        filter_type = parts[2]  # all, deposit, withdrawal
        page = int(parts[3]) if len(parts) > 3 else 0
        await show_transactions_list(update, context, filter_type=filter_type, page=page)

    # trans_page_TYPE_PAGE
    elif query.data.startswith("trans_page_"):
        parts = query.data.split("_")
        filter_type = parts[2]
        page = int(parts[3])
        await show_transactions_list(update, context, filter_type=filter_type, page=page)


# ========================================
# تابع نمایش تراکنش‌ها برای ادمین
# ========================================

async def handle_admin_transaction_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر مشاهده تراکنش‌های مشتری توسط ادمین"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("view_customer_transactions_"):
        customer_id = int(query.data.split("_")[3])

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد.")
                return

            # دریافت تراکنش‌ها
            transactions = database.crud.get_user_wallet_transactions(db, customer_id, limit=20)

            if not transactions:
                message = f"📊 **تراکنش‌های {customer.full_name}**\n\nهیچ تراکنشی یافت نشد."
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 بازگشت", callback_data=f"customer_mgmt_{customer_id}")]
                ])
            else:
                message = f"📊 **آخرین تراکنش‌های {customer.full_name}**\n\n"

                for trans in transactions:
                    trans_type_icon = "➕" if trans.amount > 0 else "➖"
                    trans_type_text = "شارژ" if trans.amount > 0 else "برداشت"

                    # تعیین نوع تراکنش
                    emoji, type_desc = get_transaction_emoji_and_type(trans.transaction_type)

                    message += f"{trans_type_icon} **{trans_type_text} {type_desc}**\n"
                    message += f"مبلغ: ${abs(trans.amount):.2f}\n"
                    message += f"توضیح: {trans.description}\n"
                    message += f"تاریخ: {gregorian_to_jalali_full(trans.created_at)}\n"
                    message += "───────────\n"

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 تازه‌سازی", callback_data=f"view_customer_transactions_{customer_id}")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data=f"customer_mgmt_{customer_id}")]
                ])

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )