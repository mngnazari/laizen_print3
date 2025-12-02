# handlers/admin.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from utils.referral import generate_referral_code, get_persian_datetime

(GET_USER_ID_TO_UPDATE, GET_NEW_REFERRAL_LIMIT) = range(2)



async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    """نام کاربری ربات را از API تلگرام دریافت می‌کند."""
    me = await context.bot.get_me()
    return me.username


async def generate_referral_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای تولید مستقیم کد دعوت و لینک توسط ادمین."""
    print("DEBUG: generate_referral_code_handler called - NEW VERSION")  # این خط رو اضافه کن
    user_id = update.effective_user.id
    """هندلر برای تولید مستقیم کد دعوت و لینک توسط ادمین."""
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name or "ادمین"

    with database.connection.SessionLocal() as db:
        try:
            admin_user = database.crud.add_admin_if_not_exists(
                db,
                user_id=user_id,
                full_name=full_name,
                phone_number=None
            )

            referral_code = generate_referral_code()
            referral = database.crud.create_admin_referral_code(db, admin_id=user_id, code=referral_code)

            bot_username = await get_bot_username(context)
            referral_link = f"https://t.me/{bot_username}?start={referral.referral_code}"

            first_message = (
                f"✅ لینک دعوت تولید شد!\n\n"
                f"🔗 **کد دعوت:** `{referral.referral_code}`\n"
                f"🌐 **لینک دعوت:**\n{referral_link}\n\n"
                f"📋 این لینک را برای معرفی افراد جدید به ربات استفاده کنید."
            )

            await update.effective_message.reply_text(first_message, parse_mode="Markdown")

            second_message = (
                f"📱 **متن زیر را می‌توانید برای معرفی استفاده کنید:**\n\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"سلام 👋\n\n"
                f"من از ربات **کایزنجت** استفاده می‌کنم که محصولی از گروه مهندس نظری هست و برای سهولت ارسال فایل‌ها برای پرینت پروژه طراحی شده.\n\n"
                f"پیشنهاد می‌کنم تو هم همین حالا عضو این بات بشی و از امکانات بی‌نظیر و شگفت‌انگیز اون استفاده کنی! 🎯\n\n"
                f"┏━━━━━━━━━━━━━━━━━━┓\n"
                f"┃   🔥 چرا KaizenJet؟   ┃\n"
                f"┗━━━━━━━━━━━━━━━━━━┛\n\n"
                f"✨ پرینت سه‌بعدی با کیفیت حرفه‌ای\n"
                f"✨ قیمت‌های شفاف و مناسب\n"
                f"✨ تحویل سریع و مطمئن\n"
                f"✨ پشتیبانی 24 ساعته\n"
                f"✨ سیستم گروهی برای تخفیف بیشتر\n"
                f"✨ رابط کاربری ساده و کاربردی\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🎁 عضویت رایگان + اعتبار هدیه\n\n"
                f"🔗 برای شروع روی لینک زیر کلیک کن:\n"
                f"👇👇👇\n"
                f"{referral_link}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📝 نحوه عضویت (فقط 3 مرحله ساده):\n\n"
                f"1️⃣ روی لینک بالا کلیک کنید و استارت بزنید\n\n"
                f"2️⃣ دکمه 📱 \"اشتراک شماره تماس\" را بزنید و شماره خود را ارسال کنید\n\n"
                f"3️⃣ نام و نام خانوادگی خود را به فارسی تایپ و ارسال کنید\n\n"
                f"✅✅ تمام! ✅✅\n\n"
                f"حالا می‌تونی از تمام خدمات استفاده کنی و پروژه‌هات رو راحت پرینت بگیری! 🎨🖨️\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💬 سوالی داری؟\n"
                f"بعد از عضویت، تیم پشتیبانی آماده راهنماییته! 👨‍💼\n\n"
                f"منتظر دیدنت تو ربات هستم! 😊🙌"
            )

            await update.effective_message.reply_text(second_message, parse_mode="Markdown")

        except Exception as e:
            await update.effective_message.reply_text(
                f"❌ متاسفانه خطایی در تولید کد دعوت رخ داد: {e}"
            )


# بقیه توابع بدون تغییر باقی می‌مانند
# فقط تابع generate_referral_code_handler تغییر کرده است

async def view_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای نمایش لیست تمام کاربران ثبت‌نام شده."""
    with database.connection.SessionLocal() as db:
        users = database.crud.get_all_users(db)

        if not users:
            await update.message.reply_text("❌ هنوز هیچ کاربری ثبت‌نام نکرده است.")
            return

        message = "👥 **لیست کاربران ثبت‌نام شده:**\n\n"
        for user in users:
            message += f"**نام:** {user.full_name}\n"
            message += f"**آی‌دی:** `{user.id}`\n"
            message += f"**شماره موبایل:** {user.phone_number}\n"
            message += f"**نقش:** {user.role or 'مشتری'}\n"
            if user.referrer_id:
                message += f"**دعوت‌شده توسط:** `{user.referrer_id}`\n"
            message += f"**تعداد دعوت‌ها:** {user.referrals_count}/{user.max_referrals}\n"
            message += f"**اعتبار:** {int(user.discount_credit)} دلار\n"

            active_codes = database.crud.get_user_referral_codes(db, user.id)
            if active_codes:
                codes_text = ", ".join([code.referral_code for code in active_codes[-2:]])
                message += f"**کدهای فعال:** {codes_text}\n"

            message += "---\n"

        await update.message.reply_text(message, parse_mode="Markdown")


