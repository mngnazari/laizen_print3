# handlers/customer.py
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import database.crud
import database.connection
from keyboards.customer import get_customer_kb
from database.models import User
from .file_archive import show_file_archive_menu
import logging
from .wallet_invoice import show_wallet_menu
from utils.timezone_utils import now_utc, now_iran, utc_to_iran, format_shamsi

# تنظیم logger
logger = logging.getLogger(__name__)



async def show_customer_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی inline مشتری."""
    from keyboards.customer import get_customer_inline_menu

    message = update.message if update.message else update.callback_query.message
    user_id = update.effective_user.id

    text = (
        "🏠 **منوی اصلی مشتری**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    if update.callback_query:
        await update.callback_query.answer()
        try:
            await message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_customer_inline_menu(user_id)
            )
        except:
            await message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_customer_inline_menu(user_id)
            )
    else:
        await message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_customer_inline_menu(user_id)
        )







async def handle_customer_inline_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای callback های منوی inline مشتری."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = query.from_user.id

    print(f"🔍 Customer inline callback: {data}")

    if data == "customer_credit_status":
        # اعتبار و وضعیت سفارش‌ها
        with database.connection.SessionLocal() as db:
            user = database.crud.get_user(db, user_id)

            if user:
                # شمارش سفارشات کاربر
                user_orders = db.query(database.models.FileOrder).filter(
                    database.models.FileOrder.user_id == user_id
                ).all()

                pending_orders = [o for o in user_orders if o.status == "pending"]
                confirmed_orders = [o for o in user_orders if o.status == "confirmed"]

                message = (
                    f"💳 **اعتبار شما:** {int(user.discount_credit)} دلار\n\n"
                    f"📊 **آمار سفارشات:**\n"
                    f"⏳ در انتظار: {len(pending_orders)}\n"
                    f"✅ تأیید شده: {len(confirmed_orders)}\n"
                    f"📋 کل سفارشات: {len(user_orders)}"
                )

                await query.message.reply_text(message, parse_mode="Markdown",
                                               reply_markup=get_customer_kb(user_id))
            else:
                await query.message.reply_text("شما هنوز ثبت‌نام نکرده‌اید. لطفاً ثبت‌نام کنید.",
                                               reply_markup=get_customer_kb(user_id))

    elif data == "customer_archive":
        # آرشیو فایل‌ها
        try:
            # ایجاد یک context مناسب
            context.user_data['archive_user_id'] = user_id

            # فراخوانی مستقیم با query.message
            from handlers.file_archive import show_file_archive_menu

            # ساخت fake update
            class FakeMessage:
                def __init__(self, original_message):
                    self.chat = original_message.chat
                    self.from_user = original_message.chat
                    self.reply_text = original_message.reply_text

            fake_update_obj = type('obj', (object,), {
                'message': FakeMessage(query.message),
                'effective_user': query.from_user,
                'effective_chat': query.message.chat,
                'callback_query': query
            })()

            await show_file_archive_menu(fake_update_obj, context)
        except Exception as e:
            print(f"❌ Error in archive: {e}")
            await query.message.reply_text(
                "📂 آرشیو فایل‌ها\n\nلطفاً از منوی ثابت دکمه 'آرشیو فایل‌ها' را انتخاب کنید.",
                reply_markup=get_customer_kb(user_id)
            )

    elif data == "customer_in_progress":
        # فایل‌های در حال انجام
        with database.connection.SessionLocal() as db:
            from utils.timezone_utils import format_shamsi

            in_progress_files = database.crud.get_customer_in_progress_files(db, user_id)

            if not in_progress_files:
                await query.message.reply_text(
                    "✅ **فایل‌های در حال انجام**\n\n"
                    "در حال حاضر هیچ فایلی در حال انجام ندارید.",
                    parse_mode="Markdown",
                    reply_markup=get_customer_kb(user_id)
                )
                return

            message = f"🔄 **فایل‌های در حال انجام** ({len(in_progress_files)})\n\n"
            message += "این فایل‌ها زمان ادیت آنها به پایان رسیده و در حال پردازش هستند:\n\n"

            for i, file in enumerate(in_progress_files, 1):
                message += f"{i}. **فایل:** `{file.file_name}`\n"
                message += f"   📦 تعداد: {file.print_count}\n"

                if file.delivery_datetime:
                    delivery_time = format_shamsi(file.delivery_datetime, include_time=True)
                    message += f"   🕐 زمان تحویل: {delivery_time}\n"

                # نمایش وضعیت
                if file.editor_status == "assigned":
                    message += f"   📝 وضعیت: در دست ادیتور\n"
                elif file.editor_status == "approved":
                    message += f"   ✅ وضعیت: ادیت شده\n"
                elif file.editor_status == "pending":
                    message += f"   ⏳ وضعیت: در صف ادیت\n"

                if file.status == "confirmed":
                    message += f"   ✓ تایید شده\n"

                message += "\n"

            message += "💡 این فایل‌ها به زودی پرینت و فاکتور خواهند شد."

            await query.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_customer_kb(user_id)
            )

    elif data == "customer_referrals":
        # زیرمجموعه‌ها
        with database.connection.SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()

            if not user or not user.referred_users:
                await query.message.reply_text("❌ شما هنوز زیرمجموعه‌ای ندارید.",
                                               reply_markup=get_customer_kb(user_id))
                return

            message = "👥 **زیرمجموعه‌های شما:**\n\n"
            for i, referred_user in enumerate(user.referred_users, 1):
                message += f"{i}. **نام:** {referred_user.full_name}\n"
                message += f"   **شماره موبایل:** {referred_user.phone_number}\n"
                message += f"   **تاریخ عضویت:** {referred_user.created_at.strftime('%Y/%m/%d')}\n"

                # شمارش سفارشات زیرمجموعه
                user_orders_count = db.query(database.models.FileOrder).filter(
                    database.models.FileOrder.user_id == referred_user.id
                ).count()
                message += f"   **تعداد سفارشات:** {user_orders_count}\n"
                message += "---\n"

            # نمایش کدهای فعال
            active_codes = database.crud.get_user_referral_codes(db, user_id)
            if active_codes:
                message += f"\n🔗 **کدهای دعوت فعال شما:**\n"
                for code in active_codes[-3:]:  # نمایش ۳ کد آخر
                    message += f"• <code>{code.referral_code}</code>\n"

            message += f"\n💰 **اعتبار کسب شده از دعوت‌ها:** {int(user.discount_credit)} دلار"
            message += f"\n📊 **وضعیت دعوت:** {user.referrals_count}/{user.max_referrals}"

            await query.message.reply_text(message, parse_mode="HTML",
                                           reply_markup=get_customer_kb(user_id))


    elif data == "customer_group_stats":

        # آمار گروهی

        try:

            from datetime import datetime, timedelta

            import jdatetime

            with database.connection.SessionLocal() as db:

                user = database.crud.get_user(db, user_id)

                if not user:
                    await query.message.reply_text("کاربر یافت نشد")

                    return

                # دریافت زیرمجموعه‌ها

                referrals = db.query(database.models.User).filter(

                    database.models.User.referrer_id == user_id

                ).all()

                print(f"🔍 DEBUG: Found {len(referrals)} referrals")

                # اعضای گروه

                group_members = [user] + referrals

                # زمان فعلی در ایران (برای نمایش)
                iran_now = now_iran()
                today_iran = iran_now.date()

                # محاسبه بازه امروز به UTC (برای مقایسه با دیتابیس)
                from datetime import datetime as dt
                today_start_iran = dt.combine(today_iran, dt.min.time())
                tomorrow_start_iran = today_start_iran + timedelta(days=1)

                # تبدیل به UTC برای query
                from utils.timezone_utils import iran_to_utc
                today_start = iran_to_utc(today_start_iran)
                tomorrow_start = iran_to_utc(tomorrow_start_iran)

                # تاریخ شمسی

                persian_date = jdatetime.date.fromgregorian(date=today_iran)

                print(f"🔍 DEBUG: Iran time now: {iran_now}")

                print(f"🔍 DEBUG: Today Iran: {today_iran}")

                print(f"🔍 DEBUG: Persian date: {persian_date}")

                total_today_weight = 0

                user_today_weight = 0

                total_all_weight = 0

                # محاسبه وزن بر اساس فاکتورها

                for member in group_members:

                    # وزن فاکتورهای امروز

                    today_invoices = db.query(database.models.Invoice).filter(

                        database.models.Invoice.customer_id == member.id,

                        database.models.Invoice.created_at >= today_start,

                        database.models.Invoice.created_at < tomorrow_start

                    ).all()

                    member_weight_today = sum(inv.weight_grams for inv in today_invoices)

                    # وزن کل فاکتورها

                    all_invoices = db.query(database.models.Invoice).filter(

                        database.models.Invoice.customer_id == member.id

                    ).all()

                    member_weight_total = sum(inv.weight_grams for inv in all_invoices)

                    print(
                        f"🔍 DEBUG: {member.full_name} - Today weight: {member_weight_today}g, Total: {member_weight_total}g")

                    total_today_weight += member_weight_today

                    total_all_weight += member_weight_total

                    if member.id == user_id:
                        user_today_weight = member_weight_today

                print(f"🔍 DEBUG: Total today weight: {total_today_weight}g")

                print(f"🔍 DEBUG: Total all-time weight: {total_all_weight}g")

                # محاسبه میانگین روزانه (آخرین 30 روز)

                days_back = 30

                start_period = today_start - timedelta(days=days_back)

                period_invoices = db.query(database.models.Invoice).filter(

                    database.models.Invoice.customer_id.in_([m.id for m in group_members]),

                    database.models.Invoice.created_at >= start_period,

                    database.models.Invoice.created_at < tomorrow_start

                ).all()

                period_weight = sum(inv.weight_grams for inv in period_invoices)

                daily_average = period_weight / days_back if days_back > 0 else 0

                # دریافت تنظیمات سطح گروه از دیتابیس

                silver_threshold = float(database.crud.get_system_setting(db, "group_silver_threshold", "50"))

                gold_threshold = float(database.crud.get_system_setting(db, "group_gold_threshold", "100"))

                silver_discount = float(database.crud.get_system_setting(db, "group_silver_discount", "5"))

                gold_discount = float(database.crud.get_system_setting(db, "group_gold_discount", "10"))

                # تعیین سطح گروه

                if daily_average >= gold_threshold:

                    group_level = "طلایی"

                    group_emoji = "🥇"

                    discount_percent = gold_discount

                elif daily_average >= silver_threshold:

                    group_level = "نقره‌ای"

                    group_emoji = "🥈"

                    discount_percent = silver_discount

                else:

                    group_level = "برنزی"

                    group_emoji = "🥉"

                    discount_percent = 0

                # ایجاد پیام

                message = f"📊 آمار گروه {user.full_name}\n\n"

                message += f"📅 تاریخ: {persian_date.strftime('%Y/%m/%d')}\n"

                message += f"👥 اعضای گروه: {len(group_members)} نفر\n"

                message += f"⚖️ وزن پرینت گروه امروز: {total_today_weight} گرم\n"

                message += f"🎯 سهم شما: {user_today_weight} گرم\n"

                message += f"📊 میانگین روزانه (30 روز): {daily_average:.1f} گرم\n\n"

                message += f"{group_emoji} سطح گروه: {group_level}\n"

                if discount_percent > 0:
                    message += f"🎁 تخفیف فعال: {discount_percent}% برای دعوت‌کننده\n"

                message += "\n"

                message += "👥 اعضای گروه:\n"

                for i, member in enumerate(group_members[:5], 1):
                    message += f"   {i}. {member.full_name}\n"

                if len(group_members) > 5:
                    remaining = len(group_members) - 5

                    message += f"   ... و {remaining} نفر دیگر\n"

                # راهنمایی برای ارتقاء سطح

                if group_level == "برنزی":

                    needed = silver_threshold - daily_average

                    message += f"\n💡 برای ارتقاء به نقره‌ای: {needed:.1f} گرم بیشتر در روز"

                elif group_level == "نقره‌ای":

                    needed = gold_threshold - daily_average

                    message += f"\n💡 برای ارتقاء به طلایی: {needed:.1f} گرم بیشتر در روز"

                else:

                    message += f"\n🎉 تبریک! شما در بالاترین سطح قرار دارید!"

                await query.message.reply_text(message, reply_markup=get_customer_kb(user_id))

                print("🔍 DEBUG: Message sent successfully")


        except Exception as e:

            print(f"❌ Error in group stats: {e}")

            import traceback

            traceback.print_exc()

            await query.message.reply_text(

                "❌ خطایی در نمایش آمار گروهی رخ داد.\n\n"

                "لطفاً از منوی ثابت دکمه 'آمار گروهی' را انتخاب کنید.",

                reply_markup=get_customer_kb(user_id)

            )

    elif data == "customer_wallet":
        # کیف پول و فاکتور
        try:
            from handlers.wallet_invoice import show_wallet_menu

            # ساخت fake update
            class FakeMessage:
                def __init__(self, original_message):
                    self.chat = original_message.chat
                    self.from_user = original_message.chat
                    self.reply_text = original_message.reply_text

            fake_update_obj = type('obj', (object,), {
                'message': FakeMessage(query.message),
                'effective_user': query.from_user,
                'effective_chat': query.message.chat,
                'callback_query': query
            })()

            await show_wallet_menu(fake_update_obj, context)
        except Exception as e:
            print(f"❌ Error in wallet: {e}")
            await query.message.reply_text(
                "💼 کیف پول و فاکتور\n\nلطفاً از منوی ثابت دکمه 'کیف پول و اعتبار و فاکتور' را انتخاب کنید.",
                reply_markup=get_customer_kb(user_id)
            )

    elif data == "customer_invite":
        # دعوت و کسب اعتبار
        with database.connection.SessionLocal() as db:
            user = database.crud.get_user(db, user_id)

            if not user:
                await query.message.reply_text("شما هنوز ثبت‌نام نکرده‌اید. لطفاً ثبت‌نام کنید.",
                                               reply_markup=ReplyKeyboardRemove())
                return

            if user.referrals_count >= user.max_referrals:
                message = (
                    "❌ متاسفانه شما به سقف دعوت مجاز رسیده‌اید.\n"
                    f"شما {user.referrals_count} نفر از {user.max_referrals} نفر را دعوت کرده‌اید.\n"
                    "برای افزایش سقف دعوت، با ادمین در تماس باشید."
                )
                await query.message.reply_text(message, parse_mode="Markdown")
                return

            try:
                referral_obj = database.crud.create_customer_referral_code(db, user_id)

                # دریافت username ربات
                me = await context.bot.get_me()
                bot_username = me.username
                referral_link = f"https://t.me/{bot_username}?start={referral_obj.referral_code}"

                silver_threshold = float(database.crud.get_system_setting(db, "group_silver_threshold", "50"))
                gold_threshold = float(database.crud.get_system_setting(db, "group_gold_threshold", "100"))
                silver_discount = float(database.crud.get_system_setting(db, "group_silver_discount", "5"))
                gold_discount = float(database.crud.get_system_setting(db, "group_gold_discount", "10"))

                from datetime import datetime, timedelta

                # زمان فعلی در ایران
                from datetime import datetime as dt
                iran_now = now_iran()
                today_iran = iran_now.date()

                # محاسبه بازه به UTC
                from utils.timezone_utils import iran_to_utc
                days_back = 30
                today_start_iran = dt.combine(today_iran, dt.min.time())
                start_period_iran = today_start_iran - timedelta(days=days_back)
                tomorrow_start_iran = today_start_iran + timedelta(days=1)

                # تبدیل به UTC برای query
                start_period = iran_to_utc(start_period_iran)
                tomorrow_start = iran_to_utc(tomorrow_start_iran)

                referrals = db.query(database.models.User).filter(
                    database.models.User.referrer_id == user_id
                ).all()
                group_members = [user] + referrals

                period_invoices = db.query(database.models.Invoice).filter(
                    database.models.Invoice.customer_id.in_([m.id for m in group_members]),
                    database.models.Invoice.created_at >= start_period,
                    database.models.Invoice.created_at < tomorrow_start
                ).all()

                period_weight = sum(inv.weight_grams for inv in period_invoices)
                daily_average = period_weight / days_back if days_back > 0 else 0

                if daily_average >= gold_threshold:
                    group_level = "طلایی"
                    group_emoji = "🥇"
                    next_level_msg = "🎉 تبریک! شما در بالاترین سطح قرار دارید!"
                elif daily_average >= silver_threshold:
                    group_level = "نقره‌ای"
                    group_emoji = "🥈"
                    next_level_msg = f"🥇 اگه به {gold_threshold:.0f} گرم برسی → طلایی می‌شی و تخفیفت میره روی {gold_discount:.0f}% 🔥"
                else:
                    group_level = "برنزی"
                    group_emoji = "🥉"
                    next_level_msg = (
                        f"🥈 فقط کافیه گروهت به {silver_threshold:.0f} گرم برسه → نقره‌ای می‌شی و {silver_discount:.0f}% تخفیف می‌گیری ✨\n"
                        f"🥇 اگه به {gold_threshold:.0f} گرم برسی → طلایی می‌شی و تخفیفت میره روی {gold_discount:.0f}% 🔥"
                    )

                first_message = (
                    f"🎉 کدت آماده‌ست! هر چی دوستای بیشتری بیاری و سفارش‌هاشون بیشتر باشه، "
                    f"سطحت بالاتر میره و تخفیفای خفن‌تری می‌گیری 😎\n\n"
                    f"📊 زیرمجموعه‌هات تا الان: {len(referrals)} نفر\n"
                    f"📊 میانگین سفارش گروهت: {daily_average:.1f} گرم تو این ماه\n\n"
                    f"{group_emoji} الان {group_level} هستی\n\n"
                    f"{next_level_msg}\n\n"
                    f"⚡ پس دست به کار شو و همین الان این پیام بعدی رو برای رفیقت بفرست!\n\n"
                    f"💡 (لینک فقط برای یک نفر فعاله، برای هر دوست جدید دوباره دکمه «🎁 دعوت و کسب اعتبار» رو بزن تا لینک جدید بسازم.)\n\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"📋 کد دعوت تو: {referral_obj.referral_code}\n"
                    f"💰 اعتبار کسب شده تا الان: {int(user.discount_credit)} دلار\n"
                    f"📈 وضعیت دعوت: {user.referrals_count}/{user.max_referrals}"
                )

                await query.message.reply_text(first_message)

                second_message = (
                    "سلام رفیق 👋\n\n"
                    "من دارم از ربات کایزنجت استفاده می‌کنم برای پرینتهای پروژتم؛ سریع، ساده و با تخفیف 🎯\n\n"
                    "🔥 مزایاش:\n"
                    "• پرینت سه‌بعدی با کیفیت عالی\n"
                    "• قیمت مناسب و شفاف\n"
                    "• تحویل سریع\n"
                    "• پشتیبانی ۲۴ ساعته\n\n"
                    "🎁 عضویت رایگانه و اعتبار هدیه هم میده!\n\n"
                    f"اینم لینکش: 👉 {referral_link}\n\n"
                    "امتحانش کن، به نظرم خیلی به کارت میاد 😊✨"
                )

                await query.message.reply_text(second_message)

            except ValueError as e:
                await query.message.reply_text(f"❌ خطا: {str(e)}")
            except Exception as e:
                logger.error(f"Error in generate_user_referral_code_handler: {str(e)}")
                await query.message.reply_text(
                    "❌ خطایی در تولید کد دعوت رخ داد. لطفاً مجدداً تلاش کنید."
                )



async def get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    """نام کاربری ربات را از API تلگرام دریافت می‌کند."""
    me = await context.bot.get_me()
    return me.username


async def handle_customer_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای دکمه‌های منوی مشتری."""
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🏠 منوی اصلی":
        await show_customer_main_menu(update, context)
        return

    else:
        print(f"🔍 DEBUG: Unknown button: '{text}'")
        await update.message.reply_text(f"دکمه ناشناخته: {text}")


