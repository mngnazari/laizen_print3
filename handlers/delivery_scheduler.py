# handlers/delivery_scheduler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from database.models import DeliverySchedule
from datetime import datetime, timedelta
import logging
from .holiday_manager import is_holiday, get_next_working_day
from utils.timezone_utils import now_utc, now_iran, iran_to_utc

logger = logging.getLogger(__name__)

# States for conversation handler
GET_DELIVERY_COUNT, GET_CUTOFF_TIME, GET_OFFSET_HOURS, GET_EDIT_DEADLINE = range(4)

# در بالای فایل delivery_scheduler.py اضافه کنید:

# مقادیر پیش‌فرض
DEFAULT_PRINT_COUNT = 1
DEFAULT_REFERENCE_TIME = 17  # ساعت 17
DEFAULT_DELIVERY_OFFSET_HOURS = 20  # 20 ساعت بعد از زمان مرجع
DEFAULT_EDIT_DEADLINE_OFFSET_HOURS = 2  # 2 ساعت بعد از زمان مرجع


# این تابع را در delivery_scheduler.py اضافه کنید:
# ===== delivery_scheduler.py =====
# تابع calculate_file_times را با این جایگزین کنید:

def calculate_file_times():
    """
    محاسبه edit_deadline و delivery_time با توجه به تنظیمات

    همه زمان‌ها به UTC ذخیره می‌شوند
    """
    from database.connection import SessionLocal
    from database.crud import get_system_setting

    logger.info("🔧 شروع محاسبه زمان‌های فایل...")

    with SessionLocal() as db:
        delay_minutes = int(get_system_setting(db, "editor_access_delay_minutes", "0"))

    logger.info(f"⚙️ تاخیر از تنظیمات: {delay_minutes} دقیقه")

    # دریافت زمان فعلی UTC
    now = now_utc()
    logger.info(f"🕐 زمان فعلی (UTC): {now}")

    # محاسبه delivery_time
    delivery_time = calculate_delivery_time(now)

    # محاسبه edit_deadline
    edit_deadline = now + timedelta(minutes=delay_minutes)

    logger.info(f"📊 نتایج محاسبه:")
    logger.info(f"  - زمان فعلی (UTC): {now}")
    logger.info(f"  - تاخیر: {delay_minutes} دقیقه")
    logger.info(f"  - Edit Deadline (UTC): {edit_deadline}")
    logger.info(f"  - Delivery Time (UTC): {delivery_time}")

    return edit_deadline, delivery_time
async def start_delivery_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """شروع تنظیم زمان‌بندی تحویل"""
    query = update.callback_query
    await query.answer()

    # پاک کردن تنظیمات قبلی از context
    context.user_data.clear()
    context.user_data['delivery_schedules'] = []
    context.user_data['current_delivery'] = 1

    message = (
        "⚙️ **تنظیم زمان‌بندی تحویل**\n\n"
        "🔢 چند بار در روز تحویل دارید؟\n\n"
        "**گزینه‌های موجود:**\n"
        "1️⃣ یک بار در روز\n"
        "2️⃣ دو بار در روز\n"
        "3️⃣ سه بار در روز\n\n"
        "لطفاً عدد مربوطه را ارسال کنید:"
    )

    await query.edit_message_text(
        text=message,
        parse_mode="Markdown"
    )

    return GET_DELIVERY_COUNT


