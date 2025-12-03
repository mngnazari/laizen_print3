# handlers/start.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
from database import crud

import database.connection
from keyboards.customer import get_customer_kb
from keyboards.admin import get_admin_main_menu
from .registration import start_registration
from utils.referral import extract_referral_code
from config import ADMIN_ID



async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """هندلر دستور /start."""
    user_id = update.effective_user.id
    full_name = update.effective_user.full_name or update.effective_user.username or "کاربر"
    phone_number = None

    with database.connection.SessionLocal() as db:
        # دریافت لیست staff از دیتابیس
        operators_ids = crud.get_operators_ids(db)
        editors_ids = crud.get_editors_ids(db)
        visitors_ids = crud.get_visitors_ids(db)

        # اگر ادمین بود
        if user_id == ADMIN_ID:
            crud.add_admin_if_not_exists(db, user_id=user_id, full_name=full_name, phone_number=phone_number)
            await update.message.reply_text(
                "سلام، ادمین! به ربات خوش آمدید.",
                reply_markup=get_admin_main_menu()
            )
            return ConversationHandler.END

        # اگر ادیتور بود - check first because editors might upload files
        elif user_id in editors_ids:
            from handlers.editor import handle_editor_menu
            await handle_editor_menu(update, context)
            return ConversationHandler.END

        # اگر اپراتور بود
        elif user_id in operators_ids:
            from keyboards.operator import get_operator_kb
            await update.message.reply_text(
                "سلام، اپراتور عزیز! به ربات خوش آمدید.",
                reply_markup=get_operator_kb()
            )
            return ConversationHandler.END

        # اگر ویزیتور بود
        elif user_id in visitors_ids:
            await update.message.reply_text(
                "سلام، ویزیتور عزیز! به ربات خوش آمدید.",
                # اینجا می‌تونید کیبورد ویزیتور بدید اگر دارید
            )
            return ConversationHandler.END

        # برای کاربران عادی
        user = crud.get_user(db, user_id)

        if user:
            # چک کردن نقش کاربر
            if user.role == "editor":
                from handlers.editor import handle_editor_menu
                await handle_editor_menu(update, context)
            elif user.role == "operator":
                from keyboards.operator import get_operator_kb
                await update.message.reply_text(
                    f"به ربات خوش آمدید، {user.full_name}!",
                    reply_markup=get_operator_kb()
                )
            else:  # customer
                await update.message.reply_text(
                    f"به ربات خوش آمدید، {user.full_name}!",
                    reply_markup=get_customer_kb(user_id)
                )
                from handlers.customer import show_customer_main_menu
                await show_customer_main_menu(update, context)

            return ConversationHandler.END

    # اگر کاربر جدید بود و کد دعوت داشت
    referral_code = extract_referral_code(context.args)
    if referral_code:
        with database.connection.SessionLocal() as referral_db:
            referral_info = crud.get_referral_code_info(referral_db, referral_code)
            if referral_info:
                # بررسی اینکه آیا دعوت‌کننده به سقف رسیده یا نه
                if referral_info.get('quota_exceeded', False):
                    referrer = crud.get_user(referral_db, referral_info['referrer_id'])
                    await update.message.reply_text(
                        f"❌ متاسفانه کاربر دعوت‌کننده ({referrer.full_name if referrer else 'ناشناس'}) "
                        f"به سقف تعداد دعوت‌های مجاز خود رسیده است.\n\n"
                        f"لطفاً با او تماس بگیرید و از او بخواهید که برای افزایش سقف دعوت با ادمین صحبت کند.\n"
                        f"یا از کد دعوت معتبر دیگری استفاده کنید."
                    )
                    return ConversationHandler.END
                else:
                    context.user_data['referrer_id'] = referral_info['referrer_id']
                    # شروع فرآیند ثبت‌نام
                    return await start_registration(update, context)
            else:
                await update.message.reply_text("❌ کد دعوت نامعتبر است. لطفاً از یک لینک معتبر استفاده کنید.")
                return ConversationHandler.END

    # اگر نه ادمین بود، نه اپراتور و نه کد دعوت داشت
    await update.message.reply_text(
        "سلام! برای ثبت‌نام در ربات باید از طریق یک لینک دعوت وارد شوید."
    )
    return ConversationHandler.END