00# ===============================
# 📂 Imports / ایمپورت‌ها
# ===============================

# --- Python Standard Libraries ---
import os
import pathlib
import logging
from handlers.customer import (
    handle_customer_menu,
    handle_invoice_navigation,
    show_referrals_handler,
    generate_user_referral_code_handler,
    handle_customer_inline_callbacks,  # ← جدید
    show_customer_main_menu  # ← جدید
)
# --- Telegram Libraries ---
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)

# --- Database ---
import database.connection
import database.models

# ===============================
# 🧩 Handlers Imports
# ===============================

# --- Start & Registration ---
from handlers.start import start_command, OPERATORS_IDS
from handlers.registration import (
    start_registration,
    get_full_name,
    save_user_info,
    GET_PHONE_NUMBER,
    GET_FULL_NAME
)

# --- Admin (main menus, callbacks, settings) ---
from handlers.admin import (
    handle_admin_settings_callbacks,
    generate_referral_code_handler,
    view_users_handler,
    show_referral_tree_handler,
    set_referral_limit_start,
    get_user_id_to_update_handler,
    get_new_referral_limit_handler,
    cancel_handler,
    admin_stats_handler,
    GET_USER_ID_TO_UPDATE,
    GET_NEW_REFERRAL_LIMIT
)

# --- Admin Inline ---
from handlers.admin_inline import (
    show_admin_main_menu,
    handle_admin_callbacks
)

# --- Admin Settings & Holiday ---
from handlers.admin_settings import (
    cmd_set_delay,
    show_editor_delay_menu,
    start_editor_delay_setting,
    save_editor_delay,
    cancel_editor_delay_setting,
    WAITING_EDITOR_DELAY
)
from handlers.holiday_manager import show_holiday_calendar, toggle_holiday

# --- Group Management ---
from handlers.group_admin import (
    show_group_settings_menu,
    show_group_statistics,
    reset_group_settings,
    get_silver_settings_conversation,
    get_gold_settings_conversation
)
from handlers.group_callbacks import handle_group_stats_callbacks

# --- Editor ---
from handlers.editor import (
    handle_editor_menu,
    handle_editor_callbacks,
    handle_editor_file_upload,
    show_editor_main_menu,
    EDITORS_IDS
)

# --- Vault Management ---
from handlers.vault_management import (
    show_vaults_list,
    show_vaults_menu,
    show_vault_detail,
    show_vault_transactions,
    start_create_vault,
    get_vault_name,
    get_vault_percent_and_create,
    start_set_percent,
    update_vault_percent,
    start_rename_vault,
    update_vault_name_handler,
    delete_vault_confirm,
    delete_vault_execute,
    start_expense_record,
    get_expense_amount,
    get_expense_description,
    record_expense_final,
    cancel_vault_operation,
    handle_vault_callbacks,
    show_gold_menu,
    show_gold_balance,
    start_buy_gold,
    get_gold_buy_weight,
    get_gold_buy_price,
    get_gold_buy_price_toman,
    execute_gold_buy,
    start_sell_gold,
    get_gold_sell_weight,
    get_gold_sell_price,
    get_gold_sell_price_toman,
    execute_gold_sell,
    show_gold_history,
    get_gold_buy_exchange_rate,
    get_gold_sell_exchange_rate,
    start_petty_cash_withdraw,
    get_petty_cash_withdraw_amount,
    execute_petty_cash_withdraw,
    GOLD_BUY_WEIGHT,
    GOLD_BUY_PRICE_TOMAN,
    GOLD_BUY_EXCHANGE_RATE,
    GOLD_BUY_DESC,
    GOLD_SELL_WEIGHT,
    GOLD_SELL_PRICE_TOMAN,
    GOLD_SELL_EXCHANGE_RATE,
    GOLD_SELL_DESC,
    VAULT_CREATE_NAME,
    VAULT_CREATE_PERCENT,
    VAULT_SET_PERCENT,
    VAULT_RENAME,
    EXPENSE_AMOUNT,
    EXPENSE_DESC,
    PETTY_CASH_WITHDRAW_AMOUNT,
    PETTY_CASH_WITHDRAW_DESC
)

