# handlers/group_admin.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, CommandHandler, \
    filters
import database.crud
import database.connection
from utils.group_settings import GroupLevelSettings

# States برای ConversationHandler
SILVER_THRESHOLD, SILVER_DISCOUNT, GOLD_THRESHOLD, GOLD_DISCOUNT = range(4)


async def show_group_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی تنظیمات گروه"""
    query = update.callback_query
    if query:
        await query.answer()

    with database.connection.SessionLocal() as db:
        settings = GroupLevelSettings.get_settings(db)
        message = "⚙️ **تنظیمات سطح‌بندی گروه**\n\n"
        message += "🥉 **برنزی:** پیش‌فرض (بدون تخفیف)\n"
        message += f"🥈 **نقره‌ای:** {settings['silver_threshold']} گرم/روز → {settings['silver_discount']}% تخفیف\n"
        message += f"🥇 **طلایی:** {settings['gold_threshold']} گرم/روز → {settings['gold_discount']}% تخفیف\n\n"
        message += "💡 تخفیف فقط برای دعوت‌کننده اصلی گروه اعمال می‌شود"

        keyboard = [
            [
                InlineKeyboardButton("🥈 تنظیم نقره‌ای", callback_data="admin_group_silver"),
                InlineKeyboardButton("🥇 تنظیم طلایی", callback_data="admin_group_gold")
            ],
            [
                InlineKeyboardButton("📊 آمار گروه‌ها", callback_data="admin_group_stats"),
                InlineKeyboardButton("🔄 بازنشانی", callback_data="admin_group_reset")
            ],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_main")]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        if query:
            await query.edit_message_text(message, parse_mode="Markdown", reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, parse_mode="Markdown", reply_markup=reply_markup)


async def start_silver_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تنظیم سطح نقره‌ای"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        settings = GroupLevelSettings.get_settings(db)

        message = f"🥈 **تنظیم سطح نقره‌ای**\n\n"
        message += f"مقدار فعلی: {settings['silver_threshold']} گرم در روز\n"
        message += f"تخفیف فعلی: {settings['silver_discount']}%\n\n"
        message += "لطفاً حد آستانه جدید را به گرم وارد کنید:"

    await query.edit_message_text(message, parse_mode="Markdown")
    return SILVER_THRESHOLD


async def get_silver_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آستانه نقره‌ای"""
    try:
        threshold = float(update.message.text)
        if threshold <= 0:
            await update.message.reply_text("❌ مقدار باید بزرگتر از صفر باشد. دوباره تلاش کنید:")
            return SILVER_THRESHOLD

        context.user_data['silver_threshold'] = threshold
        await update.message.reply_text(
            f"✅ آستانه نقره‌ای: {threshold} گرم\n\n"
            f"اکنون درصد تخفیف برای سطح نقره‌ای را وارد کنید (0-100):"
        )
        return SILVER_DISCOUNT

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
        return SILVER_THRESHOLD


async def get_silver_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت درصد تخفیف نقره‌ای"""
    try:
        discount = float(update.message.text)
        if not (0 <= discount <= 100):
            await update.message.reply_text("❌ درصد تخفیف باید بین 0 تا 100 باشد. دوباره تلاش کنید:")
            return SILVER_DISCOUNT

        threshold = context.user_data['silver_threshold']

        with database.connection.SessionLocal() as db:
            database.crud.set_system_setting(db, "group_silver_threshold", str(threshold))
            database.crud.set_system_setting(db, "group_silver_discount", str(discount))

        await update.message.reply_text(
            f"✅ **تنظیمات نقره‌ای ذخیره شد!**\n\n"
            f"🥈 آستانه: {threshold} گرم در روز\n"
            f"🎁 تخفیف: {discount}%"
        )

        # نمایش منوی اصلی
        await show_group_settings_menu(update, context)
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
        return SILVER_DISCOUNT


async def start_gold_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تنظیم سطح طلایی"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        settings = GroupLevelSettings.get_settings(db)

        message = f"🥇 **تنظیم سطح طلایی**\n\n"
        message += f"مقدار فعلی: {settings['gold_threshold']} گرم در روز\n"
        message += f"تخفیف فعلی: {settings['gold_discount']}%\n\n"
        message += "لطفاً حد آستانه جدید را به گرم وارد کنید:"

    await query.edit_message_text(message, parse_mode="Markdown")
    return GOLD_THRESHOLD


async def get_gold_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آستانه طلایی"""
    try:
        threshold = float(update.message.text)
        if threshold <= 0:
            await update.message.reply_text("❌ مقدار باید بزرگتر از صفر باشد. دوباره تلاش کنید:")
            return GOLD_THRESHOLD

        context.user_data['gold_threshold'] = threshold
        await update.message.reply_text(
            f"✅ آستانه طلایی: {threshold} گرم\n\n"
            f"اکنون درصد تخفیف برای سطح طلایی را وارد کنید (0-100):"
        )
        return GOLD_DISCOUNT

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
        return GOLD_THRESHOLD


async def get_gold_discount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت درصد تخفیف طلایی"""
    try:
        discount = float(update.message.text)
        if not (0 <= discount <= 100):
            await update.message.reply_text("❌ درصد تخفیف باید بین 0 تا 100 باشد. دوباره تلاش کنید:")
            return GOLD_DISCOUNT

        threshold = context.user_data['gold_threshold']

        with database.connection.SessionLocal() as db:
            database.crud.set_system_setting(db, "group_gold_threshold", str(threshold))
            database.crud.set_system_setting(db, "group_gold_discount", str(discount))

        await update.message.reply_text(
            f"✅ **تنظیمات طلایی ذخیره شد!**\n\n"
            f"🥇 آستانه: {threshold} گرم در روز\n"
            f"🎁 تخفیف: {discount}%"
        )

        # نمایش منوی اصلی
        await show_group_settings_menu(update, context)
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
        return GOLD_DISCOUNT


async def show_group_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کلی گروه‌ها"""
    query = update.callback_query
    await query.answer()

    message = f"📊 **آمار کلی گروه‌ها**\n\n"
    message += "این قسمت در حال توسعه است..."

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_group_settings")]]
    await query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def reset_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازنشانی تنظیمات به مقادیر پیش‌فرض"""
    query = update.callback_query
    await query.answer()

    with database.connection.SessionLocal() as db:
        database.crud.set_system_setting(db, "group_silver_threshold", "50")
        database.crud.set_system_setting(db, "group_gold_threshold", "100")
        database.crud.set_system_setting(db, "group_silver_discount", "5")
        database.crud.set_system_setting(db, "group_gold_discount", "10")

    await query.edit_message_text("✅ تنظیمات به مقادیر پیش‌فرض بازنشانی شد!")
    await show_group_settings_menu(update, context)


async def cancel_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو تنظیمات"""
    await update.message.reply_text("❌ تنظیمات لغو شد.")
    await show_group_settings_menu(update, context)
    return ConversationHandler.END


# ConversationHandler برای تنظیمات نقره‌ای
def get_silver_settings_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_silver_settings, pattern="^admin_group_silver$")],
        states={
            SILVER_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_silver_threshold)],
            SILVER_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_silver_discount)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_group_settings),
            MessageHandler(filters.Regex("^لغو$"), cancel_group_settings)
        ]
    )


# ConversationHandler برای تنظیمات طلایی
def get_gold_settings_conversation():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_gold_settings, pattern="^admin_group_gold$")],
        states={
            GOLD_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_threshold)],
            GOLD_DISCOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_discount)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_group_settings),
            MessageHandler(filters.Regex("^لغو$"), cancel_group_settings)
        ]
    )