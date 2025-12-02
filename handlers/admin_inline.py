# handlers/admin_inline.py - مدیریت منوی شیشه‌ای ادمین
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import database.crud
import database.connection
import database.models
from keyboards.admin import get_admin_main_menu, get_admin_back_button
from keyboards.customer_management import get_customers_list_keyboard
from keyboards.admin_settings import get_admin_settings_keyboard
from utils.referral import generate_referral_code, get_persian_datetime

ADMIN_ID = 2138687434


async def show_admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی ادمین"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("شما اجازه دسترسی ندارید.")
        return

    admin_name = update.effective_user.full_name or "ادمین"
    welcome_text = (
        f"🔐 **پنل مدیریت**\n\n"
        f"سلام {admin_name}!\n"
        f"به پنل مدیریت ربات خوش آمدید.\n\n"
        f"🕐 **زمان:** {get_persian_datetime()}\n\n"
        f"لطفاً عملیات مورد نظر را انتخاب کنید:"
    )

    keyboard = get_admin_main_menu()

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های منوی ادمین"""
    query = update.callback_query
    await query.answer()

    if update.effective_user.id != ADMIN_ID:
        await query.edit_message_text("شما اجازه دسترسی ندارید.")
        return

    # بازگشت به منوی اصلی
    if query.data == "admin_main_menu" or query.data == "back_to_admin_main":
        admin_name = update.effective_user.full_name or "ادمین"
        welcome_text = (
            f"🔐 **پنل مدیریت**\n\n"
            f"سلام {admin_name}!\n"
            f"به پنل مدیریت ربات خوش آمدید.\n\n"
            f"🕐 **زمان:** {get_persian_datetime()}\n\n"
            f"لطفاً عملیات مورد نظر را انتخاب کنید:"
        )

        keyboard = get_admin_main_menu()
        await query.edit_message_text(
            welcome_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # تولید لینک دعوت
    elif query.data == "admin_generate_link":
        try:
            with database.connection.SessionLocal() as db:
                admin_user = database.crud.add_admin_if_not_exists(
                    db,
                    user_id=update.effective_user.id,
                    full_name=update.effective_user.full_name or "ادمین",
                    phone_number=None
                )

                referral_code = generate_referral_code()
                referral = database.crud.create_admin_referral_code(db, admin_id=update.effective_user.id,
                                                                    code=referral_code)

                bot_info = await context.bot.get_me()
                bot_username = bot_info.username
                referral_link = f"https://t.me/{bot_username}?start={referral.referral_code}"

                success_text = (
                    f"✅ لینک دعوت تولید شد!\n\n"
                    f"🔗 کد دعوت: `{referral.referral_code}`\n"
                    f"🌐 لینک دعوت:\n{referral_link}"
                )

                keyboard = get_admin_back_button()
                await query.edit_message_text(
                    success_text,
                    reply_markup=keyboard
                )
        except Exception as e:
            error_text = f"❌ خطا در تولید لینک دعوت:\n{str(e)}"
            keyboard = get_admin_back_button()
            await query.edit_message_text(
                error_text,
                reply_markup=keyboard
            )

    # مشاهده کاربران
    elif query.data == "admin_view_users":
        with database.connection.SessionLocal() as db:
            users = database.crud.get_all_users(db)

            if not users:
                message = "❌ **هنوز هیچ کاربری ثبت‌نام نکرده است.**"
            else:
                message = f"👥 **لیست کاربران ثبت‌نام شده:** ({len(users)} نفر)\n\n"
                for i, user in enumerate(users[:10], 1):
                    message += f"**{i}.** {user.full_name}\n"
                    message += f"**آی‌دی:** `{user.id}`\n"
                    message += f"**موبایل:** {user.phone_number or 'نامشخص'}\n"
                    message += f"**نقش:** {user.role or 'مشتری'}\n"
                    if user.customer_code:
                        message += f"**کد مشتری:** {user.customer_code}\n"
                    message += f"**دعوت‌ها:** {user.referrals_count}/{user.max_referrals}\n"
                    message += f"**اعتبار:** ${int(user.discount_credit)}\n"
                    message += "─────────────\n"

                if len(users) > 10:
                    message += f"\n📋 *و {len(users) - 10} کاربر دیگر...*"

        keyboard = get_admin_back_button()
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # نمایش ساختار دعوت
    elif query.data == "admin_referral_tree":
        with database.connection.SessionLocal() as db:
            users = database.crud.get_all_users(db)

            if not users:
                message = "❌ **هیچ کاربری برای نمایش ساختار درختی وجود ندارد.**"
            else:
                referral_map = {}
                root_users = []
                user_map = {user.id: user for user in users}

                for user in users:
                    if user.referrer_id and user.referrer_id in user_map:
                        if user.referrer_id not in referral_map:
                            referral_map[user.referrer_id] = []
                        referral_map[user.referrer_id].append(user)
                    else:
                        root_users.append(user)

                message = "🌳 **ساختار درختی دعوت:**\n\n"

                if root_users:
                    for root in root_users[:5]:
                        message += f"**{root.full_name}** (`{root.id}`) - {root.referrals_count}/{root.max_referrals}\n"

                        if root.id in referral_map:
                            for child in referral_map[root.id][:3]:
                                message += f"  └─ **{child.full_name}** - {child.referrals_count}/{child.max_referrals}\n"
                        message += "\n"
                else:
                    message += "هیچ ساختار دعوتی موجود نیست."

        keyboard = get_admin_back_button()
        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # تنظیم سقف دعوت
    elif query.data == "admin_set_limit":
        instruction_text = (
            "⚙️ **تنظیم سقف دعوت**\n\n"
            "برای تنظیم سقف دعوت کاربران از دستور زیر استفاده کنید:\n\n"
            "`تنظیم سقف دعوت ⚙️`\n\n"
            "سپس آی‌دی کاربر و سقف جدید را وارد کنید."
        )

        keyboard = get_admin_back_button()
        await query.edit_message_text(
            instruction_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # مدیریت مشتریان
    elif query.data == "admin_customer_mgmt":
        with database.connection.SessionLocal() as db:
            customers = database.crud.get_customers(db)

            if not customers:
                error_text = "❌ **هنوز هیچ مشتری‌ای ثبت‌نام نکرده است.**"
                keyboard = get_admin_back_button()
                await query.edit_message_text(
                    error_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return

            keyboard = get_customers_list_keyboard(customers)
            await query.edit_message_text(
                "👥 **مدیریت مشتریان**\n\n"
                "لطفاً مشتری مورد نظر را انتخاب کنید:",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

    # رسیدهای دریافتی
    elif query.data == "admin_receipts":
        from handlers.receipt_management import show_receipts_list
        await show_receipts_list(update, context)

    # تنظیمات
    elif query.data == "admin_settings":
        with database.connection.SessionLocal() as db:
            delay = database.crud.get_system_setting(db, "editor_access_delay_minutes", "0")

        settings_text = (
            f"⚙️ **تنظیمات سیستم**\n\n"
            f"⏰ تاخیر دسترسی ادیتورها: {delay} دقیقه\n\n"
            f"لطفاً بخش مورد نظر را انتخاب کنید:"
        )

        keyboard = get_admin_settings_keyboard()
        await query.edit_message_text(
            settings_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # تاخیر دسترسی ادیتورها
    elif query.data == "admin_editor_delay":
        from handlers.admin_settings import show_editor_delay_menu_inline
        await show_editor_delay_menu_inline(query, context)

    # مدیریت روزهای تعطیل
    elif query.data == "admin_holidays":
        await query.edit_message_text(
            "📅 **مدیریت روزهای تعطیل**\n\nاین قسمت در حال توسعه است...",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")
            ]])
        )



    # آمار تنظیمات
    elif query.data == "admin_settings_stats":
        await query.edit_message_text(
            "📊 **آمار تنظیمات**\n\nاین قسمت در حال توسعه است...",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")
            ]])
        )

    # آمار کلی
    elif query.data == "admin_stats":
        try:
            with database.connection.SessionLocal() as db:
                stats = database.crud.get_orders_stats(db)
                total_users = len(database.crud.get_all_users(db))

                total_referral_codes = db.query(database.models.ReferralCode).count()
                active_referral_codes = db.query(database.models.ReferralCode).filter(
                    database.models.ReferralCode.is_active == True
                ).count()

                stats_message = f"""📊 **آمار کلی ربات:**

