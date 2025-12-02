# utils/notification_scheduler.py
import asyncio
from datetime import datetime
import logging
from utils.timezone_utils import format_shamsi_short

logger = logging.getLogger(__name__)


async def schedule_editor_notification(bot, delay_seconds: float, notification_data: dict):
    """Schedule یه نوتیفیکیشن با delay"""

    logger.info(f"📅 نوتیفیکیشن schedule شد برای {delay_seconds} ثانیه ({delay_seconds / 60:.1f} دقیقه) بعد")

    # صبر کن
    await asyncio.sleep(delay_seconds)

    # حالا بفرست
    try:
        from config import EDITORS_IDS

        notification_text = (
            f"🆕 **فایل جدید قابل دسترس**\n\n"
            f"📄 فایل: {notification_data['file_name']}\n"
            f"👤 مشتری: {notification_data['customer_code']}\n"
            f"🕐 ددتایم ادیت: {notification_data['edit_deadline_display']}\n"
            f"📝 توضیحات: {notification_data['description'] or 'ندارد'}\n\n"
            f"💡 فایل اکنون آماده دریافت است."
        )

        for editor_id in EDITORS_IDS:
            try:
                await bot.send_message(
                    chat_id=editor_id,
                    text=notification_text,
                    parse_mode="Markdown"
                )
                logger.info(f"✅ نوتیفیکیشن به ادیتور {editor_id} ارسال شد")
            except Exception as e:
                logger.error(f"❌ خطا در ارسال به ادیتور {editor_id}: {e}")

    except Exception as e:
        logger.error(f"❌ خطا در ارسال نوتیفیکیشن: {e}")