async def show_referral_tree_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای نمایش ساختار درختی دعوت کاربران."""
    with database.connection.SessionLocal() as db:
        users = database.crud.get_all_users(db)

        if not users:
            await update.message.reply_text("❌ هنوز هیچ کاربری ثبت‌نام نکرده است.")
            return

        # ایجاد ساختار درختی با استفاده از دیکشنری
        referral_map = {user.id: [] for user in users}
        user_map = {user.id: user for user in users}
        root_users = []

        for user in users:
            if user.referrer_id and user.referrer_id in referral_map:
                referral_map[user.referrer_id].append(user)
            else:
                # کاربرانی که ارجاع‌دهنده ندارند یا ارجاع‌دهنده‌شان در لیست کاربران نیست، ریشه هستند
                root_users.append(user)

        # تابع بازگشتی برای ساخت رشته نهایی درخت
        def build_tree_string(user_id, indent=""):
            tree_str = ""
            children = referral_map.get(user_id, [])
            for i, child in enumerate(children):
                is_last = (i == len(children) - 1)
                prefix = "└── " if is_last else "├── "
                tree_str += f"{indent}{prefix}**{child.full_name}** (`{child.id}`) - {child.referrals_count}/{child.max_referrals}\n"
                new_indent = indent + ("    " if is_last else "│   ")
                tree_str += build_tree_string(child.id, new_indent)
            return tree_str

        message = "🌳 **ساختار درختی دعوت:**\n\n"
        if root_users:
            for root in root_users:
                message += f"**{root.full_name}** (`{root.id}`) - {root.referrals_count}/{root.max_referrals}\n"
                message += build_tree_string(root.id, "")
        else:
            message += "هیچ ساختار دعوتی برای نمایش وجود ندارد."

        await update.message.reply_text(message, parse_mode="Markdown")


async def set_referral_limit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند تنظیم سقف دعوت برای یک کاربر."""
    await update.message.reply_text(
        "لطفاً آی‌دی کاربری که می‌خواهید سقف دعوت او را تغییر دهید، وارد کنید."
    )
    return GET_USER_ID_TO_UPDATE