# --- Customer Management ---
from handlers.customer_management import (
    show_customers_list,
    handle_customer_selection_callback,
    handle_customer_operations_callback,
    get_customer_wallet_amount,
    get_customer_wallet_description,
    get_customer_discount_amount,
    get_customer_discount_description,
    get_customer_print_price,
    cancel_customer_management,
    CUSTOMER_WALLET_AMOUNT,
    CUSTOMER_WALLET_DESC,
    CUSTOMER_DISCOUNT_AMOUNT,
    CUSTOMER_DISCOUNT_DESC,
    CUSTOMER_PRINT_PRICE
)

# --- Customer ---
from handlers.customer import (
    handle_customer_menu,
    handle_invoice_navigation,
    show_referrals_handler,
    generate_user_referral_code_handler
)

# --- Operator ---
from handlers.operator import (
    handle_operator_menu,
    show_operator_main_menu,
    show_operator_invoice_menu,
    handle_operator_callbacks,
    show_customers_for_invoice,
    handle_customer_file_selection,
    get_weight_handler,
    get_photo_handler,
    cancel_invoice_handler,
    show_operator_stats,
    show_customers_list as operator_show_customers_list,
    show_operator_settings,
    GET_WEIGHT,
    GET_PHOTO
)

# --- Operator Files ---
from handlers.operator_files import (
    operator_files_command,
    show_operator_files_main,
    show_delivery_customers,
    send_customer_files,
    send_all_delivery_files,
    handle_no_files
)

# --- Receipt Management ---
from handlers.receipt_management import (
    start_charge_from_receipt,
    get_receipt_charge_amount,
    get_receipt_charge_description,
    RECEIPT_CHARGE_AMOUNT,
    RECEIPT_CHARGE_DESC
)

# --- Receipt Submission ---
from handlers.receipt_submission import (
    start_receipt_submission,
    handle_receipt_photo,
    handle_end_command,
    handle_receipt_description,
    handle_finish_callback,
    cancel_receipt_submission,
    RECEIPT_UPLOAD,
    RECEIPT_DESCRIPTION
)

# --- Delivery Scheduler ---
from handlers.delivery_scheduler import (
    start_delivery_setup,
    get_delivery_count,
    get_cutoff_time,
    get_offset_hours,
    get_edit_deadline,
    cancel_delivery_setup,
    GET_DELIVERY_COUNT,
    GET_CUTOFF_TIME,
    GET_OFFSET_HOURS,
    GET_EDIT_DEADLINE
)

# --- Transaction & Wallet ---
from handlers.transaction_viewer import (
    handle_transaction_callbacks,
    handle_admin_transaction_view,
    show_transactions_list
)
from handlers.wallet_invoice import handle_wallet_callbacks

# --- File Archive ---
from handlers.file_archive import handle_archive_callback_unique

# --- File Submission ---
from handlers.file_submission import handle_file, handle_callback_query, handle_reply

# --- Test Handler ---
from handlers.test_handler import (
    handle_test_command,
    handle_test_callback,
    handle_test_main_menu
)

# --- Independent Income ---
from handlers.independent_income import (
    start_independent_income,
    get_income_amount,
    record_independent_income,
    cancel_independent_income,
    INCOME_AMOUNT,
    INCOME_DESC
)

# --- Broadcast Handler ---
from handlers.broadcast_handler import (
    get_broadcast_conversation_handler,
    broadcast_start,
    show_broadcast_statistics,
    show_broadcast_history,
    show_broadcast_detail,
    show_broadcast_logs
)
# --- Staff Management ---
from handlers.staff_management import (
    show_staff_menu,
    handle_staff_callbacks,
    receive_staff_id,
    receive_staff_name,
    cancel_staff_add,
    WAITING_STAFF_ID,
    WAITING_STAFF_NAME
)
# ===============================
# 📂 Config & Initialization
# ===============================
ADMIN_ID = 2138687434
TOKEN = "7735541106:AAHePw_XxcOkTUrq5xOMBybBMOxG43rb7WE"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def initialize_default_settings():
    """مقداردهی اولیه تنظیمات سیستم"""
    try:
        with database.connection.SessionLocal() as db:
            # چک کن که آیا قبلاً ست شده یا نه
            existing = db.query(database.models.SystemSettings).filter(
                database.models.SystemSettings.setting_key == "editor_access_delay_minutes"
            ).first()

            if not existing:
                database.crud.set_system_setting(
                    db,
                    "editor_access_delay_minutes",
                    "5",
                    "تاخیر دسترسی ادیتورها به فایل‌های جدید (به دقیقه)"
                )
                logger.info("✅ تنظیم editor_access_delay_minutes به 1 ست شد")
            else:
                logger.info(f"ℹ️ تنظیم editor_access_delay_minutes قبلاً ست شده: {existing.setting_value}")
    except Exception as e:
        logger.error(f"❌ خطا در مقداردهی تنظیمات اولیه: {e}")

