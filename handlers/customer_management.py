# handlers/customer_management.py - فایل کامل
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.customer_management import get_customers_list_keyboard, get_customer_operations_keyboard
from utils.referral import get_persian_datetime

# وضعیت‌های conversation - مقادیر جدا از سایر conversation ها
(CUSTOMER_WALLET_AMOUNT, CUSTOMER_WALLET_DESC,
 CUSTOMER_DISCOUNT_AMOUNT, CUSTOMER_DISCOUNT_DESC,
 CUSTOMER_PRINT_PRICE) = range(100, 105)

ADMIN_ID = 2138687434


async def show_customers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست مشتریان برای مدیریت - از طریق callback query"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("شما اجازه دسترسی به این قسمت را ندارید.")
        return ConversationHandler.END

    with database.connection.SessionLocal() as db:
        customers = database.crud.get_customers(db)

        if not customers:
            await query.edit_message_text("هنوز هیچ مشتری‌ای ثبت‌نام نکرده است.")
            return ConversationHandler.END

        keyboard = get_customers_list_keyboard(customers)
        await query.edit_message_text(
            "👥 **مدیریت مشتریان**\n\n"
            "لطفاً مشتری مورد نظر را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    return "CUSTOMER_SELECTION"


async def handle_customer_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب مشتری از کیبورد"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_customer_mgmt":
        await query.edit_message_text("❌ مدیریت مشتریان لغو شد.")
        return ConversationHandler.END

    if query.data == "back_to_customers_list":
        with database.connection.SessionLocal() as db:
            customers = database.crud.get_customers(db)
            keyboard = get_customers_list_keyboard(customers)
            await query.edit_message_text(
                "👥 **مدیریت مشتریان**\n\n"
                "لطفاً مشتری مورد نظر را انتخاب کنید:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        return "CUSTOMER_SELECTION"

    if query.data.startswith("customer_mgmt_"):
        customer_id = int(query.data.split("_")[2])
        context.user_data['selected_customer_id'] = customer_id

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد.")
                return ConversationHandler.END

            # دریافت وضعیت دریافت پیام
            status_emoji = database.crud.get_notification_status_emoji(customer.notification_status)
            status_text = database.crud.get_notification_status_text(customer.notification_status)

            info_text = (
                f"👤 **اطلاعات مشتری: {customer.full_name}**\n\n"
                f"**کد اختصاری:** {customer.customer_code}\n"
                f"**شماره تماس:** {customer.phone_number}\n"
                f"**موجودی کیف پول:** ${customer.wallet_balance:.2f}\n"
                f"**اعتبار تخفیف:** ${customer.discount_credit:.2f}\n"
                f"**تعداد دعوت‌ها:** {customer.referrals_count}/{customer.max_referrals}\n\n"
                f"**وضعیت دریافت پیام:** {status_emoji}\n"
                f"_{status_text}_\n\n"
                f"عملیات مورد نظر را انتخاب کنید:"
            )

            keyboard = get_customer_operations_keyboard(customer_id)
            await query.edit_message_text(
                info_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

        return "CUSTOMER_OPERATIONS"

    return "CUSTOMER_SELECTION"


async def handle_toggle_notification_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت دریافت پیام مشتری"""
    query = update.callback_query
    await query.answer()

    customer_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        # تغییر وضعیت
        customer = database.crud.toggle_customer_notification_status(db, customer_id)

        if not customer:
            await query.edit_message_text("❌ مشتری یافت نشد.")
            return ConversationHandler.END

        # دریافت اطلاعات وضعیت
        status_emoji = database.crud.get_notification_status_emoji(customer.notification_status)
        status_text = database.crud.get_notification_status_text(customer.notification_status)

        # نمایش اطلاعات به‌روز شده
        info_text = (
            f"👤 **اطلاعات مشتری: {customer.full_name}**\n\n"
            f"**کد اختصاری:** {customer.customer_code}\n"
            f"**شماره تماس:** {customer.phone_number}\n"
            f"**موجودی کیف پول:** ${customer.wallet_balance:.2f}\n"
            f"**اعتبار تخفیف:** ${customer.discount_credit:.2f}\n"
            f"**تعداد دعوت‌ها:** {customer.referrals_count}/{customer.max_referrals}\n\n"
            f"**وضعیت دریافت پیام:** {status_emoji}\n"
            f"_{status_text}_\n\n"
            f"عملیات مورد نظر را انتخاب کنید:"
        )

        keyboard = get_customer_operations_keyboard(customer_id)
        await query.edit_message_text(
            info_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

        # ارسال اطلاع‌رسانی به مشتری
        try:
            notification_text = (
                f"🔔 **تغییر وضعیت دریافت پیام**\n\n"
                f"وضعیت جدید: {status_emoji} {status_text}\n\n"
            )

            if customer.notification_status == "all":
                notification_text += "✅ شما تمام پیام‌های تخفیف مناسبتی و تبلیغاتی را دریافت خواهید کرد."
            elif customer.notification_status == "promotional_only":
                notification_text += "⚠️ شما فقط پیام‌های تبلیغاتی را دریافت خواهید کرد."
            else:  # none
                notification_text += "❌ شما هیچ پیامی دریافت نخواهید کرد."

            await context.bot.send_message(
                chat_id=customer_id,
                text=notification_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Could not notify customer {customer_id}: {e}")

    return "CUSTOMER_OPERATIONS"



async def handle_customer_operations_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت عملیات روی مشتری"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_customer_ops":
        await query.edit_message_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

    if query.data == "back_to_customers_list":
        with database.connection.SessionLocal() as db:
            customers = database.crud.get_customers(db)
            keyboard = get_customers_list_keyboard(customers)
            await query.edit_message_text(
                "👥 **مدیریت مشتریان**\n\n"
                "لطفاً مشتری مورد نظر را انتخاب کنید:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        return "CUSTOMER_SELECTION"

    customer_id = context.user_data.get('selected_customer_id')
    if not customer_id:
        await query.edit_message_text("❌ خطا در شناسایی مشتری.")
        return ConversationHandler.END

    # *** تغییر وضعیت دریافت پیام - قبل از همه چک‌ها ***
    if query.data.startswith("toggle_notification_"):
        customer_id_from_callback = int(query.data.split("_")[2])

        with database.connection.SessionLocal() as db:
            # تغییر وضعیت
            customer = database.crud.toggle_customer_notification_status(db, customer_id_from_callback)

            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد.")
                return ConversationHandler.END

            # دریافت اطلاعات وضعیت
            status_emoji = database.crud.get_notification_status_emoji(customer.notification_status)
            status_text = database.crud.get_notification_status_text(customer.notification_status)

            # نمایش اطلاعات به‌روز شده
            info_text = (
                f"👤 **اطلاعات مشتری: {customer.full_name}**\n\n"
                f"**کد اختصاری:** {customer.customer_code}\n"
                f"**شماره تماس:** {customer.phone_number}\n"
                f"**موجودی کیف پول:** ${customer.wallet_balance:.2f}\n"
                f"**اعتبار تخفیف:** ${customer.discount_credit:.2f}\n"
                f"**تعداد دعوت‌ها:** {customer.referrals_count}/{customer.max_referrals}\n\n"
                f"**وضعیت دریافت پیام:** {status_emoji}\n"
                f"_{status_text}_\n\n"
                f"عملیات مورد نظر را انتخاب کنید:"
            )

            # ارسال notification_status به کیبورد
            keyboard = get_customer_operations_keyboard(customer_id_from_callback, customer.notification_status)
            await query.edit_message_text(
                info_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            # ارسال اطلاع‌رسانی به مشتری
            try:
                notification_text = (
                    f"🔔 **تغییر وضعیت دریافت پیام**\n\n"
                    f"وضعیت جدید: {status_emoji} {status_text}\n\n"
                )

                if customer.notification_status == "all":
                    notification_text += "✅ شما تمام پیام‌های تخفیف مناسبتی و تبلیغاتی را دریافت خواهید کرد."
                elif customer.notification_status == "promotional_only":
                    notification_text += "⚠️ شما فقط پیام‌های تبلیغاتی را دریافت خواهید کرد."
                else:  # none
                    notification_text += "❌ شما هیچ پیامی دریافت نخواهید کرد."

                await context.bot.send_message(
                    chat_id=customer_id_from_callback,
                    text=notification_text,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not notify customer {customer_id_from_callback}: {e}")

        return "CUSTOMER_OPERATIONS"

    # شارژ کیف پول
    if query.data.startswith("wallet_charge_"):
        context.user_data['operation'] = 'wallet_charge'

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            await query.edit_message_text(
                f"💰 **شارژ/تسویه کیف پول {customer.full_name}**\n\n"
                f"موجودی فعلی: ${customer.wallet_balance:.2f}\n\n"
                f"مبلغ مورد نظر را وارد کنید:\n"
                f"• برای شارژ: عدد مثبت (مثلاً 50)\n"
                f"• برای کسر از حساب: عدد منفی (مثلاً -25)\n\n"
                f"⚠️ توجه: اگر مبلغ منفی باشد، موجودی نمی‌تواند منفی شود.",
                parse_mode="Markdown"
            )
        return CUSTOMER_WALLET_AMOUNT

    # شارژ اعتبار تخفیف
    elif query.data.startswith("discount_charge_"):
        context.user_data['operation'] = 'discount_charge'

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            await query.edit_message_text(
                f"🎁 **شارژ/تسویه اعتبار تخفیف {customer.full_name}**\n\n"
                f"اعتبار فعلی: ${customer.discount_credit:.2f}\n\n"
                f"مبلغ مورد نظر را وارد کنید:\n"
                f"• برای شارژ: عدد مثبت (مثلاً 50)\n"
                f"• برای کسر: عدد منفی (مثلاً -25)\n\n"
                f"⚠️ توجه: اگر مبلغ منفی باشد، اعتبار نمی‌تواند منفی شود.",
                parse_mode="Markdown"
            )
        return CUSTOMER_DISCOUNT_AMOUNT

    # تنظیم قیمت کار
    elif query.data.startswith("set_work_price_"):
        context.user_data['operation'] = 'set_work_price'

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            current_price = database.crud.get_price_per_gram(db)
            await query.edit_message_text(
                f"💳 **تعیین هزینه انجام کار برای {customer.full_name}**\n\n"
                f"قیمت کلی سیستم: ${current_price:.2f} در هر گرم\n\n"
                f"لطفاً قیمت جدید هر گرم پرینت را به دلار وارد کنید:",
                parse_mode="Markdown"
            )
        return CUSTOMER_PRINT_PRICE

    # مشاهده تراکنش‌ها
    elif query.data.startswith("view_customer_transactions_"):
        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد.")
                return ConversationHandler.END

            transactions = database.crud.get_user_wallet_transactions(db, customer_id, limit=20)

            if not transactions:
                message = f"📊 **تراکنش‌های {customer.full_name}**\n\nهیچ تراکنشی یافت نشد."
            else:
                message = f"📊 **آخرین تراکنش‌های {customer.full_name}**\n\n"

                for trans in transactions:
                    trans_type_icon = "➕" if trans.amount > 0 else "➖"
                    trans_type_text = "شارژ" if trans.amount > 0 else "برداشت"

                    if trans.transaction_type == "admin_adjustment":
                        type_desc = "💰 کیف پول"
                    elif trans.transaction_type == "discount_credit_adjustment":
                        type_desc = "🎁 اعتبار تخفیف"
                    else:
                        type_desc = "💼 سایر"

                    message += f"{trans_type_icon} **{trans_type_text} {type_desc}**\n"
                    message += f"مبلغ: ${abs(trans.amount):.2f}\n"
                    message += f"توضیح: {trans.description}\n"
                    message += f"تاریخ: {trans.created_at.strftime('%Y/%m/%d %H:%M')}\n"
                    message += "───────────\n"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"customer_mgmt_{customer_id}")]
            ])

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            return "CUSTOMER_SELECTION"

    return "CUSTOMER_OPERATIONS"

async def get_customer_wallet_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ شارژ/تسویه کیف پول"""
    try:
        amount = float(update.message.text)
        customer_id = context.user_data.get('selected_customer_id')
        context.user_data['amount'] = amount

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            if amount < 0 and customer.wallet_balance + amount < 0:
                await update.message.reply_text(
                    f"❌ **خطا در مبلغ**\n\n"
                    f"موجودی فعلی مشتری: ${customer.wallet_balance:.2f}\n"
                    f"مبلغ درخواستی: ${amount:.2f}\n"
                    f"موجودی جدید: ${customer.wallet_balance + amount:.2f}\n\n"
                    f"موجودی کیف پول نمی‌تواند منفی شود!\n"
                    f"لطفاً مبلغ کمتری وارد کنید.",
                    parse_mode="Markdown"
                )
                return CUSTOMER_WALLET_AMOUNT

            operation_type = "شارژ" if amount > 0 else "تسویه/برداشت از"
            await update.message.reply_text(
                f"💰 **{operation_type} کیف پول {customer.full_name}**\n\n"
                f"مبلغ: ${abs(amount):.2f}\n"
                f"موجودی فعلی: ${customer.wallet_balance:.2f}\n"
                f"موجودی جدید: ${customer.wallet_balance + amount:.2f}\n\n"
                f"لطفاً علت/توضیح این تراکنش را وارد کنید:",
                parse_mode="Markdown"
            )

        return CUSTOMER_WALLET_DESC

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک عدد معتبر وارد کنید.\n"
            "مثال: 50 یا -25 یا 12.5"
        )
        return CUSTOMER_WALLET_AMOUNT

async def get_customer_wallet_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات و اجرای تراکنش کیف پول"""
    description = update.message.text.strip()

    if not description:
        await update.message.reply_text("❌ لطفاً توضیح تراکنش را وارد کنید.")
        return CUSTOMER_WALLET_DESC

    customer_id = context.user_data.get('selected_customer_id')
    amount = context.user_data['amount']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            # شارژ کیف پول - باید receipt_id هم پاس بدیم
            # برای شارژ دستی یک رسید مجازی ایجاد می‌کنیم

            if amount > 0:  # فقط برای شارژ (نه برداشت)
                # ایجاد یک رسید مجازی برای تخصیص به صندوق‌ها
                virtual_receipt = database.crud.create_receipt(
                    db=db,
                    user_id=customer_id,
                    file_id="manual_charge",  # شناسه مجازی
                    file_name="شارژ دستی توسط ادمین",
                    description=description
                )

                # تایید فوری رسید مجازی
                database.crud.confirm_receipt(db, virtual_receipt.id, admin_id)

                receipt_id = virtual_receipt.id
            else:
                receipt_id = None

            updated_customer = database.crud.update_user_wallet_balance(
                db, customer_id, amount, description, admin_id, receipt_id
            )

            if updated_customer:
                operation_type = "شارژ شد" if amount > 0 else "کسر شد"
                operation_emoji = "➕" if amount > 0 else "➖"

                # نمایش تخصیص به صندوق‌ها
                allocation_text = ""
                if amount > 0 and receipt_id:
                    vaults = database.crud.get_all_vaults(db)
                    allocations = []
                    for vault in vaults:
                        if vault.allocation_percentage > 0:
                            allocated = (amount * vault.allocation_percentage) / 100
                            allocations.append(f"• {vault.name}: ${allocated:.2f} ({vault.allocation_percentage}%)")

                    if allocations:
                        allocation_text = "\n\n💼 **تخصیص به صندوق‌ها:**\n" + "\n".join(allocations)

                await update.message.reply_text(
                    f"✅ **تراکنش با موفقیت انجام شد!**\n\n"
                    f"👤 مشتری: {updated_customer.full_name}\n"
                    f"💰 مبلغ: ${abs(amount):.2f} {operation_type}\n"
                    f"📝 توضیح: {description}\n"
                    f"💳 موجودی جدید: ${updated_customer.wallet_balance:.2f}"
                    f"{allocation_text}\n\n"
                    f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
                    parse_mode="Markdown"
                )

                try:
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text=f"💳 **تغییر موجودی کیف پول** {operation_emoji}\n\n"
                             f"مبلغ: ${abs(amount):.2f}\n"
                             f"توضیح: {description}\n"
                             f"موجودی جدید: ${updated_customer.wallet_balance:.2f}\n"
                             f"تاریخ: {get_persian_datetime()}",
                        parse_mode="Markdown"
                    )
                except:
                    pass

            else:
                await update.message.reply_text("❌ خطا در انجام تراکنش.")

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return CUSTOMER_WALLET_DESC

    context.user_data.clear()
    return ConversationHandler.END

async def get_customer_discount_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ شارژ/تسویه اعتبار تخفیف"""
    try:
        amount = float(update.message.text)
        customer_id = context.user_data.get('selected_customer_id')
        context.user_data['amount'] = amount

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            if amount < 0 and customer.discount_credit + amount < 0:
                await update.message.reply_text(
                    f"❌ **خطا در مبلغ**\n\n"
                    f"اعتبار تخفیف فعلی: ${customer.discount_credit:.2f}\n"
                    f"مبلغ درخواستی: ${amount:.2f}\n"
                    f"اعتبار جدید: ${customer.discount_credit + amount:.2f}\n\n"
                    f"اعتبار تخفیف نمی‌تواند منفی شود!\n"
                    f"لطفاً مبلغ کمتری وارد کنید.",
                    parse_mode="Markdown"
                )
                return CUSTOMER_DISCOUNT_AMOUNT

            operation_type = "شارژ" if amount > 0 else "تسویه/کسر از"
            await update.message.reply_text(
                f"🎁 **{operation_type} اعتبار تخفیف {customer.full_name}**\n\n"
                f"مبلغ: ${abs(amount):.2f}\n"
                f"اعتبار فعلی: ${customer.discount_credit:.2f}\n"
                f"اعتبار جدید: ${customer.discount_credit + amount:.2f}\n\n"
                f"لطفاً علت/توضیح این تراکنش را وارد کنید:",
                parse_mode="Markdown"
            )

        return CUSTOMER_DISCOUNT_DESC

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک عدد معتبر وارد کنید.\n"
            "مثال: 50 یا -25 یا 12.5"
        )
        return CUSTOMER_DISCOUNT_AMOUNT


async def get_customer_discount_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات و اجرای تراکنش اعتبار تخفیف"""
    description = update.message.text.strip()

    if not description:
        await update.message.reply_text("❌ لطفاً توضیح تراکنش را وارد کنید.")
        return CUSTOMER_DISCOUNT_DESC

    customer_id = context.user_data.get('selected_customer_id')
    amount = context.user_data['amount']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            updated_customer = database.crud.update_user_discount_credit(
                db, customer_id, amount, description, admin_id
            )

            if updated_customer:
                operation_type = "شارژ شد" if amount > 0 else "کسر شد"
                operation_emoji = "➕" if amount > 0 else "➖"

                await update.message.reply_text(
                    f"✅ **تراکنش با موفقیت انجام شد!**\n\n"
                    f"👤 مشتری: {updated_customer.full_name}\n"
                    f"🎁 مبلغ: ${abs(amount):.2f} {operation_type}\n"
                    f"📝 توضیح: {description}\n"
                    f"💎 اعتبار تخفیف جدید: ${updated_customer.discount_credit:.2f}\n\n"
                    f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
                    parse_mode="Markdown"
                )

                try:
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text=f"🎁 **تغییر اعتبار تخفیف** {operation_emoji}\n\n"
                             f"مبلغ: ${abs(amount):.2f}\n"
                             f"توضیح: {description}\n"
                             f"اعتبار جدید: ${updated_customer.discount_credit:.2f}\n"
                             f"تاریخ: {get_persian_datetime()}",
                        parse_mode="Markdown"
                    )
                except:
                    pass

            else:
                await update.message.reply_text("❌ خطا در انجام تراکنش.")

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return CUSTOMER_DISCOUNT_DESC

    context.user_data.clear()
    return ConversationHandler.END


async def get_customer_print_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت جدید پرینت"""
    try:
        new_price = float(update.message.text)

        if new_price <= 0:
            await update.message.reply_text("❌ قیمت باید عددی مثبت باشد. لطفاً دوباره تلاش کنید.")
            return CUSTOMER_PRINT_PRICE

        customer_id = context.user_data.get('selected_customer_id')

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            # به‌روزرسانی قیمت برای مشتری خاص
            # فعلاً از قیمت کلی سیستم استفاده می‌کنیم
            database.crud.set_price_per_gram(db, new_price)

            await update.message.reply_text(
                f"✅ **قیمت پرینت تنظیم شد!**\n\n"
                f"👤 مشتری: {customer.full_name}\n"
                f"💳 قیمت جدید: ${new_price:.2f} در هر گرم\n\n"
                f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
                parse_mode="Markdown"
            )

            # اطلاع‌رسانی به مشتری
            try:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=f"💳 **اطلاع‌رسانی تغییر قیمت**\n\n"
                         f"قیمت پرینت شما به ${new_price:.2f} در هر گرم تغییر یافت.\n"
                         f"تاریخ: {get_persian_datetime()}",
                    parse_mode="Markdown"
                )
            except:
                pass

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return CUSTOMER_PRINT_PRICE

    context.user_data.clear()
    # بازگشت به حالت انتخاب مشتری بدون پایان conversation
    return "CUSTOMER_SELECTION"


async def cancel_customer_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند مدیریت مشتریان"""
    await update.message.reply_text("❌ عملیات لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END