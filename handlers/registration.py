# handlers/registration.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.customer import get_customer_kb
from keyboards.admin import get_admin_kb
from database import schemas
from utils.referral import generate_referral_code

(GET_PHONE_NUMBER, GET_FULL_NAME) = range(2)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """شروع فرآیند ثبت‌نام از طریق لینک دعوت یا دکمه ثبت‌نام."""
    await update.message.reply_text(
        "برای ثبت‌نام، لطفاً روی دکمه زیر کلیک کنید تا شماره موبایلتان را با من به اشتراک بگذارید:",
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton("اشتراک‌گذاری شماره 📱", request_contact=True)]
        ], resize_keyboard=True, one_time_keyboard=True)
    )
    return GET_PHONE_NUMBER


async def get_full_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت شماره موبایل از کاربر و درخواست نام."""
    contact = update.message.contact
    phone_number = contact.phone_number

    if not phone_number:
        await update.message.reply_text(
            "لطفاً با استفاده از دکمه «اشتراک‌گذاری شماره 📱» شماره خود را ارسال کنید.",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("اشتراک‌گذاری شماره 📱", request_contact=True)]
            ], resize_keyboard=True, one_time_keyboard=True)
        )
        return GET_PHONE_NUMBER

    context.user_data['phone_number'] = phone_number

    await update.message.reply_text(
        "شماره شما ثبت شد. لطفاً نام و نام خانوادگی خود را به صورت فارسی وارد کنید:",
        reply_markup=ReplyKeyboardRemove()
    )
    return GET_FULL_NAME


async def save_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """دریافت نام، ذخیره کاربر در دیتابیس و نمایش پنل مشتری."""
    full_name = update.message.text
    phone_number = context.user_data.get('phone_number')
    user_id = update.effective_user.id
    referrer_id = context.user_data.get('referrer_id')


    with database.connection.SessionLocal() as db:
        new_referral_code = generate_referral_code()

        user_schema = schemas.UserCreate(
            id=user_id,
            full_name=full_name,
            phone_number=phone_number,
            referrer_id=referrer_id,
            referral_code=new_referral_code,
            role = "customer"
        )

        try:
            database.crud.create_user(db, user_schema)

            # ارسال پیام به کاربر دعوت‌کننده (referrer)
            if referrer_id:
                referrer = database.crud.get_user(db, referrer_id)
                if referrer:
                    referrer_message = (
                        f"🎉 تبریک، {referrer.full_name} عزیز!\n"
                        f"کاربر جدیدی به نام **{full_name}** با کد دعوت شما به ربات پیوست.\n"
                        f"100 دلار اعتبار تخفیف به حساب شما اضافه شد.\n"
                        f"اعتبار فعلی شما: **{referrer.discount_credit} دلار**"
                    )

                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=referrer_message,
                        parse_mode="Markdown"
                    )

            await update.message.reply_text(
                f"✅ ثبت‌نام شما با موفقیت انجام شد، {full_name} عزیز!",
                reply_markup=get_customer_kb(user_id)
            )

        except Exception as e:
            await update.message.reply_text(
                f"❌ متاسفانه خطایی در ثبت‌نام رخ داد: {e}"
            )
            return ConversationHandler.END

    context.user_data.clear()
    return ConversationHandler.END