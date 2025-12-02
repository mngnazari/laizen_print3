# ایجاد فایل جدید: handlers/vault_management.py
from sqlalchemy import func
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.vault_management import (
    get_vaults_list_keyboard,
    get_vault_detail_keyboard,
    get_vault_transactions_keyboard,
    get_expense_vault_selection_keyboard
)
from utils.referral import get_persian_datetime
import logging
from sqlalchemy import func
logger = logging.getLogger(__name__)

# States برای ConversationHandler
# در handlers/vault_management.py - اصلاح state ها
(VAULT_CREATE_NAME, VAULT_CREATE_PERCENT,
 VAULT_SET_PERCENT, VAULT_RENAME,
 EXPENSE_AMOUNT, EXPENSE_DESC,
 PETTY_CASH_WITHDRAW_AMOUNT, PETTY_CASH_WITHDRAW_DESC,
 GOLD_BUY_WEIGHT, GOLD_BUY_PRICE_TOMAN, GOLD_BUY_EXCHANGE_RATE, GOLD_BUY_DESC,
 GOLD_SELL_WEIGHT, GOLD_SELL_PRICE_TOMAN, GOLD_SELL_EXCHANGE_RATE, GOLD_SELL_DESC) = range(300, 316)

ADMIN_ID = 2138687434


async def show_vaults_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی صندوق‌ها و هزینه‌ها"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("شما اجازه دسترسی ندارید.")
        return

    from keyboards.vault_menu import get_vaults_menu_keyboard

    message = (
        f"💰 **صندوق‌ها و هزینه‌ها**\n\n"
        f"📋 **عملیات موجود:**\n\n"
        f"💼 **مدیریت صندوق‌ها:**\n"
        f"• مشاهده لیست صندوق‌ها و موجودی\n"
        f"• ایجاد صندوق جدید\n"
        f"• تنظیم درصد تخصیص\n"
        f"• مشاهده تراکنش‌ها\n\n"
        f"💸 **ثبت هزینه:**\n"
        f"• ثبت هزینه و برداشت از صندوق\n"
        f"• انتخاب صندوق مبدا\n\n"
        f"لطفاً عملیات مورد نظر را انتخاب کنید:"
    )

    keyboard = get_vaults_menu_keyboard()
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def show_vaults_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست صندوق‌ها"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("شما اجازه دسترسی ندارید.")
        return

    with database.connection.SessionLocal() as db:
        # اطمینان از وجود تنخواه گردان
        database.crud.ensure_petty_cash_vault(db)
        database.crud.update_petty_cash_percentage(db)

        # خواندن مجدد صندوق‌ها برای اطمینان از داده‌های به‌روز
        db.expire_all()
        vaults = database.crud.get_all_vaults(db)
        summary = database.crud.get_vaults_summary(db)

        # سورت صندوق‌ها برای نمایش در متن
        sorted_vaults = sorted(vaults, key=lambda v: v.allocation_percentage, reverse=True)

        message = (
            f"💰 **مدیریت صندوق‌های مجازی**\n\n"
            f"📊 **خلاصه آمار:**\n"
            f"🏦 تعداد صندوق‌ها: {summary['total_vaults']}\n"
            f"💵 مجموع موجودی: ${summary['total_balance']:.0f}\n"
            f"📈 درصد تخصیص یافته: {summary['total_allocated_percentage']:.1f}%\n"
            f"📉 درصد باقیمانده: {summary['remaining_percentage']:.1f}%\n\n"
        )

        if vaults:
            message += "📋 **لیست صندوق‌ها:**\n"
            for v in sorted_vaults:
                # ایموجی بر اساس موجودی
                if v.balance > 0:
                    status = "💚"
                elif v.balance < 0:
                    status = "🔴"
                else:
                    status = "💰"

                message += f"{status} %{int(v.allocation_percentage)} {v.name}: ${v.balance:.0f}\n"
        else:
            message += "❌ هنوز هیچ صندوقی ایجاد نشده است."

        keyboard = get_vaults_list_keyboard(vaults)
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def show_vault_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات یک صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        if not vault:
            await query.edit_message_text("❌ صندوق یافت نشد.")
            return

        # آمار تراکنش‌ها
        transactions = database.crud.get_vault_transactions(db, vault_id, limit=10)
        total_deposits = sum(t.amount for t in transactions if t.amount > 0)
        total_withdrawals = abs(sum(t.amount for t in transactions if t.amount < 0))

        # آمار طلا
        gold_info = ""
        if vault.gold_balance > 0:
            gold_summary = database.crud.get_vault_gold_summary(db, vault_id)
            gold_info = (
                f"\n💎 **دارایی طلا:**\n"
                f"🥇 موجودی: {vault.gold_balance:.3f} گرم\n"
                f"💵 میانگین خرید: ${gold_summary['avg_buy_price']:.2f}/گرم\n"
            )

        # تبدیل تاریخ ایجاد به شمسی
        import jdatetime
        from datetime import timezone, timedelta

        iran_tz = timezone(timedelta(hours=3, minutes=30))
        created_time_iran = vault.created_at.astimezone(iran_tz)
        jalali_date = jdatetime.datetime.fromtimestamp(created_time_iran.timestamp())
        created_date_str = jalali_date.strftime('%Y/%m/%d')

        message = (
            f"💰 **جزئیات صندوق: {vault.name}**\n\n"
            f"💵 **موجودی نقد:** ${vault.balance:.2f}\n"
            f"{gold_info}"
            f"📊 **درصد تخصیص:** {vault.allocation_percentage}%\n"
            f"📅 **تاریخ ایجاد:** {created_date_str}\n\n"
            f"📈 **آمار تراکنش‌های نقدی:**\n"
            f"⬆️ واریزها: ${total_deposits:.2f}\n"
            f"⬇️ برداشت‌ها: ${total_withdrawals:.2f}\n"
            f"📜 تعداد تراکنش‌ها: {len(transactions)}\n\n"
            f"💡 لطفاً عملیات مورد نظر را انتخاب کنید:"
        )

        keyboard = get_vault_detail_keyboard(vault_id, vault.name)
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def start_create_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ایجاد صندوق جدید"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        # اطمینان از وجود تنخواه
        petty_cash = database.crud.ensure_petty_cash_vault(db)

        # محاسبه درصد باقیمانده (بدون احتساب تنخواه)
        other_vaults_total = db.query(func.sum(database.models.Vault.allocation_percentage)).filter(
            database.models.Vault.is_active == True,
            database.models.Vault.id != petty_cash.id
        ).scalar() or 0.0

        remaining = 100.0 - other_vaults_total

        if remaining <= 0:
            await query.edit_message_text(
                f"❌ **امکان ایجاد صندوق جدید وجود ندارد!**\n\n"
                f"📊 مجموع درصد تخصیص صندوق‌ها به 100% رسیده است.\n"
                f"برای ایجاد صندوق جدید، ابتدا درصد یکی از صندوق‌های موجود را کاهش دهید.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="vault_list")
                ]])
            )
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"➕ **ایجاد صندوق جدید**\n\n"
                 f"📊 درصد باقیمانده برای تخصیص: {remaining:.1f}%\n\n"
                 f"لطفاً نام صندوق را وارد کنید:\n"
                 f"(مثال: تحقیقات، تبلیغات، مالیات، نگهداری دستگاه)",
            parse_mode="Markdown"
        )

        # حذف پیام قبلی
        await query.delete_message()

        return VAULT_CREATE_NAME


