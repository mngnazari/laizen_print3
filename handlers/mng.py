# handlers/delivery_scheduler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from database.models import DeliverySchedule
from datetime import datetime, timedelta
import logging
from .holiday_manager import is_holiday, get_next_working_day

logger = logging.getLogger(__name__)

# States for conversation handler
GET_DELIVERY_COUNT, GET_CUTOFF_TIME, GET_OFFSET_HOURS = range(3)


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

        # ذخیره اطلاعات تحویل کنونی
        delivery_info = {
            'delivery_number': context.user_data['current_delivery'],
            'cutoff_time': context.user_data['current_cutoff_time'],
            'cutoff_day_offset': 0,  # همیشه همان روز
            'delivery_offset_hours': offset_hours
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
        await update.message.reply_text(
            "❌ لطفاً عددی بین 1 تا 48 وارد کنید."
        )
        return GET_OFFSET_HOURS


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
                    delivery_offset_hours=schedule_info['delivery_offset_hours']
                )
                db.add(schedule)

            db.commit()

        # ارسال پیام خلاصه با بازه‌های زمانی
        summary = "✅ **تنظیمات با موفقیت ذخیره شد!**\n\n"
        summary += "📋 **خلاصه تنظیمات:**\n\n"

        schedules = context.user_data['delivery_schedules']
        total_deliveries = len(schedules)

        # مرتب‌سازی بر اساس ساعت مرجع
        schedules_sorted = sorted(schedules, key=lambda x: x['cutoff_time'])

        for i, schedule_info in enumerate(schedules_sorted, 1):
            cutoff_time = schedule_info['cutoff_time']
            offset_hours = schedule_info['delivery_offset_hours']

            # محاسبه زمان تحویل
            cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
            total_hours = cutoff_hour + offset_hours

            if total_hours >= 24:
                delivery_day = "روز بعد"
                delivery_hour = total_hours - 24
            else:
                delivery_day = "همان روز"
                delivery_hour = total_hours

            delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d} ({delivery_day})"

            summary += f"**تحویل {i}:**\n"
            summary += f"• مرجع: {cutoff_time}\n"
            summary += f"• تحویل: {delivery_time}\n"
            summary += f"• فاصله: {offset_hours} ساعت\n\n"

        # اضافه کردن بازه‌های زمانی با منطق صحیح و واضح
        summary += "🕐 **بازه‌های دریافت فایل:**\n\n"

        if total_deliveries == 1:
            cutoff_time = schedules_sorted[0]['cutoff_time']
            offset_hours = schedules_sorted[0]['delivery_offset_hours']

            # محاسبه زمان تحویل
            cutoff_hour, cutoff_minute = map(int, cutoff_time.split(':'))
            delivery_hour = (cutoff_hour + offset_hours) % 24
            delivery_time = f"{delivery_hour:02d}:{cutoff_minute:02d}"

            summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز X:**\n"
            summary += f"فایل‌هایی هستند که از ساعت {cutoff_time} روز قبل از X تا ساعت {cutoff_time} روز X دریافت شده‌اند.\n\n"

        elif total_deliveries == 2:
            cutoff1 = schedules_sorted[0]['cutoff_time']
            cutoff2 = schedules_sorted[1]['cutoff_time']
            offset1 = schedules_sorted[0]['delivery_offset_hours']
            offset2 = schedules_sorted[1]['delivery_offset_hours']

            # محاسبه زمان‌های تحویل
            hour1, min1 = map(int, cutoff1.split(':'))
            hour2, min2 = map(int, cutoff2.split(':'))

            delivery1_hour = (hour1 + offset1) % 24
            delivery2_hour = (hour2 + offset2) % 24

            # تعیین روز تحویل به صورت صحیح
            delivery1_day_text = "روز X"
            delivery2_day_text = "روز X"

            if (hour1 + offset1) >= 24:
                delivery1_day_text = "روز X"  # همان روز X
            if (hour2 + offset2) >= 24:
                delivery2_day_text = "روز X"  # همان روز X

            delivery1_time = f"{delivery1_hour:02d}:{min1:02d}"
            delivery2_time = f"{delivery2_hour:02d}:{min2:02d}"

            summary += f"**فایل‌های تحویلی در ساعت {delivery1_time} {delivery1_day_text}:**\n"
            summary += f"فایل‌هایی هستند که از ساعت {cutoff2} روز قبل از X تا ساعت {cutoff1} روز X دریافت شده‌اند.\n\n"

            summary += f"**فایل‌های تحویلی در ساعت {delivery2_time} {delivery2_day_text}:**\n"
            summary += f"فایل‌هایی هستند که از ساعت {cutoff1} تا {cutoff2} روز X دریافت شده‌اند.\n\n"

        elif total_deliveries == 3:
            cutoffs = [s['cutoff_time'] for s in schedules_sorted]
            offsets = [s['delivery_offset_hours'] for s in schedules_sorted]

            for i, (cutoff, offset) in enumerate(zip(cutoffs, offsets)):
                hour, minute = map(int, cutoff.split(':'))
                delivery_hour = (hour + offset) % 24
                delivery_time = f"{delivery_hour:02d}:{minute:02d}"

                summary += f"**فایل‌های تحویلی در ساعت {delivery_time} روز X:**\n"

                if i == 0:
                    # اولین تحویل: از cutoff سوم روز قبل تا cutoff اول
                    prev_cutoff = cutoffs[2]  # آخرین cutoff
                    summary += f"فایل‌هایی هستند که از ساعت {prev_cutoff} روز قبل از X تا ساعت {cutoff} روز X دریافت شده‌اند.\n\n"
                elif i == 1:
                    # دومین تحویل: از cutoff اول تا cutoff دوم
                    summary += f"فایل‌هایی هستند که از ساعت {cutoffs[0]} تا {cutoff} روز X دریافت شده‌اند.\n\n"
                else:
                    # سومین تحویل: از cutoff دوم تا cutoff سوم
                    summary += f"فایل‌هایی هستند که از ساعت {cutoffs[1]} تا {cutoff} روز X دریافت شده‌اند.\n\n"

        summary += "💡 **نکته:** اگر زمان تحویل در روز تعطیل بیفتد، خودکار به اولین روز کاری منتقل می‌شود."

        await update.message.reply_text(
            text=summary,
            parse_mode="Markdown"
        )

        # پاک کردن context
        context.user_data.clear()

        logger.info("Delivery schedules saved successfully")

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