async def generate_user_referral_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای تولید کد دعوت توسط کاربر عادی."""
    user_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)

        if not user:
            await update.effective_message.reply_text("شما هنوز ثبت‌نام نکرده‌اید. لطفاً ثبت‌نام کنید.",
                                                      reply_markup=ReplyKeyboardRemove())
            return

        if user.referrals_count >= user.max_referrals:
            message = (
                "❌ متاسفانه شما به سقف دعوت مجاز رسیده‌اید.\n"
                f"شما {user.referrals_count} نفر از {user.max_referrals} نفر را دعوت کرده‌اید.\n"
                "برای افزایش سقف دعوت، با ادمین در تماس باشید."
            )
            await update.effective_message.reply_text(message, parse_mode="Markdown")
            return

        try:
            referral_obj = database.crud.create_customer_referral_code(db, user_id)
            bot_username = await get_bot_username(context)
            referral_link = f"https://t.me/{bot_username}?start={referral_obj.referral_code}"

            silver_threshold = float(database.crud.get_system_setting(db, "group_silver_threshold", "50"))
            gold_threshold = float(database.crud.get_system_setting(db, "group_gold_threshold", "100"))
            silver_discount = float(database.crud.get_system_setting(db, "group_silver_discount", "5"))
            gold_discount = float(database.crud.get_system_setting(db, "group_gold_discount", "10"))

            from datetime import datetime, timedelta

            # زمان فعلی در ایران
            from datetime import datetime as dt
            iran_now = now_iran()
            today_iran = iran_now.date()

            # محاسبه بازه به UTC
            from utils.timezone_utils import iran_to_utc
            days_back = 30
            today_start_iran = dt.combine(today_iran, dt.min.time())
            start_period_iran = today_start_iran - timedelta(days=days_back)
            tomorrow_start_iran = today_start_iran + timedelta(days=1)

            # تبدیل به UTC برای query
            start_period = iran_to_utc(start_period_iran)
            tomorrow_start = iran_to_utc(tomorrow_start_iran)

            referrals = db.query(database.models.User).filter(
                database.models.User.referrer_id == user_id
            ).all()
            group_members = [user] + referrals

            period_invoices = db.query(database.models.Invoice).filter(
                database.models.Invoice.customer_id.in_([m.id for m in group_members]),
                database.models.Invoice.created_at >= start_period,
                database.models.Invoice.created_at < tomorrow_start
            ).all()

            period_weight = sum(inv.weight_grams for inv in period_invoices)
            daily_average = period_weight / days_back if days_back > 0 else 0

            if daily_average >= gold_threshold:
                group_level = "طلایی"
                group_emoji = "🥇"
                next_level_msg = "🎉 تبریک! شما در بالاترین سطح قرار دارید!"
            elif daily_average >= silver_threshold:
                group_level = "نقره‌ای"
                group_emoji = "🥈"
                next_level_msg = f"🥇 اگه به {gold_threshold:.0f} گرم برسی → طلایی می‌شی و تخفیفت می‌ره روی {gold_discount:.0f}% 🔥"
            else:
                group_level = "برنزی"
                group_emoji = "🥉"
                next_level_msg = (
                    f"🥈 فقط کافیه گروهت به {silver_threshold:.0f} گرم برسه → نقره‌ای می‌شی و {silver_discount:.0f}% تخفیف می‌گیری ✨\n"
                    f"🥇 اگه به {gold_threshold:.0f} گرم برسی → طلایی می‌شی و تخفیفت می‌ره روی {gold_discount:.0f}% 🔥"
                )

            first_message = (
                f"🎉 کدت آماده‌ست! هر چی دوستای بیشتری بیاری و سفارش‌هاشون بیشتر باشه، "
                f"سطحت بالاتر می‌ره و تخفیفای خفن‌تری می‌گیری 😎\n\n"
                f"📊 زیرمجموعه‌هات تا الان: {len(referrals)} نفر\n"
                f"📊 میانگین سفارش گروهت: {daily_average:.1f} گرم تو این ماه\n\n"
                f"{group_emoji} الان {group_level} هستی\n\n"
                f"{next_level_msg}\n\n"
                f"⚡ پس دست به کار شو و همین الان این پیام بعدی رو برای رفیقت بفرست!\n\n"
                f"💡 (لینک فقط برای یک نفر فعاله، برای هر دوست جدید دوباره دکمه «🎁 دعوت و کسب اعتبار» رو بزن تا لینک جدید بسازم.)\n\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📋 کد دعوت تو: {referral_obj.referral_code}\n"
                f"💰 اعتبار کسب شده تا الان: {int(user.discount_credit)} دلار\n"
                f"📈 وضعیت دعوت: {user.referrals_count}/{user.max_referrals}"
            )

            await update.effective_message.reply_text(first_message)

            second_message = (
                "سلام رفیق 👋\n\n"
                "من دارم از ربات کایزنجت استفاده می‌کنم برای پرینتهای پروجتم؛ سریع، ساده و با تخفیف 🎯\n\n"
                "🔥 مزایاش:\n"
                "• پرینت سه‌بعدی با کیفیت عالی\n"
                "• قیمت مناسب و شفاف\n"
                "• تحویل سریع\n"
                "• پشتیبانی ۲۴ ساعته\n\n"
                "🎁 عضویت رایگانه و اعتبار هدیه هم میده!\n\n"
                f"اینم لینکش: 👉 {referral_link}\n\n"
                "امتحانش کن، به نظرم خیلی به کارت میاد 😊✨"
            )

            await update.effective_message.reply_text(second_message)

        except ValueError as e:
            await update.effective_message.reply_text(f"❌ خطا: {str(e)}")
        except Exception as e:
            logger.error(f"Error in generate_user_referral_code_handler: {str(e)}")
            await update.effective_message.reply_text(
                "❌ خطایی در تولید کد دعوت رخ داد. لطفاً مجدداً تلاش کنید."
            )

async def show_customer_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش فاکتورهای مشتری"""
    user_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        invoices = database.crud.get_customer_invoices(db, user_id)

        if not invoices:
            await update.message.reply_text(
                "❌ شما هنوز هیچ فاکتوری ندارید.",
                reply_markup=get_customer_kb(user_id)
            )
            return

        # ذخیره لیست فاکتورها در context
        context.user_data['customer_invoices'] = [inv.id for inv in invoices]
        context.user_data['current_invoice_index'] = 0

        # نمایش اولین فاکتور
        await show_invoice_by_index(update.message, context, 0, invoices[0])