👥 **کل کاربران:** {total_users}

📋 **سفارشات:**
- کل: {stats['total']}
- تأیید شده: {stats['confirmed']}
- در انتظار: {stats['pending']}
- لغو شده: {stats['cancelled']}

🔗 **کدهای دعوت:**
- کل: {total_referral_codes}
- فعال: {active_referral_codes}

📅 **آخرین بروزرسانی:** {get_persian_datetime()}"""

                keyboard = get_admin_back_button()
                await query.edit_message_text(
                    stats_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
        except Exception as e:
            error_text = f"❌ **خطا در دریافت آمار:**\n`{str(e)}`"
            keyboard = get_admin_back_button()
            await query.edit_message_text(
                error_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )

    # مدیریت رسیدها
    elif query.data == "admin_manage_receipts":
        from handlers.receipt_management import show_receipts_list
        await show_receipts_list(update, context)

    # جزئیات رسید
    elif query.data.startswith("admin_receipt_detail_"):
        from handlers.receipt_management import show_receipt_detail
        await show_receipt_detail(update, context)

    # شارژ از رسید
    elif query.data.startswith("admin_charge_receipt_"):
        from handlers.receipt_management import start_charge_from_receipt
        await start_charge_from_receipt(update, context)

    # رد رسید
    elif query.data.startswith("admin_reject_receipt_"):
        from handlers.receipt_management import reject_receipt
        await reject_receipt(update, context)

        # مدیریت کارکنان
    elif query.data == "admin_staff_menu":
        from handlers.staff_management import show_staff_menu
        await show_staff_menu(update, context)