async def get_vault_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام صندوق جدید"""
    name = update.message.text.strip()

    if len(name) < 2:
        await update.message.reply_text("❌ نام صندوق باید حداقل 2 کاراکتر باشد.")
        return VAULT_CREATE_NAME

    context.user_data['new_vault_name'] = name

    with database.connection.SessionLocal() as db:
        # اطمینان از وجود تنخواه
        petty_cash = database.crud.ensure_petty_cash_vault(db)

        # محاسبه درصد باقیمانده (بدون احتساب تنخواه)
        other_vaults_total = db.query(func.sum(database.models.Vault.allocation_percentage)).filter(
            database.models.Vault.is_active == True,
            database.models.Vault.id != petty_cash.id
        ).scalar() or 0.0

        remaining = 100.0 - other_vaults_total

    await update.message.reply_text(
        f"📊 **تنظیم درصد تخصیص**\n\n"
        f"💰 صندوق: {name}\n"
        f"📈 درصد باقیمانده: {remaining:.1f}%\n\n"
        f"لطفاً درصد تخصیص این صندوق از درآمدها را وارد کنید:\n"
        f"(عدد بین 0 تا {remaining:.1f})\n\n"
        f"مثال: 10 یعنی 10% از هر درآمد به این صندوق واریز شود.",
        parse_mode="Markdown"
    )

    return VAULT_CREATE_PERCENT


async def get_vault_percent_and_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت درصد و ایجاد صندوق"""
    logger.info(f"get_vault_percent_and_create called with text: {update.message.text}")

    try:
        percent = float(update.message.text.strip())
        logger.info(f"Parsed percent: {percent}")

        if percent < 0:
            await update.message.reply_text("❌ درصد نمی‌تواند منفی باشد!")
            return VAULT_CREATE_PERCENT

        name = context.user_data.get('new_vault_name')
        logger.info(f"Vault name from context: {name}")

        if not name:
            await update.message.reply_text("❌ خطا: نام صندوق یافت نشد. لطفاً دوباره شروع کنید.")
            context.user_data.clear()
            return ConversationHandler.END

        with database.connection.SessionLocal() as db:
            logger.info(f"Creating vault: {name} with {percent}%")

            vault = database.crud.create_vault(db, name, percent)
            logger.info(f"Vault created with id: {vault.id}")

            database.crud.update_petty_cash_percentage(db)
            logger.info("Petty cash updated")

            summary = database.crud.get_vaults_summary(db)
            logger.info(f"Summary retrieved: {summary}")

            # ایجاد کیبورد بازگشت
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به لیست صندوق‌ها", callback_data="vault_list")
            ]])

            await update.message.reply_text(
                f"✅ **صندوق با موفقیت ایجاد شد!**\n\n"
                f"💰 نام: {vault.name}\n"
                f"📊 درصد تخصیص: {vault.allocation_percentage}%\n"
                f"💵 موجودی اولیه: $0\n\n"
                f"📈 درصد باقیمانده: {summary['remaining_percentage']:.1f}%\n"
                f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

            logger.info("Success message sent")

        context.user_data.clear()
        logger.info("Conversation ended successfully")
        return ConversationHandler.END

    except ValueError as e:
        error_msg = str(e)
        logger.error(f"ValueError: {error_msg}")

        if "بیشتر از 100%" in error_msg:
            await update.message.reply_text(
                f"❌ {error_msg}\n\n"
                f"لطفاً عدد کمتری وارد کنید.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return VAULT_CREATE_PERCENT

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ خطای غیرمنتظره:\n{str(e)}\n\nلطفاً دوباره تلاش کنید.",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

async def start_set_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تنظیم درصد صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[3])
    context.user_data['vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        # جلوگیری از تغییر درصد تنخواه
        if vault.name == "تنخواه گردان":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ **امکان تغییر درصد تنخواه گردان وجود ندارد**\n\n"
                     f"درصد این صندوق به صورت خودکار محاسبه می‌شود.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{vault_id}")
                ]])
            )
            await query.delete_message()
            return ConversationHandler.END

        # اطمینان از وجود تنخواه
        petty_cash = database.crud.ensure_petty_cash_vault(db)

        # محاسبه درصد سایر صندوق‌ها (بدون این صندوق و بدون تنخواه)
        other_vaults_total = db.query(func.sum(database.models.Vault.allocation_percentage)).filter(
            database.models.Vault.is_active == True,
            database.models.Vault.id != vault_id,
            database.models.Vault.id != petty_cash.id
        ).scalar() or 0.0

        # حداکثر درصد قابل تخصیص
        max_percent = 100.0 - other_vaults_total

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"📊 **تنظیم درصد تخصیص**\n\n"
                 f"💰 صندوق: {vault.name}\n"
                 f"📈 درصد فعلی: {vault.allocation_percentage}%\n"
                 f"📉 حداکثر درصد قابل تخصیص: {max_percent:.1f}%\n\n"
                 f"لطفاً درصد جدید را وارد کنید:\n"
                 f"(عدد بین 0 تا {max_percent:.1f})",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return VAULT_SET_PERCENT