async def get_delivery_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت تعداد تحویل‌ها در روز"""
    try:
        count = int(update.message.text.strip())
        if count not in [1, 2, 3]:
            raise ValueError("Invalid count")

        context.user_data['total_deliveries'] = count
        context.user_data['current_delivery'] = 1

        # شروع دریافت اطلاعات اولین تحویل
        await ask_cutoff_time(update, context)
        return GET_CUTOFF_TIME

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً فقط عدد 1، 2 یا 3 را وارد کنید."
        )
        return GET_DELIVERY_COUNT

async def ask_cutoff_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """درخواست ساعت مرجع"""
    delivery_num = context.user_data['current_delivery']
    total = context.user_data['total_deliveries']

    message = (
        f"🕐 **تحویل {delivery_num} از {total}**\n\n"
        f"ساعت مرجع تحویل شماره {delivery_num} را وارد کنید:\n\n"
        "**فرمت:** `HH:MM`\n"
        "**مثال‌ها:**\n"
        "• `17:00` = ساعت 17:00\n"
        "• `14:30` = ساعت 14:30\n\n"
        "**توضیح:** فایل‌هایی که تا این ساعت ارسال شوند، در این بازه تحویل قرار می‌گیرند."
    )

    await update.message.reply_text(
        text=message,
        parse_mode="Markdown"
    )


async def get_cutoff_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت و پردازش ساعت مرجع"""
    try:
        time_input = update.message.text.strip()

        # اعتبارسنجی فرمت زمان (HH:MM)
        datetime.strptime(time_input, '%H:%M')

        # ذخیره موقت
        context.user_data['current_cutoff_time'] = time_input

        # درخواست تعداد ساعت بعد از مرجع
        delivery_num = context.user_data['current_delivery']
        message = (
            f"⏰ **تحویل {delivery_num}**\n\n"
            f"**ساعت مرجع:** {time_input}\n\n"
            f"چند ساعت بعد از ساعت مرجع، تحویل انجام شود؟\n\n"
            "**مثال‌ها:**\n"
            "• `20` = 20 ساعت بعد\n"
            "• `7` = 7 ساعت بعد\n\n"
            "**نکته:** اگر از 24 ساعت عبور کرد، به روز بعد می‌رود.\n"
            "لطفاً تعداد ساعت را وارد کنید:"
        )

        await update.message.reply_text(
            text=message,
            parse_mode="Markdown"
        )

        return GET_OFFSET_HOURS

    except ValueError:
        await update.message.reply_text(
            "❌ **فرمت اشتباه!**\n\n"
            "لطفاً به این فرمت وارد کنید: `HH:MM`\n\n"
            "مثال‌ها:\n"
            "• `17:00` (ساعت 17)\n"
            "• `14:30` (ساعت 14 و 30 دقیقه)",
            parse_mode="Markdown"
        )
        return GET_CUTOFF_TIME


async def get_offset_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت فاصله ساعتی تا تحویل"""
    try:
        offset_hours = int(update.message.text.strip())
        if offset_hours < 1 or offset_hours > 48:
            raise ValueError("Invalid offset")

        # ذخیره موقت
        context.user_data['current_delivery_offset'] = offset_hours

        # درخواست زمان مجاز ادیت
        delivery_num = context.user_data['current_delivery']
        cutoff_time = context.user_data['current_cutoff_time']

        message = (
            f"✏️ **تحویل {delivery_num} - زمان ادیت**\n\n"
            f"**ساعت مرجع:** {cutoff_time}\n"
            f"**تحویل:** {offset_hours} ساعت بعد از مرجع\n\n"
            f"چند ساعت بعد از ساعت مرجع، ادیتورها باید کارشان را تمام کرده باشند؟\n\n"
            f"**مثال‌ها:**\n"
            f"• `2` = 2 ساعت بعد از مرجع\n"
            f"• `4` = 4 ساعت بعد از مرجع\n\n"
            f"**نکته:** زمان ادیت باید کمتر از زمان تحویل ({offset_hours} ساعت) باشد.\n"
            f"لطفاً تعداد ساعت را وارد کنید:"
        )

        await update.message.reply_text(
            text=message,
            parse_mode="Markdown"
        )

        return GET_EDIT_DEADLINE

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً عددی بین 1 تا 48 وارد کنید."
        )
        return GET_OFFSET_HOURS


async def get_edit_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت زمان مجاز ادیت"""
    try:
        edit_deadline_hours = int(update.message.text.strip())
        delivery_offset = context.user_data['current_delivery_offset']

        if edit_deadline_hours < 1 or edit_deadline_hours >= delivery_offset:
            raise ValueError("Invalid edit deadline")

        # ذخیره اطلاعات تحویل کنونی
        delivery_info = {
            'delivery_number': context.user_data['current_delivery'],
            'cutoff_time': context.user_data['current_cutoff_time'],
            'cutoff_day_offset': 0,  # همیشه همان روز
            'delivery_offset_hours': delivery_offset,
            'edit_deadline_hours': edit_deadline_hours
        }

        context.user_data['delivery_schedules'].append(delivery_info)

        # بررسی آیا تحویل‌های بیشتری باقی مانده یا نه
        context.user_data['current_delivery'] += 1

        if context.user_data['current_delivery'] <= context.user_data['total_deliveries']:
            # تحویل بعدی
            await ask_cutoff_time(update, context)
            return GET_CUTOFF_TIME
        else:
            # تمام تحویل‌ها تنظیم شد، ذخیره در دیتابیس
            await save_delivery_schedules(update, context)
            return ConversationHandler.END

    except ValueError:
        delivery_offset = context.user_data['current_delivery_offset']
        await update.message.reply_text(
            f"❌ لطفاً عددی بین 1 تا {delivery_offset - 1} وارد کنید.\n"
            f"زمان ادیت باید کمتر از زمان تحویل ({delivery_offset} ساعت) باشد."
        )
        return GET_EDIT_DEADLINE