async def show_invoice_by_index(message, context: ContextTypes.DEFAULT_TYPE, index: int, invoice=None):
    """نمایش فاکتور بر اساس ایندکس"""
    user_id = message.chat.id if hasattr(message, 'chat') else message.from_user.id

    if not invoice:
        with database.connection.SessionLocal() as db:
            invoice_ids = context.user_data.get('customer_invoices', [])
            if index >= len(invoice_ids):
                return

            invoice = db.query(database.models.Invoice).filter(
                database.models.Invoice.id == invoice_ids[index]
            ).first()

    if not invoice:
        return

    total_invoices = len(context.user_data.get('customer_invoices', []))

    caption = (
        f"🧾 **فاکتور #{invoice.id}**\n\n"
        f"⚖️ **وزن:** {invoice.weight_grams} گرم\n"
        f"💰 **قیمت هر گرم:** {invoice.price_per_gram} دلار\n"
        f"💵 **مبلغ کل:** {invoice.total_amount} دلار\n"
        f"📅 **تاریخ:** {invoice.created_at.strftime('%Y/%m/%d - %H:%M')}\n\n"
        f"📊 **فاکتور {index + 1} از {total_invoices}**"
    )

    # ایجاد کیبورد ناوبری
    from keyboards.operator import create_invoice_navigation_keyboard
    keyboard = create_invoice_navigation_keyboard(index, total_invoices)

    try:
        await context.bot.send_photo(
            chat_id=user_id,
            photo=invoice.photo_file_id,
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        await message.reply_text(f"خطا در نمایش فاکتور: {str(e)}")


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

        # حذف پیام قبلی
        await query.delete_message()

        # نمایش فاکتور جدید
        with database.connection.SessionLocal() as db:
            invoice = db.query(database.models.Invoice).filter(
                database.models.Invoice.id == invoice_ids[new_index]
            ).first()

            await show_invoice_by_index(query.message, context, new_index, invoice)

    elif query.data == "back_to_customer_menu":
        await query.delete_message()
        user_id = query.from_user.id
        await context.bot.send_message(
            chat_id=user_id,
            text="🔙 بازگشت به منوی اصلی",
            reply_markup=get_customer_kb(user_id)
        )

    elif query.data == "noop":
        # دکمه‌ای که هیچ کاری نمی‌کند (نمایش شماره فاکتور)
        pass


async def show_referrals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر برای نمایش زیرمجموعه‌های مشتری."""
    user_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        user = db.query(User).filter(User.id == user_id).first()

        if not user or not user.referred_users:
            await update.message.reply_text("❌ شما هنوز زیرمجموعه‌ای ندارید.",
                                            reply_markup=get_customer_kb(user_id))
            return

        message = "👥 **زیرمجموعه‌های شما:**\n\n"
        for i, referred_user in enumerate(user.referred_users, 1):
            message += f"{i}. **نام:** {referred_user.full_name}\n"
            message += f"   **شماره موبایل:** {referred_user.phone_number}\n"
            message += f"   **تاریخ عضویت:** {referred_user.created_at.strftime('%Y/%m/%d')}\n"

            # شمارش سفارشات زیرمجموعه
            user_orders_count = db.query(database.models.FileOrder).filter(
                database.models.FileOrder.user_id == referred_user.id
            ).count()
            message += f"   **تعداد سفارشات:** {user_orders_count}\n"
            message += "---\n"

        # نمایش کدهای فعال
        active_codes = database.crud.get_user_referral_codes(db, user_id)
        if active_codes:
            message += f"\n🔗 **کدهای دعوت فعال شما:**\n"
            for code in active_codes[-3:]:  # نمایش ۳ کد آخر
                message += f"• <code>{code.referral_code}</code>\n"

        message += f"\n💰 **اعتبار کسب شده از دعوت‌ها:** {int(user.discount_credit)} دلار"
        message += f"\n📊 **وضعیت دعوت:** {user.referrals_count}/{user.max_referrals}"

        await update.message.reply_text(message, parse_mode="HTML",
                                        reply_markup=get_customer_kb(user_id))