async def update_vault_percent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بروزرسانی درصد صندوق"""
    try:
        new_percent = float(update.message.text.strip())

        if new_percent < 0:
            await update.message.reply_text("❌ درصد نمی‌تواند منفی باشد!")
            return VAULT_SET_PERCENT

        vault_id = context.user_data['vault_id']

        with database.connection.SessionLocal() as db:
            vault = database.crud.update_vault_allocation(db, vault_id, new_percent)
            summary = database.crud.get_vaults_summary(db)

            # ایجاد کیبورد بازگشت
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به صندوق", callback_data=f"vault_detail_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **درصد تخصیص بروزرسانی شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"📊 درصد جدید: {vault.allocation_percentage}%\n"
                f"📉 درصد باقیمانده کل: {summary['remaining_percentage']:.1f}%\n"
                f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        error_msg = str(e)
        if "بیشتر از 100%" in error_msg:
            await update.message.reply_text(
                f"❌ {error_msg}\n\n"
                f"لطفاً عدد کمتری وارد کنید.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return VAULT_SET_PERCENT

async def show_vault_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تراکنش‌های صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)
        transactions = database.crud.get_vault_transactions(db, vault_id, limit=50)

        if not transactions:
            message = (
                f"💰 **تراکنش‌های صندوق: {vault.name}**\n\n"
                f"❌ هنوز هیچ تراکنشی ثبت نشده است."
            )
        else:
            # محاسبه تعداد کل تراکنش‌ها برای شماره‌گذاری معکوس
            total_count = len(transactions)

            message = (
                f"💰 **تراکنش‌های صندوق: {vault.name}**\n"
                f"💵 موجودی فعلی: ${vault.balance:.2f}\n\n"
                f"📜 **آخرین تراکنش‌ها:**\n\n"
            )

            # نمایش از جدیدترین به قدیمی‌ترین، اما شماره از قدیمی‌ترین شروع می‌شه
            for i, trans in enumerate(transactions[:15], 1):
                # شماره معکوس: قدیمی‌ترین = 1، جدیدترین = total_count
                reverse_number = total_count - i + 1

                trans_type_emoji = "⬆️" if trans.amount > 0 else "⬇️"
                trans_type_text = {
                    "auto_allocation": "تخصیص خودکار",
                    "manual_expense": "ثبت هزینه",
                    "adjustment": "تعدیل",
                    "withdraw_for_distribution": "برداشت از تنخواه",
                    "petty_cash_distribution": "توزیع از تنخواه"
                }.get(trans.transaction_type, "نامشخص")

                # تبدیل تاریخ به شمسی
                import jdatetime
                from datetime import timezone, timedelta

                # تبدیل به timezone ایران (UTC+3:30)
                iran_tz = timezone(timedelta(hours=3, minutes=30))
                trans_time_iran = trans.created_at.astimezone(iran_tz)

                # تبدیل به تاریخ شمسی
                jalali_date = jdatetime.datetime.fromtimestamp(trans_time_iran.timestamp())
                date_str = jalali_date.strftime('%Y/%m/%d - %H:%M')

                message += (
                    f"**#{reverse_number}** - {trans_type_emoji} ${abs(trans.amount):.2f}\n"
                    f"   📝 {trans_type_text}\n"
                    f"   💬 {trans.description[:50]}{'...' if len(trans.description) > 50 else ''}\n"
                    f"   📅 {date_str}\n\n"
                )

            if len(transactions) > 15:
                message += f"\n📋 و {len(transactions) - 15} تراکنش دیگر..."

        keyboard = get_vault_transactions_keyboard(vault_id)
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def start_rename_vault(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تغییر نام صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])
    context.user_data['vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        # جلوگیری از تغییر نام تنخواه
        if vault.name == "تنخواه گردان":
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ **امکان تغییر نام تنخواه گردان وجود ندارد**\n\n"
                     f"این صندوق سیستمی است و نام آن قابل تغییر نیست.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{vault_id}")
                ]])
            )
            await query.delete_message()
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"✏️ **تغییر نام صندوق**\n\n"
                 f"💰 نام فعلی: {vault.name}\n\n"
                 f"لطفاً نام جدید را وارد کنید:",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return VAULT_RENAME

async def update_vault_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بروزرسانی نام صندوق"""
    new_name = update.message.text.strip()

    if len(new_name) < 2:
        await update.message.reply_text("❌ نام صندوق باید حداقل 2 کاراکتر باشد.")
        return VAULT_RENAME

    vault_id = context.user_data['vault_id']

    with database.connection.SessionLocal() as db:
        vault = database.crud.update_vault_name(db, vault_id, new_name)

        await update.message.reply_text(
            f"✅ **نام صندوق تغییر کرد!**\n\n"
            f"💰 نام جدید: {vault.name}\n"
            f"📅 تاریخ: {get_persian_datetime()}",
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def delete_vault_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تایید حذف صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        if vault.balance != 0:
            await query.edit_message_text(
                f"❌ **امکان حذف صندوق وجود ندارد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"💵 موجودی: ${vault.balance:.2f}\n\n"
                f"برای حذف صندوق، ابتدا موجودی آن باید صفر شود.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{vault_id}")
                ]])
            )
            return

        # تایید حذف
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"vault_delete_confirm_{vault_id}"),
                InlineKeyboardButton("❌ خیر", callback_data=f"vault_detail_{vault_id}")
            ]
        ])

        await query.edit_message_text(
            f"⚠️ **تایید حذف صندوق**\n\n"
            f"💰 صندوق: {vault.name}\n"
            f"📊 درصد تخصیص: {vault.allocation_percentage}%\n\n"
            f"آیا مطمئن هستید که می‌خواهید این صندوق را حذف کنید؟",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def delete_vault_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای حذف صندوق"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[3])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)
        vault_name = vault.name

        database.crud.delete_vault(db, vault_id)

        await query.edit_message_text(
            f"✅ **صندوق حذف شد!**\n\n"
            f"💰 صندوق: {vault_name}\n"
            f"📅 تاریخ: {get_persian_datetime()}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="vault_list")
            ]])
        )


async def cancel_vault_operation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو عملیات"""
    await update.message.reply_text("❌ عملیات لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END


# ==================== ثبت هزینه ====================



async def start_expense_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ثبت هزینه"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        vaults = database.crud.get_all_vaults(db)

        if not vaults:
            await query.edit_message_text(
                f"❌ **امکان ثبت هزینه وجود ندارد!**\n\n"
                f"هیچ صندوقی وجود ندارد. ابتدا یک صندوق ایجاد کنید.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="vault_list")
                ]])
            )
            return ConversationHandler.END

        keyboard = get_expense_vault_selection_keyboard(vaults)

        await query.edit_message_text(
            f"💸 **ثبت هزینه**\n\n"
            f"لطفاً صندوقی که قرار است هزینه از آن برداشت شود را انتخاب کنید:\n"
            f"(صندوق می‌تواند موجودی منفی داشته باشد)",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def get_expense_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ هزینه"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])
    context.user_data['expense_vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"💸 **ثبت هزینه از صندوق {vault.name}**\n\n"
                 f"💰 موجودی فعلی: ${vault.balance:.2f}\n\n"
                 f"لطفاً مبلغ هزینه را وارد کنید:",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return EXPENSE_AMOUNT



async def get_expense_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات هزینه"""
    try:
        amount = float(update.message.text.strip())

        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید عدد مثبتی باشد!")
            return EXPENSE_AMOUNT

        vault_id = context.user_data['expense_vault_id']
        context.user_data['expense_amount'] = amount

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)
            new_balance = vault.balance - amount

            await update.message.reply_text(
                f"📝 **توضیحات هزینه**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"💸 مبلغ: ${amount:.2f}\n"
                f"💵 موجودی فعلی: ${vault.balance:.2f}\n"
                f"💵 موجودی جدید: ${new_balance:.2f}\n\n"
                f"لطفاً توضیحات این هزینه را وارد کنید:\n"
                f"(مثال: خرید فیلامنت، تعمیر دستگاه، هزینه تبلیغات)",
                parse_mode="Markdown"
            )

        return EXPENSE_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return EXPENSE_AMOUNT