async def save_delivery_schedules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ذخیره تنظیمات در دیتابیس"""
    try:
        with database.connection.SessionLocal() as db:
            # حذف تنظیمات قبلی
            db.query(DeliverySchedule).delete()

            # ذخیره تنظیمات جدید
            for schedule_info in context.user_data['delivery_schedules']:
                schedule = DeliverySchedule(
                    delivery_number=schedule_info['delivery_number'],
                    cutoff_time=schedule_info['cutoff_time'],
                    cutoff_day_offset=schedule_info['cutoff_day_offset'],
                    delivery_offset_hours=schedule_info['delivery_offset_hours'],
                    edit_deadline_hours=schedule_info['edit_deadline_hours']
                )
                db.add(schedule)

            db.commit()

        # ارسال پیام خلاصه با تاریخ شمسی
        summary = "✅ **تنظیمات با موفقیت ذخیره شد!**\n\n"
        summary += "📋 **خلاصه تنظیمات:**\n\n"

        schedules = context.user_data['delivery_schedules']
        total_deliveries = len(schedules)

        # مرتب‌سازی بر اساس ساعت مرجع
        schedules_sorted = sorted(schedules, key=lambda x: x['cutoff_time'])

        for i, schedule_info in enumerate(schedules_sorted, 1):
            cutoff_time = schedule_info['cutoff_time']
            delivery_offset = schedule_info['delivery_offset_hours']
            edit_deadline = schedule_info['edit_deadline_hours']

            # محاسبه زمان‌ها
            cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
            delivery_hour = (cutoff_hour + delivery_offset) % 24
            edit_hour = (cutoff_hour + edit_deadline) % 24

            # تعیین روز
            delivery_day_offset = (cutoff_hour + delivery_offset) // 24
            edit_day_offset = (cutoff_hour + edit_deadline) // 24

            delivery_day_text = "همان روز" if delivery_day_offset == 0 else "روز بعد"
            edit_day_text = "همان روز" if edit_day_offset == 0 else "روز بعد"

            delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d}"
            edit_time = f"{edit_hour:02d}:{cutoff_minute:02d}"

            summary += f"**تحویل {i}:**\n"
            summary += f"• مرجع: {cutoff_time}\n"
            summary += f"• ددلاین ادیت: {edit_time} ({edit_day_text})\n"
            summary += f"• تحویل: {delivery_time} ({delivery_day_text})\n\n"

        # اضافه کردن بازه‌های دریافت فایل با تاریخ شمسی
        summary += "📁 **بازه‌های دریافت فایل:**\n\n"

        # تاریخ امروز شمسی برای محاسبه واقعی
        from datetime import datetime, timedelta
        import jdatetime

        today_gregorian = datetime.now()
        today_shamsi = jdatetime.datetime.fromgregorian(datetime=today_gregorian)

        if total_deliveries == 1:
            schedule = schedules_sorted[0]
            cutoff_time = schedule['cutoff_time']
            delivery_offset = schedule['delivery_offset_hours']
            edit_deadline = schedule['edit_deadline_hours']

            # محاسبه زمان‌ها
            cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
            delivery_hour = (cutoff_hour + delivery_offset) % 24
            edit_hour = (cutoff_hour + edit_deadline) % 24

            # تعیین روز تحویل
            delivery_day_offset = (cutoff_hour + delivery_offset) // 24

            delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d}"
            edit_time = f"{edit_hour:02d}:{cutoff_minute:02d}"

            # محاسبه تاریخ‌های شمسی
            delivery_date = today_shamsi + timedelta(days=delivery_day_offset)

            if delivery_day_offset == 0:  # تحویل امروز
                start_date = today_shamsi - timedelta(days=1)  # دیروز
                end_date = today_shamsi  # امروز
                edit_date = today_shamsi  # امروز
            else:  # تحویل فردا یا بعدتر
                start_date = today_shamsi + timedelta(days=delivery_day_offset - 2)  # 2 روز قبل از تحویل
                end_date = today_shamsi + timedelta(days=delivery_day_offset - 1)  # 1 روز قبل از تحویل
                edit_date = end_date  # همان روز آخر دریافت

            # فرمت تاریخ‌های شمسی
            delivery_date_str = delivery_date.strftime("%d %B %Y")
            start_date_str = start_date.strftime("%d %B %Y")
            end_date_str = end_date.strftime("%d %B %Y")
            edit_date_str = edit_date.strftime("%d %B %Y")

            summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
            summary += f"فایل‌هایی هستند که از ساعت {cutoff_time} روز {start_date_str} تا ساعت {cutoff_time} روز {end_date_str} دریافت شده‌اند.\n"
            summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {edit_date_str}\n\n"

        elif total_deliveries == 2:
            for i, schedule in enumerate(schedules_sorted):
                cutoff_time = schedule['cutoff_time']
                delivery_offset = schedule['delivery_offset_hours']
                edit_deadline = schedule['edit_deadline_hours']

                cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
                delivery_hour = (cutoff_hour + delivery_offset) % 24
                edit_hour = (cutoff_hour + edit_deadline) % 24

                delivery_day_offset = (cutoff_hour + delivery_offset) // 24

                delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d}"
                edit_time = f"{edit_hour:02d}:{cutoff_minute:02d}"

                delivery_date = today_shamsi + timedelta(days=delivery_day_offset)
                delivery_date_str = delivery_date.strftime("%d %B %Y")

                if i == 0:  # تحویل اول
                    # بازه: از مرجع دوم روز قبل تا مرجع اول روز قبل
                    schedule2 = schedules_sorted[1]
                    start_date = today_shamsi + timedelta(days=delivery_day_offset - 2)
                    end_date = today_shamsi + timedelta(days=delivery_day_offset - 1)
                    edit_date = end_date

                    start_date_str = start_date.strftime("%d %B %Y")
                    end_date_str = end_date.strftime("%d %B %Y")
                    edit_date_str = edit_date.strftime("%d %B %Y")

                    summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
                    summary += f"فایل‌هایی هستند که از ساعت {schedule2['cutoff_time']} روز {start_date_str} تا ساعت {cutoff_time} روز {end_date_str} دریافت شده‌اند.\n"
                    summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {edit_date_str}\n\n"
                else:  # تحویل دوم
                    # بازه: از مرجع اول تا مرجع دوم همان روز قبل
                    schedule1 = schedules_sorted[0]
                    same_day = today_shamsi + timedelta(days=delivery_day_offset - 1)
                    same_day_str = same_day.strftime("%d %B %Y")

                    summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
                    summary += f"فایل‌هایی هستند که از ساعت {schedule1['cutoff_time']} تا ساعت {cutoff_time} روز {same_day_str} دریافت شده‌اند.\n"
                    summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {same_day_str}\n\n"

        elif total_deliveries == 3:
            for i, schedule in enumerate(schedules_sorted):
                cutoff_time = schedule['cutoff_time']
                delivery_offset = schedule['delivery_offset_hours']
                edit_deadline = schedule['edit_deadline_hours']

                cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
                delivery_hour = (cutoff_hour + delivery_offset) % 24
                edit_hour = (cutoff_hour + edit_deadline) % 24

                delivery_day_offset = (cutoff_hour + delivery_offset) // 24

                delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d}"
                edit_time = f"{edit_hour:02d}:{cutoff_minute:02d}"

                delivery_date = today_shamsi + timedelta(days=delivery_day_offset)
                delivery_date_str = delivery_date.strftime("%d %B %Y")

                if i == 0:  # تحویل اول
                    schedule3 = schedules_sorted[2]
                    start_date = today_shamsi + timedelta(days=delivery_day_offset - 2)
                    end_date = today_shamsi + timedelta(days=delivery_day_offset - 1)
                    edit_date = end_date

                    start_date_str = start_date.strftime("%d %B %Y")
                    end_date_str = end_date.strftime("%d %B %Y")
                    edit_date_str = edit_date.strftime("%d %B %Y")

                    summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
                    summary += f"فایل‌هایی هستند که از ساعت {schedule3['cutoff_time']} روز {start_date_str} تا ساعت {cutoff_time} روز {end_date_str} دریافت شده‌اند.\n"
                    summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {edit_date_str}\n\n"
                elif i == 1:  # تحویل دوم
                    schedule1 = schedules_sorted[0]
                    same_day = today_shamsi + timedelta(days=delivery_day_offset - 1)
                    same_day_str = same_day.strftime("%d %B %Y")

                    summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
                    summary += f"فایل‌هایی هستند که از ساعت {schedule1['cutoff_time']} تا ساعت {cutoff_time} روز {same_day_str} دریافت شده‌اند.\n"
                    summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {same_day_str}\n\n"
                else:  # تحویل سوم
                    schedule2 = schedules_sorted[1]
                    same_day = today_shamsi + timedelta(days=delivery_day_offset - 1)
                    same_day_str = same_day.strftime("%d %B %Y")

                    summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز {delivery_date_str}:**\n"
                    summary += f"فایل‌هایی هستند که از ساعت {schedule2['cutoff_time']} تا ساعت {cutoff_time} روز {same_day_str} دریافت شده‌اند.\n"
                    summary += f"🕐 **ددلاین ادیت:** {edit_time} روز {same_day_str}\n\n"

        summary += "💡 **نکته‌های مهم:**\n"
        summary += "• اگر زمان تحویل در روز تعطیل بیفتد، خودکار به اولین روز کاری منتقل می‌شود\n"
        summary += "• ادیتورها باید کارشان را تا ددلاین مشخص شده تمام کنند\n"
        summary += "• بعد از ددلاین ادیت، فایل‌ها به اپراتور برای پرینت ارسال می‌شوند"

        await update.message.reply_text(
            text=summary,
            parse_mode="Markdown"
        )

        # پاک کردن context
        context.user_data.clear()
        logger.info("Delivery schedules with edit deadlines saved successfully")

    except Exception as e:
        logger.error(f"Error saving delivery schedules: {e}")
        await update.message.reply_text(
            "❌ خطایی در ذخیره تنظیمات رخ داد. لطفاً دوباره تلاش کنید."
        )

def calculate_sample_delivery_time(cutoff_time: str, day_offset: int, offset_hours: int) -> str:
    """محاسبه نمونه زمان تحویل برای نمایش"""
    try:
        now = datetime.now()
        cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))

        # تاریخ مرجع
        cutoff_date = now + timedelta(days=day_offset)
        cutoff_datetime = cutoff_date.replace(
            hour=cutoff_hour,
            minute=cutoff_minute,
            second=0,
            microsecond=0
        )

        # زمان تحویل
        delivery_datetime = cutoff_datetime + timedelta(hours=offset_hours)

        return delivery_datetime.strftime('%H:%M (روز %+d)')

    except Exception:
        return "نامشخص"


async def cancel_delivery_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو تنظیم زمان‌بندی"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ تنظیم زمان‌بندی لغو شد."
    )
    return ConversationHandler.END


# این تابع را در delivery_scheduler.py جایگزین کنید (خطوط 501-590)

def calculate_delivery_time(order_datetime: datetime) -> datetime:
    """
    محاسبه زمان تحویل بر اساس زمان ثبت سفارش - منطق اصلاح شده

    Args:
        order_datetime: زمان ثبت سفارش (UTC naive)

    Returns:
        زمان تحویل (UTC naive)
    """
    # تبدیل UTC به Iran time برای محاسبات
    from utils.timezone_utils import utc_to_iran
    order_iran = utc_to_iran(order_datetime)

    try:

        with database.connection.SessionLocal() as db:
            schedules = db.query(DeliverySchedule).filter(
                DeliverySchedule.is_active == True
            ).order_by(DeliverySchedule.delivery_number).all()

            if not schedules:
                # پیش‌فرض: تحویل فردا 13:00 (Iran time)
                tomorrow = order_iran.date() + timedelta(days=1)
                delivery_iran = get_next_working_day(
                    datetime.combine(tomorrow, datetime.min.time().replace(hour=13))
                )
                # تبدیل به UTC برای ذخیره در دیتابیس
                return iran_to_utc(delivery_iran)

            # مرتب‌سازی بر اساس ساعت مرجع
            cutoff_times = []
            for schedule in schedules:
                cutoff_hour, cutoff_minute = map(int, schedule.cutoff_time.split(':'))
                cutoff_time = datetime.min.time().replace(hour=cutoff_hour, minute=cutoff_minute)
                cutoff_times.append((cutoff_time, schedule))

            cutoff_times.sort(key=lambda x: (x[0].hour, x[0].minute))

            order_time = order_iran.time()
            order_date = order_iran.date()

            # تعیین اینکه در کدام بازه قرار داریم
            if len(schedules) == 1:
                # یک تحویل: 24 ساعت به دو بازه تقسیم می‌شود
                cutoff_time, schedule = cutoff_times[0]

                # محاسبه زمان تحویل
                cutoff_hour = cutoff_time.hour
                delivery_hour = (cutoff_hour + schedule.delivery_offset_hours) % 24
                delivery_date_offset = 1 if (cutoff_hour + schedule.delivery_offset_hours) >= 24 else 0

                if order_time <= cutoff_time:
                    # بازه اول: تحویل همان روز یا روز بعد
                    delivery_date = order_date + timedelta(days=delivery_date_offset)
                else:
                    # بازه دوم: تحویل 24 ساعت بعد از بازه اول
                    delivery_date = order_date + timedelta(days=delivery_date_offset + 1)

                # اصلاح: دقیقه تحویل همیشه 00 باشد
                delivery_datetime = datetime.combine(
                    delivery_date,
                    datetime.min.time().replace(hour=delivery_hour, minute=0)
                )

            else:
                # چند تحویل: بازه‌های متعدد
                selected_schedule = None
                delivery_date_offset = 0

                # پیدا کردن بازه مناسب
                for i, (cutoff_time, schedule) in enumerate(cutoff_times):
                    if order_time <= cutoff_time:
                        selected_schedule = schedule
                        break

                # اگر بعد از آخرین cutoff باشد، به اولین تحویل روز بعد
                if selected_schedule is None:
                    selected_schedule = cutoff_times[0][1]  # اولین تحویل
                    delivery_date_offset = 1

                # محاسبه زمان تحویل
                cutoff_hour, cutoff_minute = map(int, selected_schedule.cutoff_time.split(':'))
                delivery_hour = (cutoff_hour + selected_schedule.delivery_offset_hours) % 24
                schedule_day_offset = 1 if (cutoff_hour + selected_schedule.delivery_offset_hours) >= 24 else 0

                delivery_date = order_date + timedelta(days=delivery_date_offset + schedule_day_offset)

                # اصلاح: دقیقه تحویل همیشه 00 باشد
                delivery_datetime = datetime.combine(
                    delivery_date,
                    datetime.min.time().replace(hour=delivery_hour, minute=0)
                )

            # بررسی روز تعطیل
            if is_holiday(delivery_datetime.strftime('%Y-%m-%d')):
                delivery_datetime = get_next_working_day(delivery_datetime)

            # تبدیل به UTC برای ذخیره در دیتابیس
            return iran_to_utc(delivery_datetime)

    except Exception as e:
        logger.error(f"Error calculating delivery time: {e}")
        tomorrow = order_iran.date() + timedelta(days=1)
        delivery_iran = get_next_working_day(
            datetime.combine(tomorrow, datetime.min.time().replace(hour=13))
        )
        # تبدیل به UTC برای ذخیره در دیتابیس
        return iran_to_utc(delivery_iran)