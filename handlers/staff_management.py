# handlers/staff_management.py
"""مدیریت کارکنان (ادیتور، اپراتور، ویزیتور) توسط ادمین"""

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud as crud
import database.connection
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)

# States for conversation
WAITING_STAFF_ID = 1
WAITING_STAFF_NAME = 2


def get_staff_menu_keyboard():
    """کیبورد منوی مدیریت کارکنان"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن ادیتور", callback_data="staff_add_editor")],
        [InlineKeyboardButton("➕ افزودن اپراتور", callback_data="staff_add_operator")],
        [InlineKeyboardButton("➕ افزودن ویزیتور", callback_data="staff_add_visitor")],
        [InlineKeyboardButton("📋 لیست کارکنان", callback_data="staff_list")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main")]
    ])


async def show_staff_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی مدیریت کارکنان"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "👥 **مدیریت کارکنان**\n\n"
            "از این بخش می‌توانید ادیتور، اپراتور و ویزیتور اضافه یا حذف کنید.\n\n"
            "✅ تغییرات بدون نیاز به ریستارت بات اعمال می‌شوند.",
            reply_markup=get_staff_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "👥 **مدیریت کارکنان**\n\n"
            "از این بخش می‌توانید ادیتور، اپراتور و ویزیتور اضافه یا حذف کنید.",
            reply_markup=get_staff_menu_keyboard(),
            parse_mode="Markdown"
        )


async def handle_staff_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback های مدیریت کارکنان"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ شما دسترسی ندارید.")
        return

    data = query.data

    if data == "staff_menu":
        await show_staff_menu(update, context)

    elif data.startswith("staff_add_"):
        role = data.replace("staff_add_", "")
        role_names = {"editor": "ادیتور", "operator": "اپراتور", "visitor": "ویزیتور"}
        context.user_data['adding_staff_role'] = role

        await query.edit_message_text(
            f"➕ **افزودن {role_names.get(role, role)}**\n\n"
            f"لطفاً آیدی عددی تلگرام کاربر را ارسال کنید:\n\n"
            f"💡 کاربر می‌تواند آیدی خود را از @userinfobot دریافت کند.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انصراف", callback_data="staff_menu")]
            ])
        )
        return WAITING_STAFF_ID

    elif data == "staff_list":
        await show_staff_list(update, context)

    elif data.startswith("staff_toggle_"):
        user_id = int(data.replace("staff_toggle_", ""))
        await toggle_staff_status(update, context, user_id)

    elif data.startswith("staff_delete_"):
        user_id = int(data.replace("staff_delete_", ""))
        await confirm_delete_staff(update, context, user_id)

    elif data.startswith("staff_confirm_delete_"):
        user_id = int(data.replace("staff_confirm_delete_", ""))
        await delete_staff_confirmed(update, context, user_id)


async def receive_staff_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت آیدی کارمند جدید"""
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    role = context.user_data.get('adding_staff_role')
    if not role:
        await update.message.reply_text("❌ خطا! لطفاً دوباره از منو شروع کنید.")
        return ConversationHandler.END

    try:
        user_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(
            "❌ آیدی باید عدد باشد.\n"
            "لطفاً آیدی عددی معتبر ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 انصراف", callback_data="staff_menu")]
            ])
        )
        return WAITING_STAFF_ID

    context.user_data['new_staff_id'] = user_id

    await update.message.reply_text(
        f"✅ آیدی: `{user_id}`\n\n"
        f"حالا نام کاربر را وارد کنید (یا /skip برای رد کردن):",
        parse_mode="Markdown"
    )
    return WAITING_STAFF_NAME


