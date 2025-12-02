# handlers/operator_files.py

from telegram import Update
from telegram.ext import ContextTypes
import database.crud
import database.connection
from keyboards.operator_files import (
    get_delivery_times_keyboard,
    get_customers_by_delivery_keyboard
)
from utils.file_naming import generate_operator_filename
from utils.delivery_grouping import group_files_by_customer, group_files_by_delivery_time
from datetime import datetime
# در handlers/operator_files.py در بالای فایل اضافه کنید:

from utils.delivery_grouping import count_total_ready_files, count_ready_files_by_delivery

# در handlers/operator_files.py اضافه کنید:

from keyboards.operator_files import (
    get_delivery_times_keyboard,
    get_customers_by_delivery_keyboard
)
# Import تنظیمات از config
from config import OPERATORS_IDS



async def show_operator_files_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی فایل‌های اپراتور"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in OPERATORS_IDS:
        await query.edit_message_text("شما اجازه دسترسی ندارید.")
        return

    keyboard = get_delivery_times_keyboard()
    await query.edit_message_text(
        "📁 **مدیریت فایل‌های پرینت**\n\n"
        "لطفاً زمان تحویل مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )



async def show_delivery_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش مشتریان برای یک زمان تحویل"""
    query = update.callback_query
    await query.answer()

    delivery_time = query.data.replace("operator_delivery_", "")

    # ارسال context.chat_data برای tracking
    keyboard = get_customers_by_delivery_keyboard(delivery_time, context.chat_data)
    await query.edit_message_text(
        f"🕐 **فایل‌های تحویل {delivery_time}**\n\n"
        "لطفاً مشتری مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def send_customer_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال فایل‌های یک مشتری خاص"""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    customer_code = parts[3]
    delivery_time = "_".join(parts[4:])

    # ایجاد کلید یکتا برای tracking
    tracking_key = f"{delivery_time}_{customer_code}"

    # اگر قبلاً ارسال شده، tracking را init کن
    if 'sent_files' not in context.chat_data:
        context.chat_data['sent_files'] = set()

    with database.connection.SessionLocal() as db:
        try:
            import jdatetime
            jd = jdatetime.datetime.strptime(delivery_time, "%Y/%m/%d %H:%M")
            gregorian_datetime = jd.togregorian()
            target_date = gregorian_datetime.strftime("%Y-%m-%d %H:%M")
        except:
            await query.edit_message_text(f"خطا در تبدیل تاریخ: {delivery_time}")
            return

        files = db.query(database.models.FileOrder).join(database.models.User).filter(
            database.models.FileOrder.status == "pending",
            database.models.User.customer_code == customer_code,
            database.models.FileOrder.delivery_datetime.like(f"{target_date}%")
        ).options(database.crud.joinedload(database.models.FileOrder.user)).all()

        if not files:
            await query.edit_message_text(f"هیچ فایلی برای مشتری {customer_code} یافت نشد.")
            return

        # ارسال فایل‌ها
        await send_files_to_operator(query, files, f"مشتری {customer_code}")

        # علامت‌گذاری به عنوان ارسال شده
        context.chat_data['sent_files'].add(tracking_key)


async def send_all_delivery_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال تمام فایل‌های یک زمان تحویل"""
    query = update.callback_query
    await query.answer()

    delivery_time = query.data.replace("operator_send_all_", "")

    # tracking برای همه
    all_tracking_key = f"{delivery_time}_ALL"

    if 'sent_files' not in context.chat_data:
        context.chat_data['sent_files'] = set()

    with database.connection.SessionLocal() as db:
        try:
            import jdatetime
            jd = jdatetime.datetime.strptime(delivery_time, "%Y/%m/%d %H:%M")
            gregorian_datetime = jd.togregorian()
            target_date = gregorian_datetime.strftime("%Y-%m-%d %H:%M")
        except:
            await query.edit_message_text(f"خطا در تبدیل تاریخ: {delivery_time}")
            return

        files = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending",
            database.models.FileOrder.delivery_datetime.like(f"{target_date}%")
        ).options(database.crud.joinedload(database.models.FileOrder.user)).all()

        if not files:
            await query.edit_message_text(f"هیچ فایلی برای زمان تحویل {delivery_time} یافت نشد.")
            return

        # ارسال فایل‌ها
        await send_files_to_operator(query, files, f"تحویل {delivery_time}")

        # علامت‌گذاری همه به عنوان ارسال شده
        context.chat_data['sent_files'].add(all_tracking_key)

        # علامت‌گذاری تک تک مشتریان هم
        for file_order in files:
            customer_tracking = f"{delivery_time}_{file_order.user.customer_code}"
            context.chat_data['sent_files'].add(customer_tracking)


async def send_files_to_operator(query, files, title: str):
    """تابع ارسال فایل‌ها - بدون تغییر وضعیت"""
    await query.edit_message_text(f"🔄 در حال ارسال فایل‌های {title}...")

    sent_count = 0

    for file_order in files:
        try:
            new_filename = generate_operator_filename(
                customer_code=file_order.user.customer_code,
                print_count=file_order.print_count,
                original_filename=file_order.file_name
            )

            await query.message.reply_document(
                document=file_order.file_id,
                filename=new_filename,
                caption=f"📄 **{new_filename}**\n"
                        f"👤 مشتری: {file_order.user.full_name}\n"
                        f"🕐 تحویل: {file_order.delivery_datetime.strftime('%Y/%m/%d %H:%M')}\n"
                        f"📝 توضیحات: {file_order.description or 'ندارد'}",
                parse_mode="Markdown"
            )

            sent_count += 1

        except Exception as e:
            print(f"خطا در ارسال فایل {file_order.file_name}: {e}")

    await query.message.reply_text(
        f"✅ **ارسال کامل شد**\n\n"
        f"📊 تعداد فایل‌های ارسال شده: {sent_count}\n"
        f"📁 دسته: {title}",
        parse_mode="Markdown"
    )

# در handlers/operator_files.py اضافه کنید:

async def handle_no_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پیام عدم وجود فایل"""
    query = update.callback_query
    await query.answer("هیچ فایلی آماده ارسال نیست!")


async def operator_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی فایل‌های اپراتور با دستور /files"""



    if update.effective_user.id not in OPERATORS_IDS:
        await update.message.reply_text("شما اجازه دسترسی ندارید.")
        return

    with database.connection.SessionLocal() as db:
        test_files = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending"
        ).limit(3).all()

        debug_info = "تست تاریخ‌ها:\n"
        for f in test_files:
            debug_info += f"فایل: {f.file_name}\n"
            debug_info += f"تاریخ در DB: {f.delivery_datetime}\n"
            debug_info += f"نوع: {type(f.delivery_datetime)}\n\n"

        await update.message.reply_text(debug_info)

    # نمایش منوی اصلی فایل‌ها
    keyboard = get_delivery_times_keyboard()
    total_files = count_total_ready_files()

    await update.message.reply_text(
        f"📁 **مدیریت فایل‌های پرینت**\n\n"
        f"📊 تعداد کل فایل‌های آماده: {total_files}\n\n"
        "لطفاً زمان تحویل مورد نظر را انتخاب کنید:",
        parse_mode="Markdown",
        reply_markup=keyboard
    )


def count_total_ready_files() -> int:
    """شمارش کل فایل‌های آماده برای ارسال به اپراتور"""
    import database.connection

    with database.connection.SessionLocal() as db:
        return db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending",
            database.models.FileOrder.sent_to_operator == False
        ).count()


