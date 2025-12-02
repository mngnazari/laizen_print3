# handlers/receipt_management.py - فایل کامل اصلاح شده

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.receipt_management import get_receipts_list_keyboard, get_receipt_action_keyboard
from utils.referral import get_persian_datetime

# وضعیت‌های conversation
(RECEIPT_CHARGE_AMOUNT, RECEIPT_CHARGE_DESC) = range(200, 202)

ADMIN_ID = 2138687434


async def show_receipts_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
   """نمایش لیست رسیدهای تایید نشده"""
   query = update.callback_query
   await query.answer()

   if query.from_user.id != ADMIN_ID:
       await query.edit_message_text("شما اجازه دسترسی ندارید.")
       return

   with database.connection.SessionLocal() as db:
       receipts = database.crud.get_unconfirmed_receipts(db)

       if not receipts:
           await query.edit_message_text(
               "📄 **رسیدهای دریافتی**\n\n"
               "هیچ رسید تایید نشده‌ای وجود ندارد.",
               parse_mode="Markdown",
               reply_markup=InlineKeyboardMarkup([[
                   InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")
               ]])
           )
           return

       keyboard = get_receipts_list_keyboard(receipts)
       await query.edit_message_text(
           f"📄 **رسیدهای دریافتی** ({len(receipts)} رسید)\n\n"
           "لطفاً رسید مورد نظر را انتخاب کنید:",
           parse_mode="Markdown",
           reply_markup=keyboard
       )


async def show_receipt_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
   """نمایش جزئیات رسید"""
   query = update.callback_query
   await query.answer()

   # تغییر callback parsing - حالا admin_receipt_detail_ است
   receipt_id = int(query.data.split("_")[3])

   with database.connection.SessionLocal() as db:
       receipt = database.crud.get_receipt(db, receipt_id)

       if not receipt:
           await query.edit_message_text("❌ رسید یافت نشد.")
           return

       # حذف amount چون در جدول وجود ندارد
       detail_text = (
           f"📄 **جزئیات رسید**\n\n"
           f"👤 **مشتری:** {receipt.user.full_name}\n"
           f"📱 **شماره:** {receipt.user.phone_number}\n"
           f"📅 **تاریخ ارسال:** {receipt.created_at.strftime('%Y/%m/%d %H:%M')}\n"
           f"📝 **توضیحات:** {receipt.description or 'ندارد'}\n\n"
           f"**موجودی فعلی مشتری:** ${receipt.user.wallet_balance:.2f}"
       )

       keyboard = get_receipt_action_keyboard(receipt_id)
       await query.edit_message_text(
           detail_text,
           parse_mode="Markdown",
           reply_markup=keyboard
       )