async def record_expense_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت نهایی هزینه"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return EXPENSE_DESC

    vault_id = context.user_data['expense_vault_id']
    amount = context.user_data['expense_amount']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transaction = database.crud.record_vault_expense(
                db=db,
                vault_id=vault_id,
                amount=amount,
                description=description,
                admin_id=admin_id
            )

            vault = database.crud.get_vault_by_id(db, vault_id)

            # ایجاد کیبورد بازگشت
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به صندوق", callback_data=f"vault_detail_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **هزینه با موفقیت ثبت شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"💸 مبلغ: ${amount:.2f}\n"
                f"📝 توضیحات: {description}\n"
                f"💵 موجودی جدید: ${vault.balance:.2f}\n"
                f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(
            f"❌ خطا در ثبت هزینه:\n{str(e)}",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END
# ==================== Handler اصلی Callbacks ====================

async def handle_vault_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر اصلی callback های مدیریت صندوق"""
    query = update.callback_query

    if query.data == "vault_list":
        await show_vaults_list(update, context)
    elif query.data.startswith("vault_detail_"):
        await show_vault_detail(update, context)
    elif query.data.startswith("vault_transactions_"):
        await show_vault_transactions(update, context)
    elif query.data.startswith("vault_delete_confirm_"):
        await delete_vault_execute(update, context)
    elif query.data.startswith("vault_delete_"):
        await delete_vault_confirm(update, context)
    elif query.data == "vault_record_expense":
        await start_expense_record(update, context)
    elif query.data.startswith("expense_vault_"):
        await get_expense_amount(update, context)
    else:
        await query.answer("عملیات نامشخص")


# States جدید برای برداشت از تنخواه
PETTY_CASH_WITHDRAW_AMOUNT = 306
PETTY_CASH_WITHDRAW_DESC = 307


async def start_petty_cash_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع برداشت از تنخواه"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        petty_cash = database.crud.ensure_petty_cash_vault(db)

        # بررسی شرایط
        if petty_cash.allocation_percentage != 0:
            await query.edit_message_text(
                f"❌ **امکان برداشت از تنخواه وجود ندارد!**\n\n"
                f"📊 درصد تخصیص تنخواه: {petty_cash.allocation_percentage}%\n\n"
                f"برداشت از تنخواه فقط زمانی مجاز است که تمام 100% به سایر صندوق‌ها تخصیص یافته باشد.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{petty_cash.id}")
                ]])
            )
            return ConversationHandler.END

        if petty_cash.balance <= 0:
            await query.edit_message_text(
                f"❌ **موجودی تنخواه کافی نیست!**\n\n"
                f"💵 موجودی فعلی: ${petty_cash.balance:.2f}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"vault_detail_{petty_cash.id}")
                ]])
            )
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"💸 **برداشت از تنخواه و توزیع بین صندوق‌ها**\n\n"
                 f"💰 موجودی تنخواه: ${petty_cash.balance:.2f}\n\n"
                 f"لطفاً مبلغ مورد نظر برای برداشت و توزیع را وارد کنید:",
            parse_mode="Markdown"
        )

        await query.delete_message()
        return PETTY_CASH_WITHDRAW_AMOUNT


async def get_petty_cash_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ برداشت از تنخواه"""
    try:
        amount = float(update.message.text.strip())

        if amount <= 0:
            await update.message.reply_text("❌ مبلغ باید عدد مثبتی باشد!")
            return PETTY_CASH_WITHDRAW_AMOUNT

        with database.connection.SessionLocal() as db:
            petty_cash = database.crud.ensure_petty_cash_vault(db)

            if amount > petty_cash.balance:
                await update.message.reply_text(
                    f"❌ **موجودی تنخواه کافی نیست!**\n\n"
                    f"💵 موجودی فعلی: ${petty_cash.balance:.2f}\n"
                    f"💸 مبلغ درخواستی: ${amount:.2f}\n\n"
                    f"لطفاً مبلغ کمتری وارد کنید.",
                    parse_mode="Markdown"
                )
                return PETTY_CASH_WITHDRAW_AMOUNT

            # نمایش توزیع پیش‌بینی شده
            other_vaults = db.query(database.models.Vault).filter(
                database.models.Vault.is_active == True,
                database.models.Vault.id != petty_cash.id
            ).all()

            total_percentage = sum(v.allocation_percentage for v in other_vaults)

            distribution_text = "📊 **توزیع پیش‌بینی شده:**\n"
            for vault in other_vaults:
                if vault.allocation_percentage > 0:
                    allocated = (amount * vault.allocation_percentage) / total_percentage
                    distribution_text += f"• {vault.name}: ${allocated:.2f}\n"

            context.user_data['petty_cash_amount'] = amount

            await update.message.reply_text(
                f"💸 **تایید برداشت از تنخواه**\n\n"
                f"💰 مبلغ برداشت: ${amount:.2f}\n"
                f"💵 موجودی باقیمانده تنخواه: ${petty_cash.balance - amount:.2f}\n\n"
                f"{distribution_text}\n"
                f"لطفاً توضیحات این عملیات را وارد کنید:",
                parse_mode="Markdown"
            )

        return PETTY_CASH_WITHDRAW_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return PETTY_CASH_WITHDRAW_AMOUNT


async def execute_petty_cash_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای برداشت از تنخواه"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return PETTY_CASH_WITHDRAW_DESC

    amount = context.user_data['petty_cash_amount']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transactions = database.crud.withdraw_from_petty_cash(
                db=db,
                amount=amount,
                description=description,
                admin_id=admin_id
            )

            petty_cash = database.crud.ensure_petty_cash_vault(db)

            # متن نتیجه
            result_text = f"✅ **برداشت از تنخواه با موفقیت انجام شد!**\n\n"
            result_text += f"💸 مبلغ برداشت شده: ${amount:.2f}\n"
            result_text += f"💵 موجودی جدید تنخواه: ${petty_cash.balance:.2f}\n"
            result_text += f"📝 توضیحات: {description}\n\n"
            result_text += f"💼 **توزیع انجام شده:**\n"

            for trans in transactions:
                vault = database.crud.get_vault_by_id(db, trans.vault_id)
                result_text += f"• {vault.name}: ${trans.amount:.2f}\n"

            result_text += f"\n📅 تاریخ: {get_persian_datetime()}"

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به تنخواه", callback_data=f"vault_detail_{petty_cash.id}")
            ]])

            await update.message.reply_text(
                result_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(
            f"❌ خطا در برداشت از تنخواه:\n{str(e)}",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END


# ==================== مدیریت دارایی طلا ====================

async def show_gold_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی مدیریت طلا"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        if not vault:
            await query.edit_message_text("❌ صندوق یافت نشد.")
            return

        # دریافت خلاصه اطلاعات طلا
        gold_summary = database.crud.get_vault_gold_summary(db, vault_id)

        message = (
            f"💎 **مدیریت دارایی طلای صندوق: {vault.name}**\n\n"
            f"💰 **موجودی نقد:** ${vault.balance:.2f}\n"
            f"🥇 **موجودی طلا:** {vault.gold_balance:.3f} گرم\n\n"
        )

        if gold_summary['current_balance_grams'] > 0:
            message += (
                f"📊 **آمار:**\n"
                f"• کل خرید: {gold_summary['total_bought']:.3f} گرم\n"
                f"• کل فروش: {gold_summary['total_sold']:.3f} گرم\n"
                f"• میانگین قیمت خرید: ${gold_summary['avg_buy_price']:.2f}/گرم\n"
                f"• تعداد معاملات: {gold_summary['transaction_count']}\n\n"
            )

        message += "💡 لطفاً عملیات مورد نظر را انتخاب کنید:"

        from keyboards.vault_management import get_gold_menu_keyboard
        keyboard = get_gold_menu_keyboard(vault_id)

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def show_gold_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش موجودی و آمار طلا با قیمت فعلی"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)
        gold_summary = database.crud.get_vault_gold_summary(db, vault_id)

        if vault.gold_balance <= 0:
            message = (
                f"📊 **موجودی و آمار طلا: {vault.name}**\n\n"
                f"🥇 موجودی طلا: 0 گرم\n"
                f"💰 موجودی نقد: ${vault.balance:.2f}\n\n"
                f"❌ هنوز طلایی خریداری نشده است."
            )
        else:
            message = (
                f"📊 **موجودی و آمار طلا: {vault.name}**\n\n"
                f"💰 **موجودی نقد:** ${vault.balance:.2f}\n"
                f"🥇 **موجودی طلا:** {vault.gold_balance:.3f} گرم\n\n"
                f"📈 **آمار معاملات:**\n"
                f"• کل خرید: {gold_summary['total_bought']:.3f} گرم\n"
                f"• کل فروش: {gold_summary['total_sold']:.3f} گرم\n"
                f"• هزینه خرید: ${gold_summary['total_buy_cost']:.2f}\n"
                f"• درآمد فروش: ${gold_summary['total_sell_revenue']:.2f}\n"
                f"• میانگین قیمت خرید: ${gold_summary['avg_buy_price']:.2f}/گرم\n"
                f"• تعداد معاملات: {gold_summary['transaction_count']}\n\n"
                f"💡 برای محاسبه سود/زیان فعلی، قیمت روز طلا را وارد کنید."
            )

        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 بازگشت به منوی طلا", callback_data=f"gold_menu_{vault_id}")
        ]])

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def start_buy_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند خرید طلا"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])
    context.user_data['gold_vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🛒 **خرید طلا برای صندوق {vault.name}**\n\n"
                 f"💰 موجودی نقد فعلی: ${vault.balance:.2f}\n"
                 f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n\n"
                 f"لطفاً وزن طلای مورد نظر را به گرم وارد کنید:\n"
                 f"(مثال: 2.5 یا 10)",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return GOLD_BUY_WEIGHT



async def get_gold_buy_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت وزن طلا برای خرید"""
    try:
        weight = float(update.message.text.strip())

        if weight <= 0:
            await update.message.reply_text("❌ وزن باید عدد مثبتی باشد!")
            return GOLD_BUY_WEIGHT

        context.user_data['gold_weight'] = weight

        await update.message.reply_text(
            f"💴 **قیمت طلا به تومان**\n\n"
            f"🥇 وزن: {weight} گرم\n\n"
            f"لطفاً قیمت هر گرم طلا را به تومان وارد کنید:\n"
            f"(مثال: 4500000 یعنی 4 میلیون و 500 هزار تومان)",
            parse_mode="Markdown"
        )

        return GOLD_BUY_PRICE_TOMAN

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_BUY_WEIGHT

async def get_gold_buy_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت دلاری طلا"""
    try:
        price_dollar = float(update.message.text.strip())

        if price_dollar <= 0:
            await update.message.reply_text("❌ قیمت باید عدد مثبتی باشد!")
            return GOLD_BUY_PRICE_DOLLAR

        context.user_data['gold_price_dollar'] = price_dollar

        weight = context.user_data['gold_weight']

        await update.message.reply_text(
            f"💴 **قیمت تومانی طلا**\n\n"
            f"وزن: {weight} گرم\n"
            f"قیمت دلاری: ${price_dollar:.2f}/گرم\n\n"
            f"لطفاً قیمت هر گرم طلا را به تومان وارد کنید:\n"
            f"(برای ثبت در سیستم - اختیاری، اگر ندارید 0 بزنید)",
            parse_mode="Markdown"
        )

        return GOLD_BUY_PRICE_TOMAN

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_BUY_PRICE_DOLLAR



async def get_gold_buy_price_toman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت تومانی طلا"""
    try:
        price_toman = float(update.message.text.strip())

        if price_toman <= 0:
            await update.message.reply_text("❌ قیمت باید عدد مثبتی باشد!")
            return GOLD_BUY_PRICE_TOMAN

        context.user_data['gold_price_toman'] = price_toman
        weight = context.user_data['gold_weight']
        total_toman = weight * price_toman

        await update.message.reply_text(
            f"💵 **نرخ تبدیل دلار**\n\n"
            f"🥇 وزن: {weight} گرم\n"
            f"💴 قیمت هر گرم: {price_toman:,.0f} تومان\n"
            f"💴 جمع کل: {total_toman:,.0f} تومان\n\n"
            f"لطفاً نرخ تبدیل دلار به تومان را وارد کنید:\n"
            f"(مثال: 70000 یعنی هر دلار 70 هزار تومان)",
            parse_mode="Markdown"
        )

        return GOLD_BUY_EXCHANGE_RATE

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_BUY_PRICE_TOMAN

async def execute_gold_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای خرید طلا"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return GOLD_BUY_DESC

    vault_id = context.user_data['gold_vault_id']
    weight = context.user_data['gold_weight']
    price_dollar = context.user_data['gold_price_dollar']
    price_toman = context.user_data.get('gold_price_toman')
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transaction = database.crud.buy_gold_for_vault(
                db=db,
                vault_id=vault_id,
                gold_weight=weight,
                price_per_gram_dollar=price_dollar,
                price_per_gram_toman=price_toman,
                description=description,
                admin_id=admin_id
            )

            vault = database.crud.get_vault_by_id(db, vault_id)

            toman_text = f"💴 قیمت تومانی: {price_toman:,.0f} تومان/گرم\n" if price_toman else ""

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به منوی طلا", callback_data=f"gold_menu_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **خرید طلا با موفقیت انجام شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"🥇 وزن خریداری شده: {weight} گرم\n"
                f"💵 قیمت دلاری: ${price_dollar:.2f}/گرم\n"
                f"{toman_text}"
                f"💸 مبلغ پرداختی: ${transaction.total_amount:.2f}\n"
                f"📝 توضیحات: {description}\n\n"
                f"💼 موجودی نقد جدید: ${vault.balance:.2f}\n"
                f"🥇 موجودی طلا جدید: {vault.gold_balance:.3f} گرم\n"
                f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(
            f"❌ خطا در خرید طلا:\n{str(e)}",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

# ==================== فروش طلا ====================








async def start_sell_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند فروش طلا"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])
    context.user_data['gold_vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        if vault.gold_balance <= 0:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"❌ **موجودی طلا کافی نیست!**\n\n"
                     f"🥇 موجودی طلا: {vault.gold_balance:.3f} گرم",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data=f"gold_menu_{vault_id}")
                ]])
            )
            await query.delete_message()
            return ConversationHandler.END

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"💰 **فروش طلا از صندوق {vault.name}**\n\n"
                 f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n"
                 f"💰 موجودی نقد فعلی: ${vault.balance:.2f}\n\n"
                 f"لطفاً وزن طلای مورد نظر برای فروش را به گرم وارد کنید:\n"
                 f"(حداکثر: {vault.gold_balance:.3f} گرم)",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return GOLD_SELL_WEIGHT


async def get_gold_sell_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت وزن طلا برای فروش"""
    try:
        weight = float(update.message.text.strip())

        if weight <= 0:
            await update.message.reply_text("❌ وزن باید عدد مثبتی باشد!")
            return GOLD_SELL_WEIGHT

        vault_id = context.user_data['gold_vault_id']

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)

            if weight > vault.gold_balance:
                await update.message.reply_text(
                    f"❌ **موجودی طلا کافی نیست!**\n\n"
                    f"🥇 موجودی فعلی: {vault.gold_balance:.3f} گرم\n"
                    f"📊 وزن درخواستی: {weight} گرم\n\n"
                    f"لطفاً وزن کمتری وارد کنید.",
                    parse_mode="Markdown"
                )
                return GOLD_SELL_WEIGHT

        context.user_data['gold_weight'] = weight

        await update.message.reply_text(
            f"💴 **قیمت فروش به تومان**\n\n"
            f"🥇 وزن: {weight} گرم\n\n"
            f"لطفاً قیمت فروش هر گرم طلا را به تومان وارد کنید:\n"
            f"(مثال: 4500000)",
            parse_mode="Markdown"
        )

        return GOLD_SELL_PRICE_TOMAN

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_WEIGHT