async def receive_staff_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت نام کارمند و ذخیره"""
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    role = context.user_data.get('adding_staff_role')
    user_id = context.user_data.get('new_staff_id')

    if not role or not user_id:
        await update.message.reply_text("❌ خطا! لطفاً دوباره از منو شروع کنید.")
        return ConversationHandler.END

    name = None
    if update.message.text and update.message.text != "/skip":
        name = update.message.text.strip()

    with database.connection.SessionLocal() as db:
        staff = crud.add_staff(
            db=db,
            user_id=user_id,
            role=role,
            name=name,
            added_by=update.effective_user.id
        )

        role_names = {"editor": "ادیتور", "operator": "اپراتور", "visitor": "ویزیتور"}
        await update.message.reply_text(
            f"✅ **{role_names.get(role, role)} جدید اضافه شد!**\n\n"
            f"👤 آیدی: `{user_id}`\n"
            f"📝 نام: {name or 'تعیین نشده'}\n"
            f"🎭 نقش: {role_names.get(role, role)}\n\n"
            f"✨ این کاربر از همین الان دسترسی دارد.",
            parse_mode="Markdown",
            reply_markup=get_staff_menu_keyboard()
        )

    # پاک کردن داده‌های موقت
    context.user_data.pop('adding_staff_role', None)
    context.user_data.pop('new_staff_id', None)

    return ConversationHandler.END


async def show_staff_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کارکنان"""
    query = update.callback_query

    with database.connection.SessionLocal() as db:
        all_staff = crud.get_all_staff(db, active_only=False)

        if not all_staff:
            await query.edit_message_text(
                "📋 **لیست کارکنان**\n\n"
                "❌ هنوز هیچ کارمندی اضافه نشده است.",
                parse_mode="Markdown",
                reply_markup=get_staff_menu_keyboard()
            )
            return

        role_names = {"editor": "✏️ ادیتور", "operator": "🔧 اپراتور", "visitor": "👁 ویزیتور"}

        message = "📋 **لیست کارکنان**\n\n"

        buttons = []
        for staff in all_staff:
            status = "✅" if staff.is_active else "❌"
            role_emoji = role_names.get(staff.role, staff.role)
            name_display = staff.name or f"ID: {staff.user_id}"

            message += f"{status} {role_emoji} | {name_display} | `{staff.user_id}`\n"

            # دکمه برای هر کارمند
            btn_text = f"{'غیرفعال' if staff.is_active else 'فعال'} کردن {staff.user_id}"
            buttons.append([
                InlineKeyboardButton(f"🔄 {staff.user_id}", callback_data=f"staff_toggle_{staff.user_id}"),
                InlineKeyboardButton(f"🗑", callback_data=f"staff_delete_{staff.user_id}")
            ])

        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="staff_menu")])

        await query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def toggle_staff_status(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """تغییر وضعیت فعال/غیرفعال کارمند"""
    query = update.callback_query

    with database.connection.SessionLocal() as db:
        staff = crud.get_staff_by_user_id(db, user_id)
        if staff:
            staff.is_active = not staff.is_active
            db.commit()
            status = "فعال ✅" if staff.is_active else "غیرفعال ❌"
            await query.answer(f"وضعیت به {status} تغییر کرد", show_alert=True)
        else:
            await query.answer("کارمند یافت نشد!", show_alert=True)

    # رفرش لیست
    await show_staff_list(update, context)


async def confirm_delete_staff(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """تایید حذف کارمند"""
    query = update.callback_query

    await query.edit_message_text(
        f"⚠️ **آیا مطمئن هستید؟**\n\n"
        f"کارمند با آیدی `{user_id}` حذف شود؟",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"staff_confirm_delete_{user_id}"),
                InlineKeyboardButton("❌ انصراف", callback_data="staff_list")
            ]
        ])
    )


async def delete_staff_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """حذف قطعی کارمند"""
    query = update.callback_query

    with database.connection.SessionLocal() as db:
        if crud.delete_staff(db, user_id):
            await query.answer("✅ کارمند حذف شد", show_alert=True)
        else:
            await query.answer("❌ خطا در حذف", show_alert=True)

    await show_staff_list(update, context)


async def cancel_staff_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو افزودن کارمند"""
    context.user_data.pop('adding_staff_role', None)
    context.user_data.pop('new_staff_id', None)
    await show_staff_menu(update, context)
    return ConversationHandler.END
