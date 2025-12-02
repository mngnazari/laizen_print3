# keyboards/file_keyboards.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def create_initial_keyboard(print_count: int = 1) -> InlineKeyboardMarkup:
    """
    Creates the initial inline keyboard for a new file order.
    Includes buttons for 'Cancel' and 'Edit Count'.
    """
    keyboard = [
        [
            InlineKeyboardButton("❌ انصراف", callback_data="cancel_order"),
            InlineKeyboardButton(f"🔢 تعداد ({print_count})", callback_data="edit_count")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_count_keyboard(print_count: int = 1) -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for editing the print count.
    Includes buttons for 'Decrease', 'Display Count', 'Increase', 'Confirm', and 'Cancel'.
    """
    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data="decrease_count"),
            InlineKeyboardButton(f"{print_count}", callback_data="show_count"),
            InlineKeyboardButton("➕", callback_data="increase_count")
        ],
        [
            InlineKeyboardButton("✅ تأیید", callback_data="confirm_count"),
            InlineKeyboardButton("❌ انصراف", callback_data="cancel_count_edit")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def create_final_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Creates the inline keyboard for confirming order deletion.
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ بله، مطمئنم", callback_data="confirm_delete"),
            InlineKeyboardButton("❌ خیر", callback_data="back_to_initial")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)