async def get_gold_sell_price_toman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت تومانی فروش طلا"""
    try:
        price_toman = float(update.message.text.strip())

        if price_toman <= 0:
            await update.message.reply_text("❌ قیمت باید عدد مثبتی باشد!")
            return GOLD_SELL_PRICE_TOMAN

        context.user_data['gold_price_toman'] = price_toman
        weight = context.user_data['gold_weight']
        total_toman = weight * price_toman

        await update.message.reply_text(
            f"💵 **نرخ تبدیل دلار**\n\n"
            f"🥇 وزن: {weight} گرم\n"
            f"💴 قیمت فروش هر گرم: {price_toman:,.0f} تومان\n"
            f"💴 جمع کل: {total_toman:,.0f} تومان\n\n"
            f"لطفاً نرخ تبدیل دلار به تومان را وارد کنید:\n"
            f"(مثال: 70000)",
            parse_mode="Markdown"
        )

        return GOLD_SELL_EXCHANGE_RATE

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_PRICE_TOMAN


async def get_gold_sell_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نرخ تبدیل دلار برای فروش"""
    try:
        exchange_rate = float(update.message.text.strip())

        if exchange_rate <= 0:
            await update.message.reply_text("❌ نرخ تبدیل باید عدد مثبتی باشد!")
            return GOLD_SELL_EXCHANGE_RATE

        weight = context.user_data['gold_weight']
        price_toman = context.user_data['gold_price_toman']
        vault_id = context.user_data['gold_vault_id']

        # محاسبات
        total_toman = weight * price_toman
        price_per_gram_dollar = price_toman / exchange_rate
        total_dollar = total_toman / exchange_rate

        context.user_data['exchange_rate'] = exchange_rate
        context.user_data['price_per_gram_dollar'] = price_per_gram_dollar
        context.user_data['total_dollar'] = total_dollar

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)
            gold_summary = database.crud.get_vault_gold_summary(db, vault_id)

            # محاسبه سود/زیان
            avg_buy_price = gold_summary['avg_buy_price']
            profit_loss = (price_per_gram_dollar - avg_buy_price) * weight if avg_buy_price > 0 else 0
            profit_loss_text = f"📈 سود: ${profit_loss:.2f}" if profit_loss > 0 else f"📉 زیان: ${abs(profit_loss):.2f}" if profit_loss < 0 else "⚖️ بدون سود/زیان"

            await update.message.reply_text(
                f"✅ **تایید فروش طلا**\n\n"
                f"💰 صندوق: {vault.name}\n\n"
                f"📊 **جزئیات معامله:**\n"
                f"🥇 وزن: {weight} گرم\n"
                f"💴 قیمت فروش هر گرم: {price_toman:,.0f} تومان\n"
                f"💴 جمع به تومان: {total_toman:,.0f} تومان\n\n"
                f"💱 نرخ تبدیل: {exchange_rate:,.0f} تومان/دلار\n"
                f"💵 قیمت هر گرم به دلار: ${price_per_gram_dollar:.2f}\n"
                f"💸 مبلغ دریافتی به دلار: ${total_dollar:.2f}\n\n"
                f"💼 میانگین قیمت خرید: ${avg_buy_price:.2f}/گرم\n"
                f"{profit_loss_text}\n\n"
                f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n"
                f"🥇 موجودی طلا بعد: {vault.gold_balance - weight:.3f} گرم\n\n"
                f"💼 موجودی نقد فعلی: ${vault.balance:.2f}\n"
                f"💼 موجودی نقد بعد: ${vault.balance + total_dollar:.2f}\n\n"
                f"لطفاً توضیحات این معامله را وارد کنید:",
                parse_mode="Markdown"
            )

        return GOLD_SELL_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_EXCHANGE_RATE


