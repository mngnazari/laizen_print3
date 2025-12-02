# handlers/test_wallet.py
from telegram import Update
from telegram.ext import ContextTypes
from keyboards.customer import get_customer_kb


async def test_wallet_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تابع تست ساده برای کیف پول"""
    user_id = update.effective_user.id

    message = (
        "🧪 **تست کیف پول**\n\n"
        "اگر این پیام را می‌بینید، یعنی:\n"
        "✅ فایل handlers/test_wallet.py کار می‌کند\n"
        "✅ Import موفق بوده\n"
        "✅ Handler درست اضافه شده\n\n"
        "حالا می‌توانید فایل اصلی wallet_invoice.py را جایگزین کنید."
    )

    await update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=get_customer_kb(user_id)
    )