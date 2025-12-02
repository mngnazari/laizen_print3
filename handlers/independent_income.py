# handlers/independent_income.py
"""
هندلر ثبت درآمد مستقل (خارج از شارژ حساب مشتریان)
این درآمدها مستقیماً به صندوق‌ها تخصیص می‌یابند
"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from utils.referral import get_persian_datetime

# وضعیت‌های conversation
(INCOME_AMOUNT, INCOME_DESC) = range(400, 402)

ADMIN_ID = 2138687434


async def start_independent_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند ثبت درآمد مستقل"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("شما اجازه دسترسی ندارید.")
        return ConversationHandler.END

    with database.connection.SessionLocal() as db:
        # اطمینان از وجود تنخواه
        database.crud.ensure_petty_cash_vault(db)

        # دریافت لیست صندوق‌ها برای نمایش
        vaults = database.crud.get_all_vaults(db)

        if not vaults:
            await query.edit_message_text(
                "❌ **امکان ثبت درآمد وجود ندارد!**\n\n"
                "هیچ صندوقی وجود ندارد. ابتدا صندوق ایجاد کنید.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_vaults_menu")
                ]])
            )
            return ConversationHandler.END

        # محاسبه درصد تخصیص‌ها
        total_allocated = sum(v.allocation_percentage for v in vaults)

        vault_info = "\n".join([
            f"• {v.name}: {v.allocation_percentage}%"
            for v in sorted(vaults, key=lambda x: x.allocation_percentage, reverse=True)
            if v.allocation_percentage > 0
        ])

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"💰 **ثبت درآمد مستقل**\n\n"
                 f"این درآمد به صورت خودکار بین صندوق‌ها توزیع می‌شود:\n\n"
                 f"{vault_info}\n\n"
                 f"📊 مجموع درصد تخصیص: {total_allocated}%\n\n"
                 f"لطفاً مبلغ درآمد را به دلار وارد کنید:\n"
                 f"(مثال: 100 یا 50.5)",
            parse_mode="Markdown"
        )

        # حذف پیام قبلی
        await query.delete_message()

    return INCOME_AMOUNT


async def get_income_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ درآمد"""
    try:
        amount = float(update.message.text.strip())

        if amount <= 0:
            await update.message.reply_text(
                "❌ مبلغ باید عدد مثبتی باشد!\n"
                "لطفاً دوباره وارد کنید:"
            )
            return INCOME_AMOUNT

        context.user_data['income_amount'] = amount

        with database.connection.SessionLocal() as db:
            vaults = database.crud.get_all_vaults(db)

            # محاسبه توزیع پیش‌بینی شده
            distribution_text = "💼 **توزیع پیش‌بینی شده:**\n"
            for vault in vaults:
                if vault.allocation_percentage > 0:
                    allocated = (amount * vault.allocation_percentage) / 100
                    distribution_text += f"• {vault.name}: ${allocated:.2f} ({vault.allocation_percentage}%)\n"

        await update.message.reply_text(
            f"✅ **تایید ثبت درآمد مستقل**\n\n"
            f"💵 مبلغ کل: ${amount:.2f}\n\n"
            f"{distribution_text}\n"
            f"لطفاً توضیحات این درآمد را وارد کنید:\n"
            f"(مثال: فروش محصول، خدمات مشاوره، درآمد جانبی)",
            parse_mode="Markdown"
        )

        return INCOME_DESC

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک عدد معتبر وارد کنید.\n"
            "مثال: 100 یا 50.5"
        )
        return INCOME_AMOUNT


async def record_independent_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ثبت نهایی درآمد مستقل و تخصیص به صندوق‌ها"""
    description = update.message.text.strip()

    if len(description) < 3:
        await update.message.reply_text(
            "❌ توضیحات باید حداقل 3 کاراکتر باشد.\n"
            "لطفاً توضیح مختصری درباره این درآمد بنویسید:"
        )
        return INCOME_DESC

    amount = context.user_data.get('income_amount')
    admin_id = update.effective_user.id

    if not amount:
        await update.message.reply_text("❌ خطا: مبلغ یافت نشد. لطفاً دوباره تلاش کنید.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        with database.connection.SessionLocal() as db:
            # تخصیص درآمد به صندوق‌ها
            transactions = database.crud.allocate_independent_income_to_vaults(
                db=db,
                income_amount=amount,
                description=description,
                admin_id=admin_id
            )

            if not transactions:
                await update.message.reply_text(
                    "❌ خطا در ثبت درآمد. هیچ صندوقی برای تخصیص یافت نشد.",
                    parse_mode="Markdown"
                )
                context.user_data.clear()
                return ConversationHandler.END

            # ایجاد پیام نتیجه
            allocation_text = "💼 **تخصیص انجام شده:**\n"
            for trans in transactions:
                vault = database.crud.get_vault_by_id(db, trans.vault_id)
                allocation_text += f"• {vault.name}: ${trans.amount:.2f}\n"

            # دریافت مجموع موجودی‌ها
            summary = database.crud.get_vaults_summary(db)

            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("💰 مدیریت صندوق‌ها", callback_data="vault_list"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_vaults_menu")
            ]])

            await update.message.reply_text(
                f"✅ **درآمد مستقل با موفقیت ثبت شد!**\n\n"
                f"💵 مبلغ کل: ${amount:.2f}\n"
                f"📝 توضیحات: {description}\n"
                f"📅 تاریخ: {get_persian_datetime()}\n\n"
                f"{allocation_text}\n"
                f"📊 **آمار کلی:**\n"
                f"💼 مجموع موجودی صندوق‌ها: ${summary['total_balance']:.2f}\n"
                f"🏦 تعداد صندوق‌ها: {summary['total_vaults']}",
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ثبت درآمد:\n{str(e)}\n\n"
            f"لطفاً دوباره تلاش کنید.",
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_independent_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند ثبت درآمد"""
    await update.message.reply_text(
        "❌ ثبت درآمد مستقل لغو شد.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 بازگشت به منوی صندوق‌ها", callback_data="admin_vaults_menu")
        ]])
    )
    context.user_data.clear()
    return ConversationHandler.END