async def execute_gold_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای فروش طلا"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return GOLD_SELL_DESC

    vault_id = context.user_data['gold_vault_id']
    weight = context.user_data['gold_weight']
    price_toman = context.user_data['gold_price_toman']
    price_dollar = context.user_data['price_per_gram_dollar']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transaction = database.crud.sell_gold_from_vault(
                db=db,
                vault_id=vault_id,
                gold_weight=weight,
                price_per_gram_dollar=price_dollar,
                price_per_gram_toman=price_toman,
                description=description,
                admin_id=admin_id
            )

            vault = database.crud.get_vault_by_id(db, vault_id)

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به منوی طلا", callback_data=f"gold_menu_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **فروش طلا با موفقیت انجام شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"🥇 وزن: {weight} گرم\n"
                f"💴 قیمت: {price_toman:,.0f} تومان/گرم\n"
                f"💵 قیمت: ${price_dollar:.2f}/گرم\n"
                f"💸 مبلغ: ${transaction.total_amount:.2f}\n"
                f"📝 توضیحات: {description}\n\n"
                f"🥇 موجودی طلا جدید: {vault.gold_balance:.3f} گرم\n"
                f"💼 موجودی نقد جدید: ${vault.balance:.2f}\n"
                f"📅 {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}", parse_mode="Markdown")
        context.user_data.clear()
        return ConversationHandler.END