async def start_charge_from_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع فرآیند شارژ از روی رسید"""
    query = update.callback_query
    await query.answer()

    receipt_id = int(query.data.split("_")[3])
    context.user_data['receipt_id'] = receipt_id

    with database.connection.SessionLocal() as db:
        receipt = database.crud.get_receipt(db, receipt_id)

        # ارسال پیام جدید به جای edit کردن
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"💰 **شارژ کیف پول از روی رسید**\n\n"
                 f"👤 مشتری: {receipt.user.full_name}\n"
                 f"💳 موجودی فعلی: ${receipt.user.wallet_balance:.2f}\n\n"
                 f"لطفاً مبلغ شارژ را وارد کنید:",
            parse_mode="Markdown"
        )

    return RECEIPT_CHARGE_AMOUNT


async def get_receipt_charge_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
   """دریافت مبلغ شارژ"""
   try:
       amount = float(update.message.text)

       if amount <= 0:
           await update.message.reply_text("❌ مبلغ باید مثبت باشد.")
           return RECEIPT_CHARGE_AMOUNT

       context.user_data['charge_amount'] = amount
       receipt_id = context.user_data['receipt_id']

       with database.connection.SessionLocal() as db:
           receipt = database.crud.get_receipt(db, receipt_id)

           await update.message.reply_text(
               f"💰 **تایید شارژ کیف پول**\n\n"
               f"👤 مشتری: {receipt.user.full_name}\n"
               f"💰 مبلغ شارژ: ${amount:.2f}\n"
               f"💳 موجودی جدید: ${receipt.user.wallet_balance + amount:.2f}\n\n"
               f"لطفاً دلیل شارژ را وارد کنید:",
               parse_mode="Markdown"
           )

       return RECEIPT_CHARGE_DESC

   except ValueError:
       await update.message.reply_text("❌ لطفاً عدد معتبر وارد کنید.")
       return RECEIPT_CHARGE_AMOUNT


async def get_receipt_charge_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات و انجام شارژ با تخصیص به صندوق‌ها"""
    description = update.message.text.strip()

    if not description:
        await update.message.reply_text("❌ لطفاً توضیح را وارد کنید.")
        return RECEIPT_CHARGE_DESC

    receipt_id = context.user_data.get('receipt_id')
    amount = context.user_data.get('charge_amount')
    admin_id = update.effective_user.id

    # DEBUG: چاپ مقادیر
    print(f"DEBUG - receipt_id: {receipt_id}")
    print(f"DEBUG - amount: {amount}")
    print(f"DEBUG - admin_id: {admin_id}")

    if not receipt_id or not amount:
        await update.message.reply_text("❌ خطا: اطلاعات ناقص است. لطفاً دوباره تلاش کنید.")
        context.user_data.clear()
        return ConversationHandler.END

    with database.connection.SessionLocal() as db:
        receipt = database.crud.get_receipt(db, receipt_id)

        if not receipt:
            await update.message.reply_text("❌ رسید یافت نشد.")
            context.user_data.clear()
            return ConversationHandler.END

        # شارژ کیف پول با receipt_id - DEBUG
        print(f"DEBUG - قبل از شارژ: receipt_id={receipt_id}")

        updated_user = database.crud.update_user_wallet_balance(
            db=db,
            user_id=receipt.user_id,
            amount=amount,
            description=description,
            admin_id=admin_id,
            receipt_id=receipt_id
        )

        # تایید رسید
        database.crud.confirm_receipt(db, receipt_id, admin_id)

        # دریافت اطلاعات تخصیص به صندوق‌ها
        vault_allocations = []
        vaults = database.crud.get_all_vaults(db)

        print(f"DEBUG - تعداد صندوق‌ها: {len(vaults)}")

        for vault in vaults:
            print(f"DEBUG - صندوق: {vault.name}, درصد: {vault.allocation_percentage}")
            if vault.allocation_percentage > 0:
                allocated = (amount * vault.allocation_percentage) / 100
                vault_allocations.append(f"• {vault.name}: ${allocated:.2f} ({vault.allocation_percentage}%)")

        allocation_text = "\n".join(vault_allocations) if vault_allocations else "هیچ صندوقی برای تخصیص وجود ندارد"

        await update.message.reply_text(
            f"✅ **شارژ با موفقیت انجام شد!**\n\n"
            f"👤 مشتری: {updated_user.full_name}\n"
            f"💰 مبلغ شارژ: ${amount:.2f}\n"
            f"📝 توضیح: {description}\n"
            f"💳 موجودی جدید: ${updated_user.wallet_balance:.2f}\n\n"
            f"💼 **تخصیص به صندوق‌ها:**\n{allocation_text}\n\n"
            f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
            parse_mode="Markdown"
        )

        # اطلاع‌رسانی به مشتری
        try:
            await context.bot.send_message(
                chat_id=receipt.user_id,
                text=f"✅ **رسید شما تایید شد!**\n\n"
                     f"💰 مبلغ: ${amount:.2f}\n"
                     f"📝 توضیح: {description}\n"
                     f"💳 موجودی جدید: ${updated_user.wallet_balance:.2f}\n"
                     f"📅 تاریخ: {get_persian_datetime()}",
                parse_mode="Markdown"
            )
        except:
            pass

    context.user_data.clear()
    return ConversationHandler.END

async def reject_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
   """رد کردن رسید"""
   query = update.callback_query
   await query.answer()

   # تغییر callback parsing - حالا admin_reject_receipt_ است
   receipt_id = int(query.data.split("_")[3])

   with database.connection.SessionLocal() as db:
       receipt = database.crud.get_receipt(db, receipt_id)
       database.crud.reject_receipt(db, receipt_id, query.from_user.id)

       await query.edit_message_text(
           f"❌ **رسید رد شد**\n\n"
           f"رسید مشتری {receipt.user.full_name} رد شد.",
           parse_mode="Markdown"
       )

       # اطلاع‌رسانی به مشتری
       try:
           await context.bot.send_message(
               chat_id=receipt.user_id,
               text=f"❌ **رسید شما رد شد**\n\n"
                    f"متأسفانه رسید ارسالی شما رد شد.\n"
                    f"لطفاً با پشتیبانی تماس بگیرید.",
               parse_mode="Markdown"
           )
       except:
           pass


async def show_receipt_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات رسید"""
    query = update.callback_query
    await query.answer()

    receipt_id = int(query.data.split("_")[3])

    with database.connection.SessionLocal() as db:
        receipt = database.crud.get_receipt(db, receipt_id)

        if not receipt:
            await query.edit_message_text("❌ رسید یافت نشد.")
            return

        # ارسال عکس رسید
        try:
            caption_text = (
                f"📄 **جزئیات رسید**\n\n"
                f"👤 **مشتری:** {receipt.user.full_name}\n"
                f"📱 **شماره:** {receipt.user.phone_number}\n"
                f"📅 **تاریخ ارسال:** {receipt.created_at.strftime('%Y/%m/%d %H:%M')}\n"
                f"📝 **توضیحات:** {receipt.description or 'ندارد'}\n\n"
                f"**موجودی فعلی مشتری:** ${receipt.user.wallet_balance:.2f}"
            )

            keyboard = get_receipt_action_keyboard(receipt_id)

            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=receipt.file_id,
                caption=caption_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            # حذف پیام قبلی
            await query.delete_message()

        except Exception as e:
            await query.edit_message_text(f"❌ خطا در نمایش رسید: {str(e)}")