# ============================================================
# 🟢 Main Function / تابع اصلی ربات
# ============================================================
def main() -> None:
    """تابع اصلی ربات."""
    logger.info("🚀 شروع راه‌اندازی ربات...")

    # حذف دیتابیس قبلی
    db_path = pathlib.Path('print3d_orders.db')
    if db_path.exists():
        try:
            os.remove(db_path)
            logger.info("✅ دیتابیس با موفقیت پاک شد")
        except Exception as e:
            logger.error(f"❌ خطا در حذف دیتابیس: {e}")

    # ایجاد دیتابیس
    database.connection.Base.metadata.create_all(database.connection.engine)
    logger.info("🗄️ دیتابیس ایجاد شد")

    # اطمینان از وجود صندوق تنخواه گردان
    with database.connection.SessionLocal() as db:
        database.crud.ensure_petty_cash_vault(db)
        logger.info("💰 صندوق تنخواه گردان بررسی/ایجاد شد")
        # مقداردهی تنظیمات پیش‌فرض
    initialize_default_settings()
    # ایجاد Application
    application = Application.builder().token(TOKEN).build()
    logger.info("📱 Application ایجاد شد")

    # ============================================================
    # 🟢 CONVERSATION HANDLERS
    # ============================================================

    # ConversationHandler های تنظیمات گروه
    application.add_handler(get_silver_settings_conversation())
    application.add_handler(get_gold_settings_conversation())
    logger.info("✅ ConversationHandler های گروه اضافه شدند")

    # Handler مدیریت رسیدها
    receipt_management_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_charge_from_receipt, pattern=r"^admin_charge_receipt_")
        ],
        states={
            RECEIPT_CHARGE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_receipt_charge_amount)
            ],
            RECEIPT_CHARGE_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_receipt_charge_description)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", lambda update, context: ConversationHandler.END)
        ],
        allow_reentry=True
    )
    application.add_handler(receipt_management_handler)
    logger.info("✅ Receipt management handler اضافه شد")

    # هندلر ارسال رسید کارت به کارت
    receipt_submission_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_receipt_submission, pattern=r"^submit_receipt$")
        ],
        states={
            RECEIPT_UPLOAD: [
                MessageHandler(filters.PHOTO, handle_receipt_photo),
                MessageHandler(filters.Regex(r'^/end$'), handle_end_command),
                CallbackQueryHandler(handle_finish_callback,
                                    pattern=r"^(finish_receipt_upload|cancel_receipt_submission)$")
            ],
            RECEIPT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_receipt_description),
                CallbackQueryHandler(handle_finish_callback, pattern=r"^cancel_receipt_submission$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_receipt_submission),
            MessageHandler(filters.Regex(r'^لغو$'), cancel_receipt_submission)
        ],
        allow_reentry=False
    )
    application.add_handler(receipt_submission_handler)
    logger.info("✅ Receipt submission handler اضافه شد")

    # هندلر مدیریت مشتریان
    customer_management_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_customers_list, pattern=r"^admin_customer_mgmt$"),
            MessageHandler(
                filters.Regex(r'^👥 مدیریت مشتریان$') & filters.User(user_id=ADMIN_ID),
                show_customers_list
            )
        ],
        states={
            "CUSTOMER_SELECTION": [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^(customer_mgmt_|cancel_customer_mgmt|back_to_customers_list)")
            ],
            "CUSTOMER_OPERATIONS": [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                CallbackQueryHandler(handle_customer_operations_callback,
                                    pattern=r"^(wallet_charge_|discount_charge_|set_work_price_|view_customer_transactions_|toggle_notification_|back_to_customers_list)")
            ],
            CUSTOMER_WALLET_AMOUNT: [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_wallet_amount)
            ],
            CUSTOMER_WALLET_DESC: [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_wallet_description)
            ],
            CUSTOMER_DISCOUNT_AMOUNT: [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_discount_amount)
            ],
            CUSTOMER_DISCOUNT_DESC: [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_discount_description)
            ],
            CUSTOMER_PRINT_PRICE: [
                CallbackQueryHandler(handle_customer_selection_callback,
                                    pattern=r"^customer_mgmt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_customer_print_price)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_customer_management),
            MessageHandler(filters.Regex(r'^لغو$'), cancel_customer_management)
        ],
        allow_reentry=True
    )
    application.add_handler(customer_management_handler)
    logger.info("✅ Customer management handler اضافه شد")

    # هندلر مدیریت کارکنان (ادیتور، اپراتور، ویزیتور)
    staff_management_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_staff_callbacks, pattern=r"^staff_(add_editor|add_operator|add_visitor)$")
        ],
        states={
            WAITING_STAFF_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID), receive_staff_id),
                CallbackQueryHandler(cancel_staff_add, pattern=r"^staff_menu$")
            ],
            WAITING_STAFF_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID), receive_staff_name),
                CommandHandler("skip", receive_staff_name)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_staff_add),
            CallbackQueryHandler(cancel_staff_add, pattern=r"^staff_menu$")
        ],
        allow_reentry=True
    )
    application.add_handler(staff_management_handler)
    logger.info("✅ Staff management handler اضافه شد")
    # هندلر ثبت‌نام
    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            GET_PHONE_NUMBER: [MessageHandler(filters.CONTACT, get_full_name)],
            GET_FULL_NAME: [MessageHandler(filters.TEXT & filters.Regex(r'^[\u0600-\u06FF\s\_]+$'), save_user_info)],
        },
        fallbacks=[MessageHandler(filters.Regex(r'^ثبت نام 📝$'), start_registration)],
    )
    application.add_handler(registration_handler)
    logger.info("✅ Registration handler اضافه شد")

    # هندلر صدور فاکتور
    invoice_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_customer_file_selection, pattern=r'^select_customer_\d+$'),
            CallbackQueryHandler(handle_customer_file_selection, pattern=r'^toggle_file_\d+$'),
            CallbackQueryHandler(handle_customer_file_selection, pattern=r'^issue_invoice_\d+$'),
            CallbackQueryHandler(handle_customer_file_selection, pattern=r'^back_to_customers_list$')
        ],
        states={
            GET_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight_handler)],
            GET_PHOTO: [MessageHandler(filters.PHOTO, get_photo_handler)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_invoice_handler),
            CallbackQueryHandler(cancel_invoice_handler, pattern=r'^back_to_operator_menu$')
        ],
    )
    application.add_handler(invoice_handler)
    logger.info("✅ Invoice handler اضافه شد")

    # هندلر تنظیم سقف دعوت
    set_referral_limit_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r'^تنظیم سقف دعوت ⚙️$') & filters.User(user_id=ADMIN_ID),
                                    set_referral_limit_start)],
        states={
            GET_USER_ID_TO_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_user_id_to_update_handler)],
            GET_NEW_REFERRAL_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_new_referral_limit_handler)]
        },
        fallbacks=[CommandHandler("cancel", cancel_handler)],
    )
    application.add_handler(set_referral_limit_handler)
    logger.info("✅ Referral limit handler اضافه شد")

    # تاخیر ادیتور
    editor_delay_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^⏰ تنظیم تاخیر دسترسی ادیتورها$") & filters.User(user_id=ADMIN_ID),
                start_editor_delay_setting
            )
        ],
        states={
            WAITING_EDITOR_DELAY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
                    save_editor_delay
                )
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_editor_delay_setting)
        ],
    )
    application.add_handler(editor_delay_conv)

    # تنظیمات زمان‌بندی تحویل
    delivery_scheduler_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_delivery_setup, pattern=r"^admin_delivery_schedule$")
        ],
        states={
            GET_DELIVERY_COUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
                    get_delivery_count
                )
            ],
            GET_CUTOFF_TIME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
                    get_cutoff_time
                )
            ],
            GET_OFFSET_HOURS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
                    get_offset_hours
                )
            ],
            GET_EDIT_DEADLINE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
                    get_edit_deadline
                )
            ],
        },
        fallbacks=[
            CommandHandler('cancel', cancel_delivery_setup),
            CallbackQueryHandler(cancel_delivery_setup, pattern=r"^admin_settings$")
        ],
        allow_reentry=True
    )
    application.add_handler(delivery_scheduler_conv)
    logger.info("✅ Delivery scheduler handler اضافه شد")

    # Vault conversation handlers
    vault_create_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_create_vault, pattern=r'^vault_create_new$')
        ],
        states={
            VAULT_CREATE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_vault_name)
            ],
            VAULT_CREATE_PERCENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_vault_percent_and_create)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_vault_operation)
        ],
        conversation_timeout=300
    )
    application.add_handler(vault_create_conv)

    vault_percent_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_set_percent, pattern=r'^vault_set_percent_\d+$')
        ],
        states={
            VAULT_SET_PERCENT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_vault_percent)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_vault_operation)
        ],
        conversation_timeout=300
    )
    application.add_handler(vault_percent_conv)

    vault_rename_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_rename_vault, pattern=r'^vault_rename_\d+$')
        ],
        states={
            VAULT_RENAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_vault_name_handler)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_vault_operation)
        ],
        conversation_timeout=300
    )
    application.add_handler(vault_rename_conv)

    expense_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_expense_record, pattern=r'^vault_record_expense$'),
            CallbackQueryHandler(get_expense_amount, pattern=r'^expense_vault_\d+$')
        ],
        states={
            EXPENSE_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_expense_description)
            ],
            EXPENSE_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, record_expense_final)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_vault_operation)
        ],
        conversation_timeout=300
    )
    application.add_handler(expense_conv)

    independent_income_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_independent_income, pattern=r'^vault_independent_income$')
        ],
        states={
            INCOME_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_income_amount)
            ],
            INCOME_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, record_independent_income)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_independent_income)
        ],
        conversation_timeout=300
    )
    application.add_handler(independent_income_conv)
    logger.info("✅ Independent income handler اضافه شد")

    gold_buy_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_buy_gold, pattern=r'^gold_buy_\d+$')
        ],
        states={
            GOLD_BUY_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_buy_weight)
            ],
            GOLD_BUY_PRICE_TOMAN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_buy_price_toman)
            ],
            GOLD_BUY_EXCHANGE_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_buy_exchange_rate)
            ],
            GOLD_BUY_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, execute_gold_buy)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_vault_operation)],
        conversation_timeout=300
    )
    application.add_handler(gold_buy_conv)

    gold_sell_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_sell_gold, pattern=r'^gold_sell_\d+$')
        ],
        states={
            GOLD_SELL_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_sell_weight)
            ],
            GOLD_SELL_PRICE_TOMAN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_sell_price_toman)
            ],
            GOLD_SELL_EXCHANGE_RATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_gold_sell_exchange_rate)
            ],
            GOLD_SELL_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, execute_gold_sell)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_vault_operation)],
        conversation_timeout=300
    )
    application.add_handler(gold_sell_conv)
    logger.info("✅ Gold conversation handlers اضافه شدند")

    petty_cash_withdraw_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_petty_cash_withdraw, pattern=r'^vault_petty_withdraw_\d+$')
        ],
        states={
            PETTY_CASH_WITHDRAW_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_petty_cash_withdraw_amount)
            ],
            PETTY_CASH_WITHDRAW_DESC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, execute_petty_cash_withdraw)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_vault_operation)
        ],
        conversation_timeout=300
    )
    application.add_handler(petty_cash_withdraw_conv)

    # ============================================================
    # 🔵 CALLBACK QUERY HANDLERS
    # ترتیب مهم است!
    # ============================================================

    # ✨ Broadcast Handlers - اولویت بالا
    application.add_handler(get_broadcast_conversation_handler())
    application.add_handler(CallbackQueryHandler(broadcast_start, pattern=r'^broadcast_main$'))
    application.add_handler(CallbackQueryHandler(show_broadcast_statistics, pattern=r'^broadcast_stats$'))
    application.add_handler(CallbackQueryHandler(show_broadcast_history, pattern=r'^broadcast_history'))
    application.add_handler(CallbackQueryHandler(show_broadcast_detail, pattern=r'^broadcast_view_'))
    application.add_handler(CallbackQueryHandler(show_broadcast_logs, pattern=r'^broadcast_logs_'))
    logger.info("✅ Broadcast handlers اضافه شدند")

    # Handler آرشیو فایل‌ها - بالاترین اولویت
    application.add_handler(CallbackQueryHandler(
        handle_archive_callback_unique,
        pattern=r"^ARCHIVE_"
    ))
    logger.info("✅ Archive callback handler اضافه شد")

    # Test handlers
    application.add_handler(CallbackQueryHandler(handle_test_callback, pattern="^test_show_expected_files$"))
    application.add_handler(CallbackQueryHandler(handle_test_main_menu, pattern="^test_main_menu$"))
    logger.info("✅ Test callback handlers اضافه شدند")

    # Editor handlers
    application.add_handler(CallbackQueryHandler(
        handle_editor_callbacks,
        pattern=r"^(editor_|no_files$)"
    ))
    logger.info("✅ Editor callback handlers اضافه شد")

    # Group settings
    application.add_handler(CallbackQueryHandler(show_group_settings_menu, pattern="^admin_group_settings$"))
    application.add_handler(CallbackQueryHandler(show_group_statistics, pattern="^admin_group_stats$"))
    application.add_handler(CallbackQueryHandler(reset_group_settings, pattern="^admin_group_reset$"))
    logger.info("✅ Group settings handlers اضافه شدند")

    # Holiday handlers
    application.add_handler(CallbackQueryHandler(show_holiday_calendar, pattern=r"^admin_holidays$"))
    application.add_handler(CallbackQueryHandler(toggle_holiday, pattern=r"^holiday_toggle_"))
    logger.info("✅ Admin holiday handlers اضافه شدند")

    # Staff management callbacks
    application.add_handler(CallbackQueryHandler(
        handle_staff_callbacks,
        pattern=r"^staff_"
    ))
    logger.info("✅ Staff management callbacks اضافه شد")

    # Operator handlers
    application.add_handler(CallbackQueryHandler(show_operator_main_menu, pattern=r"^operator_main_menu$"))
    application.add_handler(CallbackQueryHandler(show_operator_invoice_menu, pattern=r"^operator_invoice_menu$"))
    application.add_handler(CallbackQueryHandler(
        handle_operator_callbacks,
        pattern=r"^(operator_my_stats|operator_view_customers|operator_settings)$"
    ))
    logger.info("✅ Operator handlers اضافه شدند")

    # Operator files
    application.add_handler(CallbackQueryHandler(show_operator_files_main, pattern=r"^operator_files_main$"))
    application.add_handler(CallbackQueryHandler(show_delivery_customers, pattern=r"^operator_delivery_"))
    application.add_handler(CallbackQueryHandler(handle_group_stats_callbacks, pattern="^group_"))
    application.add_handler(CallbackQueryHandler(send_customer_files, pattern=r"^operator_send_customer_"))
    application.add_handler(CallbackQueryHandler(send_all_delivery_files, pattern=r"^operator_send_all_"))
    application.add_handler(CallbackQueryHandler(handle_no_files, pattern=r"^no_files$"))
    logger.info("✅ Operator files handlers اضافه شدند")

    # Vault menu
    application.add_handler(CallbackQueryHandler(show_vaults_menu, pattern=r"^admin_vaults_menu$"))
    logger.info("✅ Vaults menu handler اضافه شد")

    # Gold management
    application.add_handler(CallbackQueryHandler(show_gold_menu, pattern=r'^gold_menu_\d+$'))
    application.add_handler(CallbackQueryHandler(show_gold_balance, pattern=r'^gold_balance_\d+$'))
    application.add_handler(CallbackQueryHandler(show_gold_history, pattern=r'^gold_history_\d+$'))
    logger.info("✅ Gold menu handlers اضافه شدند")

    # Vault callbacks
    application.add_handler(CallbackQueryHandler(handle_vault_callbacks, pattern=r'^vault_'))
    application.add_handler(CallbackQueryHandler(handle_vault_callbacks, pattern=r'^expense_vault_'))
    logger.info("✅ Vault callback handlers اضافه شدند")

    # Admin settings
    application.add_handler(CallbackQueryHandler(
        handle_admin_settings_callbacks,
        pattern="^(admin_settings|admin_editor_delay)$"
    ))
    logger.info("✅ Admin settings specific handlers اضافه شد")

    # Admin inline
    application.add_handler(CallbackQueryHandler(
        handle_admin_callbacks,
        pattern=r"^(admin_|back_to_admin)"
    ))
    logger.info("✅ Admin inline handlers اضافه شدند")

    # Invoice navigation
    application.add_handler(CallbackQueryHandler(handle_invoice_navigation, pattern=r'^invoice_nav_'))

    # Transactions
    application.add_handler(CallbackQueryHandler(handle_transaction_callbacks, pattern="^trans_"))
    application.add_handler(CallbackQueryHandler(
        handle_admin_transaction_view,
        pattern="^view_customer_transactions_"
    ))
    logger.info("✅ Transaction handlers اضافه شدند")

    # Wallet
    application.add_handler(CallbackQueryHandler(
        handle_wallet_callbacks,
        pattern="^(wallet_|invoice_nav_|back_to_customer_menu|noop).*"
    ))
    logger.info("✅ Wallet handlers اضافه شدند")

    # General callback - باید در آخر باشد
    # فقط callback های مربوط به file submission
    application.add_handler(CallbackQueryHandler(
        handle_callback_query,
        pattern=r"^(cancel_order|edit_count|decrease_count|increase_count|show_count|confirm_count|cancel_count_edit|confirm_delete|back_to_initial)$"
    ))
    logger.info("✅ General callback handler اضافه شد")

    # Customer inline menu
    application.add_handler(CallbackQueryHandler(
        handle_customer_inline_callbacks,
        pattern=r"^customer_"
    ))
    logger.info("✅ Customer inline menu handlers اضافه شد")

    # ============================================================
    # 📨 MESSAGE HANDLERS
    # ============================================================

    # Admin command handlers
    application.add_handler(CommandHandler("admin", show_admin_main_menu, filters=filters.User(user_id=ADMIN_ID)))
    application.add_handler(CommandHandler("test", handle_test_command))
    application.add_handler(MessageHandler(
        filters.Regex(r'^(سلام|شروع|منو|menu|admin)') & filters.User(user_id=ADMIN_ID),
        show_admin_main_menu
    ))
    logger.info("✅ Admin message handlers اضافه شدند")
    application.add_handler(CommandHandler("setdelay", cmd_set_delay))

    # Editor message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^📝 منوی ادیتور') & filters.User(user_id=EDITORS_IDS),
        handle_editor_menu
    ))

    application.add_handler(MessageHandler(
        filters.Document.ALL & filters.User(user_id=EDITORS_IDS),
        handle_editor_file_upload
    ))
    logger.info("✅ Editor message handlers اضافه شد")

    # Operator message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^(📋|🔙) منوی اصلی') & filters.User(user_id=OPERATORS_IDS),
        handle_operator_menu
    ))

    application.add_handler(MessageHandler(
        filters.Regex(r'^📋 صدور فاکتور') & filters.User(user_id=OPERATORS_IDS),
        show_customers_for_invoice
    ))

    application.add_handler(MessageHandler(
        filters.Regex(r'^(📊 آمار کارهای من|👥 مشاهده مشتریان|⚙️ تنظیمات)') & filters.User(
            user_id=OPERATORS_IDS), handle_operator_menu))
    logger.info("✅ Operator message handlers اضافه شدند")

    # File handlers
    application.add_handler(MessageHandler(
        filters.Document.ALL & ~filters.User(user_id=EDITORS_IDS) & ~filters.COMMAND,
        handle_file
    ))
    application.add_handler(
        MessageHandler(filters.TEXT & filters.REPLY & ~filters.User(user_id=ADMIN_ID), handle_reply))
    logger.info("✅ File handlers اضافه شدند")

    # Customer message handlers
    # Customer message handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^🏠 منوی اصلی$') & ~filters.User(user_id=ADMIN_ID) & ~filters.User(user_id=OPERATORS_IDS),
        handle_customer_menu
    ))

    application.add_handler(MessageHandler(
        filters.Regex(
            r'^(💳 اعتبار و وضعیت سفارش‌ها|📂 آرشیو فایل‌ها|👥 زیرمجموعه‌ها|🧾 فاکتورها|💼 کیف پول و اعتبار و فاکتور|📊 آمار گروهی|🎁 دعوت و کسب اعتبار)$'
        ) & ~filters.User(user_id=ADMIN_ID) & ~filters.User(user_id=OPERATORS_IDS),
        handle_customer_menu
    ))

    logger.info("✅ Customer message handlers اضافه شدند")

    # Operator files command
    application.add_handler(CommandHandler(
        "files",
        operator_files_command,
        filters=filters.User(user_id=OPERATORS_IDS)
    ))
    logger.info("✅ Operator files command اضافه شد")

    logger.info("🎉 همه handlers اضافه شدند - Bot آماده است!")
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()