async def get_user_id_to_update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت آی‌دی کاربر و درخواست سقف جدید."""
    try:
        user_id = int(update.message.text)

        with database.connection.SessionLocal() as db:
            user = database.crud.get_user(db, user_id)
            if not user:
                await update.message.reply_text(
                    "❌ کاربری با این آی‌دی یافت نشد. لطفاً آی‌دی صحیح را وارد کنید یا /cancel را برای لغو بزنید."
                )
                return GET_USER_ID_TO_UPDATE

        context.user_data['user_to_update_id'] = user_id
        await update.message.reply_text(
            f"✅ کاربر یافت شد: {user.full_name}.\n"
            f"سقف فعلی: {user.referrals_count}/{user.max_referrals}\n"
            f"لطفاً سقف جدید دعوت را به صورت عددی وارد کنید."
        )
        return GET_NEW_REFERRAL_LIMIT

    except ValueError:
        await update.message.reply_text(
            "❌ آی‌دی وارد شده نامعتبر است. لطفاً یک عدد صحیح وارد کنید."
        )
        return GET_USER_ID_TO_UPDATE


async def get_new_referral_limit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت سقف جدید و به‌روزرسانی پایگاه داده."""
    try:
        new_limit = int(update.message.text)

        if new_limit < 0:
            await update.message.reply_text("❌ سقف دعوت نمی‌تواند منفی باشد. لطفاً یک عدد مثبت وارد کنید.")
            return GET_NEW_REFERRAL_LIMIT

        user_id = context.user_data.get('user_to_update_id')

        with database.connection.SessionLocal() as db:
            updated_user = database.crud.update_user_max_referrals(db, user_id, new_limit)

            if updated_user:
                # اطلاع‌رسانی به کاربر در صورت افزایش سقف
                if new_limit > updated_user.referrals_count and updated_user.role == "customer":
                    try:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 خبر خوش!\n"
                                 f"سقف دعوت‌های شما توسط ادمین به {new_limit} نفر افزایش یافت.\n"
                                 f"اکنون می‌توانید {new_limit - updated_user.referrals_count} نفر دیگر را دعوت کنید!"
                        )
                    except Exception:
                        pass  # اگر پیام ارسال نشد، نادیده بگیر

                await update.message.reply_text(
                    f"✅ سقف دعوت برای کاربر '{updated_user.full_name}' از {updated_user.referrals_count} به {new_limit} تغییر یافت."
                )
            else:
                await update.message.reply_text(
                    "❌ خطایی در به‌روزرسانی رخ داد. لطفاً دوباره تلاش کنید."
                )

    except ValueError:
        await update.message.reply_text(
            "❌ سقف دعوت باید یک عدد صحیح باشد. لطفاً دوباره تلاش کنید."
        )
        return GET_NEW_REFERRAL_LIMIT

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """لغو فرآیند مکالمه."""
    await update.message.reply_text("عملیات لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END


async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to show statistics."""
    ADMIN_ID = 2138687434
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما اجازه دسترسی به این دستور را ندارید.")
        return

    try:
        with database.connection.SessionLocal() as db:
            # آمار سفارشات
            stats = database.crud.get_orders_stats(db)

            # آمار کاربران
            total_users = len(database.crud.get_all_users(db))

            # آمار کدهای دعوت
            total_referral_codes = db.query(database.models.ReferralCode).count()
            active_referral_codes = db.query(database.models.ReferralCode).filter(
                database.models.ReferralCode.is_active == True
            ).count()
            admin_codes = db.query(database.models.ReferralCode).filter(
                database.models.ReferralCode.creator_role == "admin"
            ).count()
            customer_codes = db.query(database.models.ReferralCode).filter(
                database.models.ReferralCode.creator_role == "customer"
            ).count()

            stats_message = f"""
📊 آمار ربات:

👥 کل کاربران: {total_users}

📋 کل سفارشات: {stats['total']}
✅ تأیید شده: {stats['confirmed']}
⏳ در انتظار: {stats['pending']}
❌ لغو شده: {stats['cancelled']}

🔗 آمار کدهای دعوت:
📝 کل کدها: {total_referral_codes}
✅ فعال: {active_referral_codes}
👑 ادمین: {admin_codes}
👤 مشتریان: {customer_codes}

📅 آخرین به‌روزرسانی: {get_persian_datetime()}
"""

            await update.message.reply_text(stats_message.strip())

    except Exception as e:
        await update.message.reply_text("❌ خطا در دریافت آمار.")


# اضافه کردن این کدها به handlers/admin.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.admin import get_customers_keyboard, get_wallet_management_keyboard
from utils.referral import get_persian_datetime

# وضعیت‌های جدید conversation
(GET_CUSTOMER_ID, GET_PRINT_PRICE, GET_WALLET_AMOUNT, GET_TRANSACTION_DESCRIPTION) = range(10, 14)

ADMIN_ID = 2138687434


async def wallet_management_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر اصلی برای مدیریت کیف پول مشتریان."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما اجازه دسترسی به این قسمت را ندارید.")
        return

    with database.connection.SessionLocal() as db:
        customers = database.crud.get_customers(db)

        if not customers:
            await update.message.reply_text("هنوز هیچ مشتری‌ای ثبت‌نام نکرده است.")
            return

        keyboard = get_customers_keyboard(customers)
        await update.message.reply_text(
            "👥 لیست مشتریان:\n\n"
            "لطفاً مشتری مورد نظر را انتخاب کنید:",
            reply_markup=keyboard
        )


async def handle_customer_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت انتخاب مشتری از کیبورد."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_customer_selection":
        await query.edit_message_text("❌ انتخاب مشتری لغو شد.")
        return

    if query.data == "back_to_customers":
        with database.connection.SessionLocal() as db:
            customers = database.crud.get_customers(db)
            keyboard = get_customers_keyboard(customers)
            await query.edit_message_text(
                "👥 لیست مشتریان:\n\n"
                "لطفاً مشتری مورد نظر را انتخاب کنید:",
                reply_markup=keyboard
            )
        return

    if query.data.startswith("customer_"):
        customer_id = int(query.data.split("_")[1])

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            if not customer:
                await query.edit_message_text("❌ مشتری یافت نشد.")
                return

            # نمایش اطلاعات مشتری
            info_text = (
                f"👤 **اطلاعات مشتری:**\n\n"
                f"**نام:** {customer.full_name}\n"
                f"**شماره تماس:** {customer.phone_number}\n"
                f"**موجودی کیف پول:** ${customer.wallet_balance:.2f}\n"
                f"**قیمت هر گرم پرینت:** ${customer.print_price_per_gram:.2f}\n"
                f"**تعداد دعوت‌ها:** {customer.referrals_count}/{customer.max_referrals}\n\n"
                f"عملیات مورد نظر را انتخاب کنید:"
            )

            keyboard = get_wallet_management_keyboard(customer_id)
            await query.edit_message_text(info_text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_wallet_operations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت عملیات کیف پول."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_wallet_management":
        await query.edit_message_text("❌ مدیریت کیف پول لغو شد.")
        return ConversationHandler.END

    if query.data.startswith("set_price_"):
        customer_id = int(query.data.split("_")[2])
        context.user_data['customer_id'] = customer_id
        context.user_data['operation'] = 'set_price'

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            await query.edit_message_text(
                f"💳 تنظیم قیمت پرینت برای {customer.full_name}\n\n"
                f"قیمت فعلی: ${customer.print_price_per_gram:.2f} در هر گرم\n\n"
                f"لطفاً قیمت جدید هر گرم پرینت را به دلار وارد کنید:"
            )
        return GET_PRINT_PRICE

    elif query.data.startswith("wallet_charge_"):
        customer_id = int(query.data.split("_")[2])
        context.user_data['customer_id'] = customer_id
        context.user_data['operation'] = 'wallet_charge'

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            await query.edit_message_text(
                f"💰 شارژ/تسویه کیف پول {customer.full_name}\n\n"
                f"موجودی فعلی: ${customer.wallet_balance:.2f}\n\n"
                f"مبلغ مورد نظر را وارد کنید:\n"
                f"• برای شارژ: عدد مثبت (مثلاً 50)\n"
                f"• برای کسر از حساب: عدد منفی (مثلاً -25)"
            )
        return GET_WALLET_AMOUNT

    elif query.data.startswith("view_transactions_"):
        customer_id = int(query.data.split("_")[2])

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            transactions = database.crud.get_user_wallet_transactions(db, customer_id, limit=10)

            if not transactions:
                message = f"📊 تراکنش‌های {customer.full_name}\n\nهیچ تراکنشی یافت نشد."
            else:
                message = f"📊 آخرین تراکنش‌های {customer.full_name}\n\n"
                for trans in transactions:
                    trans_type = "شارژ ➕" if trans.amount > 0 else "برداشت ➖"
                    message += f"**{trans_type}**\n"
                    message += f"مبلغ: ${abs(trans.amount):.2f}\n"
                    message += f"توضیح: {trans.description}\n"
                    message += f"تاریخ: {trans.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                    message += "---\n"

            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data=f"customer_{customer_id}")
            ]])

            await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")


async def get_print_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت جدید پرینت."""
    try:
        new_price = float(update.message.text)

        if new_price <= 0:
            await update.message.reply_text("❌ قیمت باید عددی مثبت باشد. لطفاً دوباره تلاش کنید.")
            return GET_PRINT_PRICE

        customer_id = context.user_data['customer_id']

        with database.connection.SessionLocal() as db:
            updated_customer = database.crud.update_user_print_price(db, customer_id, new_price)

            if updated_customer:
                await update.message.reply_text(
                    f"✅ قیمت پرینت برای {updated_customer.full_name} به ${new_price:.2f} در هر گرم تغییر یافت.\n\n"
                    f"📱 اطلاع‌رسانی به مشتری ارسال شد."
                )

                # اطلاع‌رسانی به مشتری
                try:
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text=f"💳 اطلاع‌رسانی تغییر قیمت\n\n"
                             f"قیمت پرینت شما به ${new_price:.2f} در هر گرم تغییر یافت."
                    )
                except:
                    pass

            else:
                await update.message.reply_text("❌ خطا در به‌روزرسانی قیمت.")

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GET_PRINT_PRICE

    context.user_data.clear()
    return ConversationHandler.END


