# keyboards/broadcast_keyboards.py
from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def get_broadcast_main_keyboard() -> InlineKeyboardMarkup:
    """کیبورد اصلی بخش ارسال پیام"""
    keyboard = [
        [
            InlineKeyboardButton("📢 پیام تبلیغاتی", callback_data="broadcast_promotional"),
            InlineKeyboardButton("🎉 تخفیف مناسبتی", callback_data="broadcast_occasional")
        ],
        [
            InlineKeyboardButton("📊 آمار ارسال‌ها", callback_data="broadcast_stats"),
            InlineKeyboardButton("📜 تاریخچه", callback_data="broadcast_history")
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_type_selection_keyboard() -> InlineKeyboardMarkup:
    """کیبورد انتخاب نوع پیام"""
    keyboard = [
        [InlineKeyboardButton("📢 پیام تبلیغاتی", callback_data="broadcast_type_promotional")],
        [InlineKeyboardButton("🎉 تخفیف مناسبتی", callback_data="broadcast_type_occasional")],
        [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_preview_keyboard(message_type: str) -> InlineKeyboardMarkup:
    """کیبورد پیش‌نمایش و تایید ارسال"""
    keyboard = [
        [
            InlineKeyboardButton("✅ تایید و ارسال", callback_data=f"broadcast_confirm_{message_type}"),
            InlineKeyboardButton("🔄 ویرایش", callback_data=f"broadcast_edit_{message_type}")
        ],
        [InlineKeyboardButton("❌ لغو", callback_data="broadcast_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    """کیبورد لغو"""
    keyboard = [
        [InlineKeyboardButton("❌ لغو و بازگشت", callback_data="broadcast_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_history_keyboard(broadcasts: list, page: int = 0) -> InlineKeyboardMarkup:
    """کیبورد نمایش تاریخچه پیام‌ها"""
    keyboard = []

    # نمایش پیام‌ها
    for broadcast in broadcasts:
        type_emoji = "📢" if broadcast.message_type == "promotional" else "🎉"
        button_text = f"{type_emoji} {broadcast.id} - {broadcast.successful_sends}/{broadcast.total_recipients}"
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"broadcast_view_{broadcast.id}")
        ])

    # دکمه‌های ناوبری
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"broadcast_history_page_{page - 1}"))
    nav_buttons.append(InlineKeyboardButton("🔙 بازگشت", callback_data="broadcast_main"))
    if len(broadcasts) >= 10:  # اگر 10 تا باشه احتمالا صفحه بعدی هم هست
        nav_buttons.append(InlineKeyboardButton("▶️ بعدی", callback_data=f"broadcast_history_page_{page + 1}"))

    keyboard.append(nav_buttons)

    return InlineKeyboardMarkup(keyboard)


def get_broadcast_detail_keyboard(broadcast_id: int) -> InlineKeyboardMarkup:
    """کیبورد جزئیات یک پیام ارسالی"""
    keyboard = [
        [InlineKeyboardButton("📋 مشاهده لاگ‌ها", callback_data=f"broadcast_logs_{broadcast_id}")],
        [InlineKeyboardButton("🔙 بازگشت به تاریخچه", callback_data="broadcast_history")]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_notification_settings_keyboard(user_id: int, current_status: str) -> InlineKeyboardMarkup:
    """کیبورد تنظیمات دریافت پیام مشتری"""
    from database.crud import get_notification_status_emoji, get_notification_status_text

    emoji = get_notification_status_emoji(current_status)
    status_text = get_notification_status_text(current_status)

    keyboard = [
        [InlineKeyboardButton(
            f"{emoji} تغییر وضعیت (فعلی: {status_text})",
            callback_data=f"toggle_notification_{user_id}"
        )],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="customer_main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)