async def get_gold_sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت فروش طلا"""
    try:
        price = float(update.message.text.strip())

        if price <= 0:
            await update.message.reply_text("❌ قیمت باید عدد مثبتی باشد!")
            return GOLD_SELL_PRICE

        weight = context.user_data['gold_weight']
        total = weight * price
        vault_id = context.user_data['gold_vault_id']

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)
            gold_summary = database.crud.get_vault_gold_summary(db, vault_id)

            # محاسبه سود/زیان احتمالی
            avg_buy_price = gold_summary['avg_buy_price']
            profit_loss = (price - avg_buy_price) * weight if avg_buy_price > 0 else 0
            profit_loss_text = f"📈 سود: ${profit_loss:.2f}" if profit_loss > 0 else f"📉 زیان: ${abs(profit_loss):.2f}" if profit_loss < 0 else "⚖️ بدون سود/زیان"

        context.user_data['gold_price'] = price

        await update.message.reply_text(
            f"✅ **تایید فروش طلا**\n\n"
            f"💰 صندوق: {vault.name}\n"
            f"🥇 وزن: {weight} گرم\n"
            f"💵 قیمت فروش هر گرم: ${price:.2f}\n"
            f"💸 مبلغ دریافتی: ${total:.2f}\n\n"
            f"💼 میانگین قیمت خرید: ${avg_buy_price:.2f}/گرم\n"
            f"{profit_loss_text}\n\n"
            f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n"
            f"🥇 موجودی طلا بعد از فروش: {vault.gold_balance - weight:.3f} گرم\n\n"
            f"💼 موجودی نقد فعلی: ${vault.balance:.2f}\n"
            f"💼 موجودی نقد بعد از فروش: ${vault.balance + total:.2f}\n\n"
            f"لطفاً توضیحات این معامله را وارد کنید:",
            parse_mode="Markdown"
        )

        return GOLD_SELL_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_PRICE

async def execute_gold_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای فروش طلا"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return GOLD_SELL_DESC

    vault_id = context.user_data['gold_vault_id']
    weight = context.user_data['gold_weight']
    price_dollar = context.user_data['gold_price_dollar']
    price_toman = context.user_data.get('gold_price_toman')
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transaction = database.crud.sell_gold_from_vault(
                db=db,
                vault_id=vault_id,
                gold_weight=weight,
                price_per_gram_dollar=price_dollar,
                price_per_gram_toman=price_toman,
                description=description,
                admin_id=admin_id
            )

            vault = database.crud.get_vault_by_id(db, vault_id)

            toman_text = f"💴 قیمت تومانی: {price_toman:,.0f} تومان/گرم\n" if price_toman else ""

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به منوی طلا", callback_data=f"gold_menu_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **فروش طلا با موفقیت انجام شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"🥇 وزن فروخته شده: {weight} گرم\n"
                f"💵 قیمت دلاری: ${price_dollar:.2f}/گرم\n"
                f"{toman_text}"
                f"💸 مبلغ دریافتی: ${transaction.total_amount:.2f}\n"
                f"📝 توضیحات: {description}\n\n"
                f"🥇 موجودی طلا جدید: {vault.gold_balance:.3f} گرم\n"
                f"💼 موجودی نقد جدید: ${vault.balance:.2f}\n"
                f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(
            f"❌ خطا در فروش طلا:\n{str(e)}",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END

# ==================== تاریخچه معاملات طلا ====================

async def show_gold_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تاریخچه معاملات طلا"""
    query = update.callback_query
    await query.answer()

    # اصلاح parsing - باید index صحیح رو استفاده کنه
    parts = query.data.split("_")
    # gold_history_123 -> ['gold', 'history', '123']
    vault_id = int(parts[2])

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)
        transactions = database.crud.get_vault_gold_transactions(db, vault_id, limit=50)

        if not transactions:
            message = (
                f"💎 **تاریخچه معاملات طلا: {vault.name}**\n\n"
                f"❌ هنوز هیچ معامله‌ای ثبت نشده است."
            )
        else:
            total_count = len(transactions)

            message = (
                f"💎 **تاریخچه معاملات طلا: {vault.name}**\n"
                f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n\n"
                f"📜 **آخرین معاملات:**\n\n"
            )

            for i, trans in enumerate(transactions[:15], 1):
                reverse_number = total_count - i + 1

                trans_emoji = "🛒" if trans.transaction_type == "buy" else "💰"
                trans_text = "خرید" if trans.transaction_type == "buy" else "فروش"

                # تبدیل تاریخ به شمسی
                import jdatetime
                from datetime import timezone, timedelta

                iran_tz = timezone(timedelta(hours=3, minutes=30))
                trans_time_iran = trans.created_at.astimezone(iran_tz)
                jalali_date = jdatetime.datetime.fromtimestamp(trans_time_iran.timestamp())
                date_str = jalali_date.strftime('%Y/%m/%d - %H:%M')

                # نمایش قیمت تومانی اگر وجود داشته باشه
                toman_text = f"💴 {trans.price_per_gram_toman:,.0f} تومان/گرم\n" if trans.price_per_gram_toman else ""

                message += (
                    f"**#{reverse_number}** - {trans_emoji} {trans_text}\n"
                    f"   🥇 وزن: {trans.gold_weight_grams:.3f} گرم\n"
                    f"   💵 ${trans.price_per_gram_dollar:.2f}/گرم\n"
                    f"   {toman_text}"
                    f"   💸 مبلغ: ${trans.total_amount:.2f}\n"
                    f"   💬 {trans.description[:40]}{'...' if len(trans.description) > 40 else ''}\n"
                    f"   📅 {date_str}\n\n"
                )

            if len(transactions) > 15:
                message += f"\n📋 و {len(transactions) - 15} معامله دیگر..."

        from keyboards.vault_management import get_gold_history_keyboard
        keyboard = get_gold_history_keyboard(vault_id)

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def get_gold_sell_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت دلاری فروش طلا"""
    try:
        price_dollar = float(update.message.text.strip())

        if price_dollar <= 0:
            await update.message.reply_text("❌ قیمت باید عدد مثبتی باشد!")
            return GOLD_SELL_PRICE_DOLLAR

        context.user_data['gold_price_dollar'] = price_dollar

        weight = context.user_data['gold_weight']

        await update.message.reply_text(
            f"💴 **قیمت تومانی فروش**\n\n"
            f"وزن: {weight} گرم\n"
            f"قیمت دلاری: ${price_dollar:.2f}/گرم\n\n"
            f"لطفاً قیمت فروش هر گرم طلا را به تومان وارد کنید:\n"
            f"(برای ثبت در سیستم - اختیاری، اگر ندارید 0 بزنید)",
            parse_mode="Markdown"
        )

        return GOLD_SELL_PRICE_TOMAN

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_PRICE_DOLLAR

async def get_gold_sell_price_toman(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت تومانی فروش طلا"""
    try:
        price_toman = float(update.message.text.strip())

        if price_toman < 0:
            await update.message.reply_text("❌ قیمت نمی‌تواند منفی باشد!")
            return GOLD_SELL_PRICE_TOMAN

        context.user_data['gold_price_toman'] = price_toman if price_toman > 0 else None

        weight = context.user_data['gold_weight']
        price_dollar = context.user_data['gold_price_dollar']
        total = weight * price_dollar
        vault_id = context.user_data['gold_vault_id']

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)
            gold_summary = database.crud.get_vault_gold_summary(db, vault_id)

            # محاسبه سود/زیان احتمالی
            avg_buy_price = gold_summary['avg_buy_price']
            profit_loss = (price_dollar - avg_buy_price) * weight if avg_buy_price > 0 else 0
            profit_loss_text = f"📈 سود: ${profit_loss:.2f}" if profit_loss > 0 else f"📉 زیان: ${abs(profit_loss):.2f}" if profit_loss < 0 else "⚖️ بدون سود/زیان"

            toman_text = f"💴 قیمت تومانی: {price_toman:,.0f} تومان/گرم\n" if price_toman > 0 else ""

        await update.message.reply_text(
            f"✅ **تایید فروش طلا**\n\n"
            f"💰 صندوق: {vault.name}\n"
            f"🥇 وزن: {weight} گرم\n"
            f"💵 قیمت دلاری: ${price_dollar:.2f}/گرم\n"
            f"{toman_text}"
            f"💸 مبلغ دریافتی: ${total:.2f}\n\n"
            f"💼 میانگین قیمت خرید: ${avg_buy_price:.2f}/گرم\n"
            f"{profit_loss_text}\n\n"
            f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n"
            f"🥇 موجودی طلا بعد از فروش: {vault.gold_balance - weight:.3f} گرم\n\n"
            f"💼 موجودی نقد فعلی: ${vault.balance:.2f}\n"
            f"💼 موجودی نقد بعد از فروش: ${vault.balance + total:.2f}\n\n"
            f"لطفاً توضیحات این معامله را وارد کنید:",
            parse_mode="Markdown"
        )

        return GOLD_SELL_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_SELL_PRICE_TOMAN