async def get_wallet_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ شارژ/برداشت."""
    try:
        amount = float(update.message.text)

        customer_id = context.user_data['customer_id']
        context.user_data['amount'] = amount

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            operation_type = "شارژ" if amount > 0 else "برداشت از"
            await update.message.reply_text(
                f"💰 {operation_type} کیف پول {customer.full_name}\n\n"
                f"مبلغ: ${abs(amount):.2f}\n"
                f"موجودی فعلی: ${customer.wallet_balance:.2f}\n"
                f"موجودی جدید: ${customer.wallet_balance + amount:.2f}\n\n"
                f"لطفاً عنوان/توضیح این تراکنش را وارد کنید:"
            )

        return GET_TRANSACTION_DESCRIPTION

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return GET_WALLET_AMOUNT


async def get_transaction_description_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات تراکنش و اجرای عملیات."""
    description = update.message.text.strip()

    if not description:
        await update.message.reply_text("❌ لطفاً توضیح تراکنش را وارد کنید.")
        return GET_TRANSACTION_DESCRIPTION

    customer_id = context.user_data['customer_id']
    amount = context.user_data['amount']
    admin_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        updated_customer = database.crud.update_user_wallet_balance(
            db, customer_id, amount, description, admin_id
        )

        if updated_customer:
            operation_type = "شارژ شد" if amount > 0 else "کسر شد"
            await update.message.reply_text(
                f"✅ تراکنش با موفقیت انجام شد!\n\n"
                f"👤 مشتری: {updated_customer.full_name}\n"
                f"💰 مبلغ: ${abs(amount):.2f} {operation_type}\n"
                f"📝 توضیح: {description}\n"
                f"💳 موجودی جدید: ${updated_customer.wallet_balance:.2f}\n\n"
                f"📱 اطلاع‌رسانی به مشتری ارسال شد."
            )

            # اطلاع‌رسانی به مشتری
            try:
                operation_emoji = "➕" if amount > 0 else "➖"
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=f"💰 تغییر موجودی کیف پول {operation_emoji}\n\n"
                         f"مبلغ: ${abs(amount):.2f}\n"
                         f"توضیح: {description}\n"
                         f"موجودی جدید: ${updated_customer.wallet_balance:.2f}\n"
                         f"تاریخ: {get_persian_datetime()}"
                )
            except:
                pass

        else:
            await update.message.reply_text("❌ خطا در انجام تراکنش.")

    context.user_data.clear()
    return ConversationHandler.END