def calculate_delivery_time(order_datetime: datetime) -> datetime:
    """
    محاسبه زمان تحویل بر اساس زمان ثبت سفارش - منطق اصلاح شده
    """
    try:
        with database.connection.SessionLocal() as db:
            schedules = db.query(DeliverySchedule).filter(
                DeliverySchedule.is_active == True
            ).order_by(DeliverySchedule.delivery_number).all()

            if not schedules:
                # پیش‌فرض: تحویل فردا 13:00
                tomorrow = order_datetime.date() + timedelta(days=1)
                return get_next_working_day(
                    datetime.combine(tomorrow, datetime.min.time().replace(hour=13))
                )

            # مرتب‌سازی بر اساس ساعت مرجع
            cutoff_times = []
            for schedule in schedules:
                cutoff_hour, cutoff_minute = map(int, schedule.cutoff_time.split(':'))
                cutoff_time = datetime.min.time().replace(hour=cutoff_hour, minute=cutoff_minute)
                cutoff_times.append((cutoff_time, schedule))

            cutoff_times.sort(key=lambda x: (x[0].hour, x[0].minute))

            order_time = order_datetime.time()
            order_date = order_datetime.date()

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

                delivery_datetime = datetime.combine(
                    delivery_date,
                    datetime.min.time().replace(hour=delivery_hour, minute=cutoff_time.minute)
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
                delivery_datetime = datetime.combine(
                    delivery_date,
                    datetime.min.time().replace(hour=delivery_hour, minute=cutoff_minute)
                )

            # بررسی روز تعطیل
            if is_holiday(delivery_datetime.strftime('%Y-%m-%d')):
                delivery_datetime = get_next_working_day(delivery_datetime)

            return delivery_datetime

    except Exception as e:
        logger.error(f"Error calculating delivery time: {e}")
        tomorrow = order_datetime.date() + timedelta(days=1)
        return get_next_working_day(
            datetime.combine(tomorrow, datetime.min.time().replace(hour=13))
        )