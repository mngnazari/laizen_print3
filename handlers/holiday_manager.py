# handlers/holiday_manager.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database.crud
import database.connection
from database.models import Holiday
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def create_holiday_calendar_keyboard():
    """ایجاد کیبورد 90 روزه برای تعیین روزهای تعطیل"""
    keyboard = []
    today = datetime.now()

    # تقسیم 90 روز به 15 ردیف 6 ستونی
    for week in range(15):
        row = []
        for day in range(6):
            day_index = week * 6 + day
            if day_index >= 90:
                break

            current_date = today + timedelta(days=day_index)
            date_str = current_date.strftime('%Y-%m-%d')
            display_text = current_date.strftime('%m/%d')

            # بررسی آیا روز تعطیل است یا نه
            with database.connection.SessionLocal() as db:
                holiday = db.query(Holiday).filter(Holiday.date == date_str).first()

                # اگر رکورد وجود دارد، از وضعیت ذخیره شده استفاده کن
                if holiday:
                    is_holiday = holiday.is_holiday
                else:
                    # پیش‌فرض: جمعه‌ها (weekday = 4) تعطیل هستند
                    is_holiday = current_date.weekday() == 4  # Friday = 4

                if is_holiday:
                    display_text = f"🔴 {display_text}"

            row.append(InlineKeyboardButton(
                display_text,
                callback_data=f"holiday_toggle_{date_str}"
            ))

        if row:  # فقط اگر ردیف دارای دکمه باشد
            keyboard.append(row)

    # افزودن دکمه بازگشت
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin_settings")])

    return InlineKeyboardMarkup(keyboard)


async def show_holiday_calendar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تقویم روزهای تعطیل"""
    query = update.callback_query
    await query.answer()

    keyboard = create_holiday_calendar_keyboard()

    message = (
        "📅 **مدیریت روزهای تعطیل**\n\n"
        "🔴 روزهای قرمز = تعطیل\n"
        "⚪ روزهای عادی = کاری\n\n"
        "💡 **راهنما:**\n"
        "• کلیک کنید تا وضعیت روز تغییر کند\n"
        "• تاریخ‌ها به فرمت ماه/روز نمایش داده می‌شوند\n"
        "• تغییرات فوراً ذخیره می‌شوند\n\n"
        f"📊 **بازه نمایش:** {datetime.now().strftime('%Y/%m/%d')} تا "
        f"{(datetime.now() + timedelta(days=89)).strftime('%Y/%m/%d')}"
    )

    await query.edit_message_text(
        text=message,
        parse_mode="Markdown",
        reply_markup=keyboard
    )


async def toggle_holiday(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تغییر وضعیت روز تعطیل/کاری"""
    query = update.callback_query
    await query.answer()

    # استخراج تاریخ از callback_data
    date_str = query.data.split("_")[2]  # holiday_toggle_2024-08-31 -> 2024-08-31

    try:
        with database.connection.SessionLocal() as db:
            # جستجوی رکورد موجود
            holiday = db.query(Holiday).filter(Holiday.date == date_str).first()

            if holiday:
                # تغییر وضعیت موجود
                holiday.is_holiday = not holiday.is_holiday
                status = "تعطیل" if holiday.is_holiday else "کاری"
            else:
                # ایجاد رکورد جدید (پیش‌فرض تعطیل)
                holiday = Holiday(date=date_str, is_holiday=True)
                db.add(holiday)
                status = "تعطیل"

            db.commit()

            # نمایش پیام موفقیت
            date_display = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y/%m/%d')
            success_message = f"✅ روز {date_display} به عنوان **{status}** تنظیم شد"

            await query.answer(success_message, show_alert=True)

            # بروزرسانی کیبورد
            keyboard = create_holiday_calendar_keyboard()

            await query.edit_message_reply_markup(reply_markup=keyboard)

            logger.info(f"Holiday status changed for {date_str}: {status}")

    except Exception as e:
        logger.error(f"Error toggling holiday for {date_str}: {e}")
        await query.answer("❌ خطایی رخ داد. دوباره تلاش کنید.", show_alert=True)


def is_holiday(date_str: str) -> bool:
    """بررسی آیا تاریخ مشخص شده تعطیل است یا نه"""
    try:
        with database.connection.SessionLocal() as db:
            holiday = db.query(Holiday).filter(Holiday.date == date_str).first()

            if holiday:
                # اگر رکورد وجود دارد، از وضعیت ذخیره شده استفاده کن
                return holiday.is_holiday
            else:
                # اگر رکورد وجود ندارد، بررسی کن که آیا جمعه است یا نه
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                return date_obj.weekday() == 4  # Friday = 4 (پیش‌فرض تعطیل)

    except Exception as e:
        logger.error(f"Error checking holiday status for {date_str}: {e}")
        # در صورت خطا، بررسی که آیا جمعه است
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.weekday() == 4
        except:
            return False


def get_next_working_day(start_date: datetime) -> datetime:
    """دریافت اولین روز کاری پس از تاریخ مشخص شده"""
    current_date = start_date
    max_attempts = 30  # جلوگیری از حلقه بی‌نهایت

    for _ in range(max_attempts):
        date_str = current_date.strftime('%Y-%m-%d')
        if not is_holiday(date_str):
            return current_date
        current_date += timedelta(days=1)

    # در صورت عدم یافتن روز کاری، همان روز اصلی را برگردان
    logger.warning(f"Could not find working day after {start_date.strftime('%Y-%m-%d')}")
    return start_date


def get_holiday_statistics() -> dict:
    """آمار روزهای تعطیل"""
    try:
        with database.connection.SessionLocal() as db:
            today = datetime.now().strftime('%Y-%m-%d')
            next_90_days = (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d')

            total_holidays = db.query(Holiday).filter(
                Holiday.date >= today,
                Holiday.date <= next_90_days,
                Holiday.is_holiday == True
            ).count()

            return {
                'total_holidays_90_days': total_holidays,
                'working_days_90_days': 90 - total_holidays
            }
    except Exception as e:
        logger.error(f"Error getting holiday statistics: {e}")
        return {'total_holidays_90_days': 0, 'working_days_90_days': 90}