async def start_buy_gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند خرید طلا"""
    query = update.callback_query
    await query.answer()

    vault_id = int(query.data.split("_")[2])
    context.user_data['gold_vault_id'] = vault_id

    with database.connection.SessionLocal() as db:
        vault = database.crud.get_vault_by_id(db, vault_id)

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"🛒 **خرید طلا برای صندوق {vault.name}**\n\n"
                 f"💰 موجودی نقد فعلی: ${vault.balance:.2f}\n"
                 f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n\n"
                 f"لطفاً وزن طلای مورد نظر را به گرم وارد کنید:\n"
                 f"(مثال: 2.5 یا 10)",
            parse_mode="Markdown"
        )

        await query.delete_message()

    return GOLD_BUY_WEIGHT


async def get_gold_buy_exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نرخ تبدیل دلار"""
    try:
        exchange_rate = float(update.message.text.strip())

        if exchange_rate <= 0:
            await update.message.reply_text("❌ نرخ تبدیل باید عدد مثبتی باشد!")
            return GOLD_BUY_EXCHANGE_RATE

        weight = context.user_data['gold_weight']
        price_toman = context.user_data['gold_price_toman']
        vault_id = context.user_data['gold_vault_id']

        # محاسبات
        total_toman = weight * price_toman
        price_per_gram_dollar = price_toman / exchange_rate
        total_dollar = total_toman / exchange_rate

        context.user_data['exchange_rate'] = exchange_rate
        context.user_data['price_per_gram_dollar'] = price_per_gram_dollar
        context.user_data['total_dollar'] = total_dollar

        with database.connection.SessionLocal() as db:
            vault = database.crud.get_vault_by_id(db, vault_id)

            await update.message.reply_text(
                f"✅ **تایید خرید طلا**\n\n"
                f"💰 صندوق: {vault.name}\n\n"
                f"📊 **جزئیات معامله:**\n"
                f"🥇 وزن: {weight} گرم\n"
                f"💴 قیمت هر گرم: {price_toman:,.0f} تومان\n"
                f"💴 جمع به تومان: {total_toman:,.0f} تومان\n\n"
                f"💱 نرخ تبدیل: {exchange_rate:,.0f} تومان/دلار\n"
                f"💵 قیمت هر گرم به دلار: ${price_per_gram_dollar:.2f}\n"
                f"💸 مبلغ کل به دلار: ${total_dollar:.2f}\n\n"
                f"💼 موجودی نقد فعلی: ${vault.balance:.2f}\n"
                f"💼 موجودی نقد بعد از خرید: ${vault.balance - total_dollar:.2f}\n\n"
                f"🥇 موجودی طلا فعلی: {vault.gold_balance:.3f} گرم\n"
                f"🥇 موجودی طلا بعد از خرید: {vault.gold_balance + weight:.3f} گرم\n\n"
                f"لطفاً توضیحات این معامله را وارد کنید:\n"
                f"(مثال: خرید از طلافروشی، سرمایه‌گذاری)",
                parse_mode="Markdown"
            )

        return GOLD_BUY_DESC

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GOLD_BUY_EXCHANGE_RATE

async def execute_gold_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اجرای خرید طلا"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text("❌ توضیحات باید حداقل 3 کاراکتر باشد.")
        return GOLD_BUY_DESC

    vault_id = context.user_data['gold_vault_id']
    weight = context.user_data['gold_weight']
    price_toman = context.user_data['gold_price_toman']
    price_dollar = context.user_data['price_per_gram_dollar']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            transaction = database.crud.buy_gold_for_vault(
                db=db,
                vault_id=vault_id,
                gold_weight=weight,
                price_per_gram_dollar=price_dollar,
                price_per_gram_toman=price_toman,
                description=description,
                admin_id=admin_id
            )

            vault = database.crud.get_vault_by_id(db, vault_id)

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت به منوی طلا", callback_data=f"gold_menu_{vault_id}")
            ]])

            await update.message.reply_text(
                f"✅ **خرید طلا با موفقیت انجام شد!**\n\n"
                f"💰 صندوق: {vault.name}\n"
                f"🥇 وزن: {weight} گرم\n"
                f"💴 قیمت: {price_toman:,.0f} تومان/گرم\n"
                f"💵 قیمت: ${price_dollar:.2f}/گرم\n"
                f"💸 مبلغ: ${transaction.total_amount:.2f}\n"
                f"📝 توضیحات: {description}\n\n"
                f"💼 موجودی نقد جدید: ${vault.balance:.2f}\n"
                f"🥇 موجودی طلا جدید: {vault.gold_balance:.3f} گرم\n"
                f"📅 {get_persian_datetime()}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

        context.user_data.clear()
        return ConversationHandler.END

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}", parse_mode="Markdown")
        context.user_data.clear()
        return ConversationHandler.END