# در handlers/admin.py اضافه کنید:

async def show_group_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات سطح‌بندی گروه"""
    from utils.group_settings import GroupLevelSettings

    with database.connection.SessionLocal() as db:
        settings = GroupLevelSettings.get_settings(db)

        message = "⚙️ **تنظیمات سطح‌بندی گروه**\n\n"
        message += f"🥈 **نقره‌ای:** {settings['silver_threshold']} گرم/روز → {settings['silver_discount']}% تخفیف\n"
        message += f"🥇 **طلایی:** {settings['gold_threshold']} گرم/روز → {settings['gold_discount']}% تخفیف\n\n"
        message += "برای تغییر تنظیمات از دکمه‌های زیر استفاده کنید:"

        keyboard = [
            [("🥈 تنظیم نقره‌ای", "admin_group_silver"), ("🥇 تنظیم طلایی", "admin_group_gold")],
            [("🔙 بازگشت", "back_to_admin_main")]
        ]

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(text, callback_data=data) for text, data in row] for row in keyboard])
        )


# در handlers/admin.py - اضافه کن به انتهای فایل:

async def handle_admin_settings_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های تنظیمات ادمین"""
    query = update.callback_query
    await query.answer()

    if query.data == "admin_settings":
        from keyboards.admin_settings import get_admin_settings_keyboard
        keyboard = get_admin_settings_keyboard()

        with database.connection.SessionLocal() as db:
            delay = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

        message = (
            f"⚙️ **تنظیمات سیستم**\n\n"
            f"⏰ تاخیر دسترسی ادیتورها: {delay} دقیقه\n\n"
            f"لطفاً گزینه مورد نظر را انتخاب کنید:"
        )

        await query.edit_message_text(message, reply_markup=keyboard, parse_mode="Markdown")

    elif query.data == "admin_editor_delay":
        # نمایش منوی تاخیر
        from handlers.admin_settings import show_editor_delay_menu
        await show_editor_delay_menu(query, context)

    elif query.data == "back_to_admin_main":
        from keyboards.admin import get_admin_main_menu
        keyboard = get_admin_main_menu()
        await query.edit_message_text(
            "🏠 **منوی اصلی ادمین**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )