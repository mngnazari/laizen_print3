from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session, joinedload
import secrets
import string
from sqlalchemy import and_, desc, func
from . import models, schemas
from .models import User, FileOrder, ReferralCode, Invoice, SystemSettings, Holiday, DeliverySchedule, WalletTransaction
from telegram import Update
from telegram.ext import ContextTypes
import logging
from .models import Vault, VaultTransaction
from utils.timezone_utils import now_utc

logger = logging.getLogger(__name__)

def get_user(db: Session, user_id: int) -> Optional[User]:
    """دریافت کاربر بر اساس شناسه."""
    return db.query(User).filter(User.id == user_id).first()

def get_system_setting(db: Session, key: str, default_value: str = None) -> str:
    """دریافت تنظیمات سیستم."""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    return setting.setting_value if setting else default_value

def set_system_setting(db: Session, key: str, value: str, description: str = None) -> SystemSettings:
    """تنظیم مقادیر سیستم."""
    setting = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    if setting:
        setting.setting_value = value
        if description:
            setting.description = description
    else:
        setting = SystemSettings(
            setting_key=key,
            setting_value=value,
            description=description
        )
        db.add(setting)
    db.commit()
    return setting

def generate_customer_code(db: Session) -> str:
    """تولید کد اختصاری مشتری (c1, c2, c3, ...)."""
    last_number = get_system_setting(db, "last_customer_number", "0")
    next_number = int(last_number) + 1
    customer_code = f"c{next_number}"

    while db.query(User).filter(User.customer_code == customer_code).first():
        next_number += 1
        customer_code = f"c{next_number}"

    set_system_setting(db, "last_customer_number", str(next_number))
    return customer_code

def generate_unique_referral_code(db: Session) -> str:
    """تولید کد دعوت یکتا."""
    while True:
        code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        existing_user_code = db.query(User).filter(User.referral_code == code).first()
        existing_referral_code = db.query(ReferralCode).filter(ReferralCode.referral_code == code).first()
        if not existing_user_code and not existing_referral_code:
            return code

def get_referral_code_info(db: Session, referral_code: str) -> Optional[Dict]:
    """اطلاعات ارجاع‌دهنده را بر اساس کد دعوت برمی‌گرداند."""
    referral_code_obj = db.query(ReferralCode).filter(
        ReferralCode.referral_code == referral_code,
        ReferralCode.is_active == True
    ).first()

    if referral_code_obj:
        creator = db.query(User).filter(User.id == referral_code_obj.creator_id).first()
        if creator:
            if referral_code_obj.creator_role in ["admin", "editor", "visitor"]:
                return {'referrer_id': creator.id, 'is_admin_code': True}
            elif referral_code_obj.creator_role in ["customer", "operator"]:
                if creator.referrals_count < creator.max_referrals:
                    return {'referrer_id': creator.id, 'is_admin_code': False}
                else:
                    return {'referrer_id': creator.id, 'is_admin_code': False, 'quota_exceeded': True}

    user_referrer = db.query(User).filter(User.referral_code == referral_code).first()
    if user_referrer:
        if user_referrer.role in ["admin", "editor", "visitor"]:
            return {'referrer_id': user_referrer.id, 'is_admin_code': True}
        elif user_referrer.referrals_count < user_referrer.max_referrals:
            return {'referrer_id': user_referrer.id, 'is_admin_code': False}
        else:
            return {'referrer_id': user_referrer.id, 'is_admin_code': False, 'quota_exceeded': True}

    return None

def create_user(db: Session, user: schemas.UserCreate) -> User:
    """ایجاد کاربر جدید با کد اختصاری مشتری."""
    new_referral_code = generate_unique_referral_code(db)
    customer_code = generate_customer_code(db) if user.role == "customer" else None

    db_user = User(
        id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        customer_code=customer_code,
        referrer_id=user.referrer_id,
        referral_code=new_referral_code,
        role=user.role
    )
    db.add(db_user)

    if user.referrer_id:
        referrer = get_user(db, user.referrer_id)
        if referrer:
            referrer.referrals_count += 1
            referrer.discount_credit += 100.0

            if referrer.role in ["customer", "operator"] and referrer.referrals_count >= referrer.max_referrals:
                db.query(ReferralCode).filter(
                    ReferralCode.creator_id == referrer.id,
                    ReferralCode.creator_role.in_(["customer", "operator"])
                ).update({"is_active": False})
                referrer.referral_code = None

    db.commit()
    db.refresh(db_user)
    return db_user

def get_customers_with_pending_orders(db: Session) -> List[User]:
    """دریافت مشتریانی که سفارش pending دارند."""
    return db.query(User).join(FileOrder).filter(
        FileOrder.status == "pending",
        User.role == "customer"
    ).distinct().all()

def get_customer_pending_orders(db: Session, customer_id: int) -> List[FileOrder]:
    """دریافت سفارشات pending یک مشتری."""
    return db.query(FileOrder).filter(
        FileOrder.user_id == customer_id,
        FileOrder.status == "pending"
    ).all()

def create_invoice(db: Session, invoice_data: dict) -> Invoice:
    """ایجاد فاکتور جدید."""
    total_amount = invoice_data['weight_grams'] * invoice_data['price_per_gram']
    db_invoice = Invoice(
        customer_id=invoice_data['customer_id'],
        operator_id=invoice_data['operator_id'],
        file_order_id=invoice_data.get('file_order_id'),
        weight_grams=invoice_data['weight_grams'],
        price_per_gram=invoice_data['price_per_gram'],
        total_amount=total_amount,
        photo_file_id=invoice_data['photo_file_id']
    )
    db.add(db_invoice)

    if invoice_data.get('file_order_id'):
        db.query(FileOrder).filter(FileOrder.id == invoice_data['file_order_id']).update({
            "has_invoice": True,
            "status": "invoiced"
        })

    db.commit()
    db.refresh(db_invoice)
    return db_invoice

def get_customer_invoices(db: Session, customer_id: int) -> List[Invoice]:
    """دریافت فاکتورهای یک مشتری."""
    return db.query(Invoice).filter(
        Invoice.customer_id == customer_id
    ).order_by(desc(Invoice.created_at)).all()

def get_price_per_gram(db: Session) -> float:
    """دریافت قیمت هر گرم از تنظیمات."""
    price = get_system_setting(db, "price_per_gram", "10")
    return float(price)

def set_price_per_gram(db: Session, price: float) -> None:
    """تنظیم قیمت هر گرم."""
    set_system_setting(db, "price_per_gram", str(price), "قیمت هر گرم پرینت سه‌بعدی")

def update_user_max_referrals(db: Session, user_id: int, new_limit: int) -> Optional[User]:
    """به‌روزرسانی سقف دعوت‌های یک کاربر."""
    user = get_user(db, user_id)
    if user:
        old_limit = user.max_referrals
        user.max_referrals = new_limit

        if (new_limit > user.referrals_count and old_limit <= user.referrals_count and
                user.role in ["customer", "operator"]):
            db.query(ReferralCode).filter(
                ReferralCode.creator_id == user_id,
                ReferralCode.creator_role.in_(["customer", "operator"])
            ).update({"is_active": True})
            if not user.referral_code:
                user.referral_code = generate_unique_referral_code(db)

        db.commit()
        db.refresh(user)
        return user
    return None

def create_referral_code(db: Session, creator_id: int, creator_role: str, code: str = None) -> ReferralCode:
    """ایجاد کد دعوت جدید."""
    if not code:
        code = generate_unique_referral_code(db)

    existing_code = db.query(ReferralCode).filter(ReferralCode.referral_code == code).first()
    if existing_code:
        raise ValueError("این کد دعوت قبلاً وجود دارد")

    db_referral = ReferralCode(
        creator_id=creator_id,
        creator_role=creator_role,
        referral_code=code,
        is_active=True
    )
    db.add(db_referral)
    db.commit()
    db.refresh(db_referral)
    return db_referral

def create_admin_referral_code(db: Session, admin_id: int, code: str) -> ReferralCode:
    """ایجاد کد دعوت ادمین."""
    return create_referral_code(db, admin_id, "admin", code)

def create_customer_referral_code(db: Session, customer_id: int) -> ReferralCode:
    """تولید کد دعوت برای مشتری."""
    customer = get_user(db, customer_id)
    if not customer:
        raise ValueError("کاربر یافت نشد")

    if customer.role in ["customer", "operator"] and customer.referrals_count >= customer.max_referrals:
        raise ValueError("شما به سقف دعوت مجاز رسیده‌اید")

    return create_referral_code(db, customer_id, customer.role)

def get_user_referral_codes(db: Session, user_id: int) -> List[ReferralCode]:
    """دریافت تمام کدهای دعوت فعال یک کاربر."""
    return db.query(ReferralCode).filter(
        ReferralCode.creator_id == user_id,
        ReferralCode.is_active == True
    ).all()


def create_file_order(db: Session, file_order: schemas.FileOrderCreate) -> FileOrder:
    """ذخیره اطلاعات فایل ارسالی در دیتابیس."""
    try:
        file_order_data = {
            'user_id': file_order.user_id,
            'username': file_order.username,
            'file_id': file_order.file_id,
            'file_name': file_order.file_name,
            'file_size': file_order.file_size,
            'print_count': file_order.print_count,
            'description': file_order.description,
            'message_id': file_order.message_id,
            'delivery_datetime': file_order.delivery_datetime,
            'edit_deadline': file_order.edit_deadline
        }

        # اگر created_at داده شده، استفاده کن (باید UTC naive باشه)
        if hasattr(file_order, 'created_at') and file_order.created_at is not None:
            # حذف tzinfo اگر داشته باشه (فرض: مقدار UTC است)
            if hasattr(file_order.created_at, 'tzinfo') and file_order.created_at.tzinfo is not None:
                file_order_data['created_at'] = file_order.created_at.replace(tzinfo=None)
            else:
                file_order_data['created_at'] = file_order.created_at

        db_file = FileOrder(**file_order_data)
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        logger.info(f"FileOrder created successfully with id: {db_file.id}")
        return db_file

    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ایجاد FileOrder: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def get_file_order_by_id(db: Session, order_id: int) -> Optional[FileOrder]:
    """دریافت سفارش بر اساس ID."""
    return db.query(FileOrder).filter(FileOrder.id == order_id).first()

def update_file_order(db: Session, order_id: int, **kwargs) -> Optional[FileOrder]:
    """به‌روزرسانی سفارش."""
    order = get_file_order_by_id(db, order_id)
    if order:
        for key, value in kwargs.items():
            setattr(order, key, value)
        db.commit()
        db.refresh(order)
        return order
    return None

def get_all_users(db: Session) -> List[User]:
    """دریافت تمام کاربران از دیتابیس."""
    return db.query(User).all()

def get_orders_stats(db: Session) -> Dict[str, int]:
    """دریافت آمار سفارشات."""
    total_orders = db.query(FileOrder).count()
    confirmed_orders = db.query(FileOrder).filter(FileOrder.status == "confirmed").count()
    pending_orders = db.query(FileOrder).filter(FileOrder.status == "pending").count()
    cancelled_orders = db.query(FileOrder).filter(FileOrder.status == "cancelled").count()
    invoiced_orders = db.query(FileOrder).filter(FileOrder.status == "invoiced").count()

    return {
        'total': total_orders,
        'confirmed': confirmed_orders,
        'pending': pending_orders,
        'cancelled': cancelled_orders,
        'invoiced': invoiced_orders
    }

def add_admin_if_not_exists(db: Session, user_id: int, full_name: str = None, phone_number: str = None) -> User:
    """افزودن یا به‌روزرسانی ادمین."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user.role != "admin":
            user.role = "admin"
            db.commit()
            db.refresh(user)
        return user

    new_admin = User(
        id=user_id,
        full_name=full_name or "ادمین",
        phone_number=phone_number,
        role="admin"
    )
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

def add_operator_if_not_exists(db: Session, user_id: int, full_name: str, phone_number: Optional[str] = None) -> User:
    """افزودن یا به‌روزرسانی اپراتور."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user.role != "operator":
            user.role = "operator"
            db.commit()
            db.refresh(user)
        return user

    new_user = User(
        id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        role="operator"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def add_editor_if_not_exists(db: Session, user_id: int, full_name: str, phone_number: Optional[str] = None) -> User:
    """افزودن یا به‌روزرسانی ویرایشگر."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user.role != "editor":
            user.role = "editor"
            db.commit()
            db.refresh(user)
        return user

    new_user = User(
        id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        role="editor"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def add_visitor_if_not_exists(db: Session, user_id: int, full_name: str, phone_number: Optional[str] = None) -> User:
    """افزودن یا به‌روزرسانی بازدیدکننده."""
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if user.role != "visitor":
            user.role = "visitor"
            db.commit()
            db.refresh(user)
        return user

    new_user = User(
        id=user_id,
        full_name=full_name,
        phone_number=phone_number,
        role="visitor"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def get_customers(db: Session) -> List[User]:
    """دریافت لیست تمام مشتریان."""
    return db.query(User).filter(User.role == "customer").order_by(User.full_name).all()

def get_user_files_by_period(db: Session, user_id: int, days_back: int = None) -> List[FileOrder]:
    """دریافت فایل‌های کاربر در بازه زمانی مشخص."""
    query_filter = FileOrder.user_id == user_id
    if days_back:
        date_limit = datetime.now() - timedelta(days=days_back)
        query_filter = and_(query_filter, FileOrder.created_at >= date_limit)

    return db.query(FileOrder).filter(query_filter).order_by(FileOrder.created_at.asc()).all()

def get_user_files_count_by_period(db: Session, user_id: int, days_back: int = None) -> int:
    """شمارش فایل‌های کاربر در بازه زمانی مشخص."""
    query_filter = FileOrder.user_id == user_id
    if days_back:
        date_limit = datetime.now() - timedelta(days=days_back)
        query_filter = and_(query_filter, FileOrder.created_at >= date_limit)

    return db.query(FileOrder).filter(query_filter).count()

def get_user_files_grouped_by_date(db: Session, user_id: int, days_back: int = None) -> Dict[str, List[FileOrder]]:
    """دریافت فایل‌های کاربر گروه‌بندی شده بر اساس تاریخ."""
    files = get_user_files_by_period(db, user_id, days_back)
    grouped_files = defaultdict(list)
    for file_order in files:
        date_key = file_order.created_at.date().strftime('%Y-%m-%d')
        grouped_files[date_key].append(file_order)
    return dict(grouped_files)

def get_archive_statistics(db: Session, user_id: int) -> Dict[str, int]:
    """دریافت آمار کلی آرشیو فایل‌های کاربر."""
    now = datetime.now()
    weekly_count = get_user_files_count_by_period(db, user_id, 7)
    monthly_count = get_user_files_count_by_period(db, user_id, 30)
    total_count = get_user_files_count_by_period(db, user_id, None)
    all_files = get_user_files_by_period(db, user_id, None)

    return {
        'weekly': weekly_count,
        'monthly': monthly_count,
        'total': total_count,
        'pending': len([f for f in all_files if f.status == "pending"]),
        'confirmed': len([f for f in all_files if f.status == "confirmed"]),
        'cancelled': len([f for f in all_files if f.status == "cancelled"]),
        'invoiced': len([f for f in all_files if f.status == "invoiced"])
    }

def toggle_holiday_status(db: Session, date_str: str) -> Holiday:
    """تغییر وضعیت روز تعطیل/کاری."""
    holiday = db.query(Holiday).filter(Holiday.date == date_str).first()
    if holiday:
        holiday.is_holiday = not holiday.is_holiday
        holiday.updated_at = datetime.now()
    else:
        holiday = Holiday(date=date_str, is_holiday=True)
        db.add(holiday)

    db.commit()
    db.refresh(holiday)
    return holiday

def is_date_holiday(db: Session, date_str: str) -> bool:
    """بررسی آیا تاریخ مشخص شده تعطیل است یا خیر."""
    holiday = db.query(Holiday).filter(Holiday.date == date_str, Holiday.is_holiday == True).first()
    return holiday is not None

def get_holidays_in_range(db: Session, start_date: str, end_date: str) -> List[Holiday]:
    """دریافت تعطیلات در بازه زمانی مشخص."""
    return db.query(Holiday).filter(
        Holiday.date >= start_date,
        Holiday.date <= end_date,
        Holiday.is_holiday == True
    ).order_by(Holiday.date).all()

def clear_delivery_schedules(db: Session) -> None:
    """حذف تمام تنظیمات تحویل."""
    db.query(DeliverySchedule).delete()
    db.commit()

def save_delivery_schedule(db: Session, schedule_data: dict) -> DeliverySchedule:
    """ذخیره تنظیمات تحویل."""
    schedule = DeliverySchedule(
        delivery_number=schedule_data['delivery_number'],
        cutoff_time=schedule_data['cutoff_time'],
        cutoff_day_offset=schedule_data['cutoff_day_offset'],
        delivery_offset_hours=schedule_data['delivery_offset_hours']
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule

def get_active_delivery_schedules(db: Session) -> List[DeliverySchedule]:
    """دریافت تنظیمات فعال تحویل."""
    return db.query(DeliverySchedule).filter(DeliverySchedule.is_active == True).order_by(DeliverySchedule.delivery_number).all()

def get_delivery_schedule_count(db: Session) -> int:
    """تعداد تحویل‌های تنظیم شده در روز."""
    return db.query(DeliverySchedule).filter(DeliverySchedule.is_active == True).count()

def get_user_wallet_transactions(db: Session, user_id: int, limit: int = 50) -> List[WalletTransaction]:
    """دریافت تراکنش‌های کیف پول کاربر."""
    return db.query(WalletTransaction).filter(
        WalletTransaction.user_id == user_id
    ).order_by(desc(WalletTransaction.created_at)).limit(limit).all()

def create_wallet_transaction(db: Session, user_id: int, amount: float,
                             transaction_type: str, description: str,
                             admin_id: int = None) -> WalletTransaction:
    """ایجاد تراکنش کیف پول جدید."""
    transaction = WalletTransaction(
        user_id=user_id,
        admin_id=admin_id,
        amount=amount,
        transaction_type=transaction_type,
        description=description
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction

def update_user_wallet_balance(db: Session, user_id: int, amount: float,
                               description: str, admin_id: int = None,
                               receipt_id: int = None) -> Optional[User]:
    """بروزرسانی موجودی کیف پول کاربر با ثبت تراکنش و تخصیص به صندوق‌ها"""
    logger.info(f"update_user_wallet_balance called - user_id: {user_id}, amount: {amount}, receipt_id: {receipt_id}")

    user = get_user(db, user_id)
    if not user:
        logger.error(f"User {user_id} not found")
        return None

    if amount < 0 and user.wallet_balance + amount < 0:
        raise ValueError(f"موجودی کافی نیست. موجودی فعلی: ${user.wallet_balance:.2f}")

    # بروزرسانی موجودی
    user.wallet_balance += amount
    logger.info(f"User balance updated: {user.wallet_balance}")

    # ثبت تراکنش کیف پول
    create_wallet_transaction(
        db=db,
        user_id=user_id,
        amount=amount,
        transaction_type="admin_adjustment",
        description=description,
        admin_id=admin_id
    )
    logger.info("Wallet transaction created")

    # اگر شارژ بود (مثبت) و receipt_id داریم، به صندوق‌ها تخصیص بده
    if amount > 0:
        logger.info(f"Amount is positive, checking receipt_id: {receipt_id}")

        if receipt_id:
            try:
                # اطمینان از وجود تنخواه
                ensure_petty_cash_vault(db)
                logger.info("Petty cash ensured")

                # تخصیص به صندوق‌ها
                transactions = allocate_receipt_to_vaults(
                    db=db,
                    receipt_amount=amount,
                    receipt_id=receipt_id,
                    admin_id=admin_id
                )
                logger.info(f"✅ مبلغ ${amount} به صندوق‌ها تخصیص یافت - {len(transactions)} تراکنش ایجاد شد")
            except Exception as e:
                logger.error(f"❌ خطا در تخصیص به صندوق‌ها: {e}", exc_info=True)
        else:
            logger.warning(f"⚠️ receipt_id is None - مبلغ ${amount} به صندوق‌ها تخصیص نیافت")

    db.commit()
    db.refresh(user)
    logger.info("Transaction completed successfully")
    return user

def update_user_discount_credit(db: Session, user_id: int, amount: float,
                               description: str, admin_id: int = None) -> Optional[User]:
    """بروزرسانی اعتبار تخفیف کاربر."""
    user = get_user(db, user_id)
    if not user:
        return None

    if amount < 0 and user.discount_credit + amount < 0:
        raise ValueError(f"اعتبار تخفیف کافی نیست. اعتبار فعلی: ${user.discount_credit:.2f}")

    user.discount_credit += amount
    create_wallet_transaction(
        db=db,
        user_id=user_id,
        amount=amount,
        transaction_type="discount_credit_adjustment",
        description=description,
        admin_id=admin_id
    )

    db.commit()
    db.refresh(user)
    return user

def update_user_print_price(db: Session, user_id: int, new_price: float) -> Optional[User]:
    """تنظیم قیمت پرینت اختصاصی برای کاربر."""
    user = get_user(db, user_id)
    if not user:
        return None

    if not hasattr(user, 'print_price_per_gram'):
        pass

    user.print_price_per_gram = new_price
    db.commit()
    db.refresh(user)
    return user

def check_user_balance_sufficient(db: Session, user_id: int, amount: float, balance_type: str = "wallet") -> bool:
    """بررسی کافی بودن موجودی کاربر."""
    user = get_user(db, user_id)
    if not user:
        return False

    if balance_type == "wallet":
        return user.wallet_balance >= abs(amount)
    elif balance_type == "discount":
        return user.discount_credit >= abs(amount)
    return False

async def get_customer_discount_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت مبلغ شارژ/تسویه اعتبار تخفیف."""
    try:
        amount = float(update.message.text)
        customer_id = context.user_data.get('selected_customer_id')
        context.user_data['amount'] = amount

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)

            if amount < 0 and customer.discount_credit + amount < 0:
                await update.message.reply_text(
                    f"❌ **خطا در مبلغ**\n\n"
                    f"اعتبار تخفیف فعلی: ${customer.discount_credit:.2f}\n"
                    f"مبلغ درخواستی: ${amount:.2f}\n"
                    f"اعتبار جدید: ${customer.discount_credit + amount:.2f}\n\n"
                    f"اعتبار تخفیف نمی‌تواند منفی شود!\n"
                    f"لطفاً مبلغ کمتری وارد کنید.",
                    parse_mode="Markdown"
                )
                return CUSTOMER_DISCOUNT_AMOUNT

            operation_type = "شارژ" if amount > 0 else "تسویه/کسر از"
            await update.message.reply_text(
                f"🎁 **{operation_type} اعتبار تخفیف {customer.full_name}**\n\n"
                f"مبلغ: ${abs(amount):.2f}\n"
                f"اعتبار فعلی: ${customer.discount_credit:.2f}\n"
                f"اعتبار جدید: ${customer.discount_credit + amount:.2f}\n\n"
                f"لطفاً علت/توضیح این تراکنش را وارد کنید:",
                parse_mode="Markdown"
            )
        return CUSTOMER_DISCOUNT_DESC

    except ValueError:
        await update.message.reply_text(
            "❌ لطفاً یک عدد معتبر وارد کنید.\n"
            "مثال: 50 یا -25 یا 12.5"
        )
        return CUSTOMER_DISCOUNT_AMOUNT

async def get_customer_discount_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت توضیحات و اجرای تراکنش اعتبار تخفیف."""
    description = update.message.text.strip()

    if not description:
        await update.message.reply_text("❌ لطفاً توضیح تراکنش را وارد کنید.")
        return CUSTOMER_DISCOUNT_DESC

    customer_id = context.user_data.get('selected_customer_id')
    amount = context.user_data['amount']
    admin_id = update.effective_user.id

    try:
        with database.connection.SessionLocal() as db:
            updated_customer = database.crud.update_user_discount_credit(
                db, customer_id, amount, description, admin_id
            )

            if updated_customer:
                operation_type = "شارژ شد" if amount > 0 else "کسر شد"
                operation_emoji = "➕" if amount > 0 else "➖"

                await update.message.reply_text(
                    f"✅ **تراکنش با موفقیت انجام شد!**\n\n"
                    f"👤 مشتری: {updated_customer.full_name}\n"
                    f"🎁 مبلغ: ${abs(amount):.2f} {operation_type}\n"
                    f"📝 توضیح: {description}\n"
                    f"💎 اعتبار تخفیف جدید: ${updated_customer.discount_credit:.2f}\n\n"
                    f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
                    parse_mode="Markdown"
                )

                try:
                    await context.bot.send_message(
                        chat_id=customer_id,
                        text=f"🎁 **تغییر اعتبار تخفیف** {operation_emoji}\n\n"
                             f"مبلغ: ${abs(amount):.2f}\n"
                             f"توضیح: {description}\n"
                             f"اعتبار جدید: ${updated_customer.discount_credit:.2f}\n"
                             f"تاریخ: {get_persian_datetime()}",
                        parse_mode="Markdown"
                    )
                except:
                    pass

            else:
                await update.message.reply_text("❌ خطا در انجام تراکنش.")

    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)}")
        return CUSTOMER_DISCOUNT_DESC

    context.user_data.clear()
    return ConversationHandler.END

async def get_customer_print_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت قیمت جدید پرینت."""
    try:
        new_price = float(update.message.text)

        if new_price <= 0:
            await update.message.reply_text("❌ قیمت باید عددی مثبت باشد. لطفاً دوباره تلاش کنید.")
            return CUSTOMER_PRINT_PRICE

        customer_id = context.user_data.get('selected_customer_id')

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            database.crud.set_price_per_gram(db, new_price)

            await update.message.reply_text(
                f"✅ **قیمت پرینت تنظیم شد!**\n\n"
                f"👤 مشتری: {customer.full_name}\n"
                f"💳 قیمت جدید: ${new_price:.2f} در هر گرم\n\n"
                f"📱 اطلاع‌رسانی به مشتری ارسال شد.",
                parse_mode="Markdown"
            )

            try:
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=f"💳 **اطلاع‌رسانی تغییر قیمت**\n\n"
                         f"قیمت پرینت شما به ${new_price:.2f} در هر گرم تغییر یافت.\n"
                         f"تاریخ: {get_persian_datetime()}",
                    parse_mode="Markdown"
                )
            except:
                pass

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید.")
        return CUSTOMER_PRINT_PRICE

    context.user_data.clear()
    return ConversationHandler.END

# اضافه کردن این توابع به آخر فایل database/crud.py

def create_receipt(db: Session, user_id: int, file_id: str,
                  file_name: str = None, file_size: int = None,
                  description: str = None) -> models.Receipt:
    """ایجاد رسید جدید"""
    receipt = models.Receipt(
        user_id=user_id,
        file_id=file_id,
        file_name=file_name,
        file_size=file_size,
        description=description,
        status="pending"
    )
    db.add(receipt)
    db.commit()
    db.refresh(receipt)
    return receipt


def get_user_receipts(db: Session, user_id: int, limit: int = 50) -> List[models.Receipt]:
    """دریافت رسیدهای کاربر"""
    return db.query(models.Receipt).filter(
        models.Receipt.user_id == user_id
    ).order_by(desc(models.Receipt.created_at)).limit(limit).all()


def get_pending_receipts(db: Session, limit: int = 100) -> List[models.Receipt]:
    """دریافت رسیدهای در انتظار بررسی"""
    return db.query(models.Receipt).filter(
        models.Receipt.status == "pending"
    ).order_by(models.Receipt.created_at).limit(limit).all()


def update_receipt_status(db: Session, receipt_id: int, status: str,
                         admin_id: int = None, admin_notes: str = None) -> models.Receipt:
    """بروزرسانی وضعیت رسید توسط ادمین"""
    receipt = db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()
    if receipt:
        receipt.status = status
        receipt.reviewed_by = admin_id
        receipt.reviewed_at = datetime.now()
        if admin_notes:
            receipt.admin_notes = admin_notes
        db.commit()
        db.refresh(receipt)
    return receipt


def get_receipt_by_id(db: Session, receipt_id: int) -> models.Receipt:
    """دریافت رسید بر اساس ID"""
    return db.query(models.Receipt).filter(models.Receipt.id == receipt_id).first()

# اضافه کردن این توابع به آخر فایل database/crud.py

def get_unconfirmed_receipts(db: Session) -> List[models.Receipt]:
    """دریافت رسیدهای تایید نشده"""
    return db.query(models.Receipt).options(joinedload(models.Receipt.user)).filter(
        models.Receipt.status == "pending"
    ).order_by(models.Receipt.created_at).all()

def count_unconfirmed_receipts(db: Session) -> int:
    """شمارش رسیدهای تایید نشده"""
    return db.query(models.Receipt).filter(
        models.Receipt.status == "pending"
    ).count()

def get_receipt(db: Session, receipt_id: int) -> models.Receipt:
    """دریافت رسید با لود کردن اطلاعات کاربر"""
    return db.query(models.Receipt).options(joinedload(models.Receipt.user)).filter(
        models.Receipt.id == receipt_id
    ).first()

def confirm_receipt(db: Session, receipt_id: int, admin_id: int) -> models.Receipt:
    """تایید رسید"""
    return update_receipt_status(db, receipt_id, "approved", admin_id)

def reject_receipt(db: Session, receipt_id: int, admin_id: int, reason: str = None) -> models.Receipt:
    """رد رسید"""
    return update_receipt_status(db, receipt_id, "rejected", admin_id, reason)


def get_pending_files_by_delivery_time(db: Session, delivery_time_pattern: str) -> List[FileOrder]:
    """دریافت فایل‌های pending برای یک زمان تحویل"""
    return db.query(FileOrder).filter(
        FileOrder.status == "pending",
        FileOrder.sent_to_operator == False,
        FileOrder.delivery_datetime.like(f"{delivery_time_pattern}%")
    ).options(joinedload(FileOrder.user)).all()


def get_pending_files_by_customer_and_delivery(db: Session, customer_code: str, delivery_time_pattern: str) -> List[
    FileOrder]:
    """دریافت فایل‌های pending برای مشتری و زمان تحویل خاص"""
    return db.query(FileOrder).join(User).filter(
        FileOrder.status == "pending",
        FileOrder.sent_to_operator == False,
        FileOrder.delivery_datetime.like(f"{delivery_time_pattern}%"),
        User.customer_code == customer_code
    ).options(joinedload(FileOrder.user)).all()


def mark_files_as_sent_to_operator(db: Session, file_ids: List[int], operator_filenames: dict = None):
    """علامت‌گذاری فایل‌ها به عنوان ارسال شده به اپراتور"""
    from datetime import datetime

    for file_id in file_ids:
        file_order = db.query(FileOrder).filter(FileOrder.id == file_id).first()
        if file_order:
            file_order.sent_to_operator = True
            file_order.sent_to_operator_at = datetime.now()
            if operator_filenames and file_id in operator_filenames:
                file_order.operator_filename = operator_filenames[file_id]

    db.commit()


def get_files_statistics(db: Session) -> dict:
    """آمار کلی فایل‌ها"""
    total_files = db.query(FileOrder).count()
    pending_files = db.query(FileOrder).filter(FileOrder.status == "pending").count()
    sent_to_operator = db.query(FileOrder).filter(FileOrder.sent_to_operator == True).count()

    return {
        'total': total_files,
        'pending': pending_files,
        'sent_to_operator': sent_to_operator,
        'ready_for_operator': db.query(FileOrder).filter(
            FileOrder.status == "pending",
            FileOrder.sent_to_operator == False
        ).count()
    }


# ==================== مدیریت صندوق‌ها ====================

def get_all_vaults(db: Session) -> List[Vault]:
    """دریافت تمام صندوق‌های فعال"""
    return db.query(Vault).filter(Vault.is_active == True).order_by(Vault.name).all()


def get_vault_by_id(db: Session, vault_id: int) -> Optional[Vault]:
    """دریافت صندوق بر اساس ID"""
    return db.query(Vault).filter(Vault.id == vault_id).first()


def get_total_allocation_percentage(db: Session, exclude_vault_id: int = None) -> float:
    """محاسبه مجموع درصد تخصیص صندوق‌ها (بدون تنخواه)"""
    petty_cash = db.query(Vault).filter(
        Vault.name == "تنخواه گردان",
        Vault.is_active == True
    ).first()

    query = db.query(func.sum(Vault.allocation_percentage)).filter(Vault.is_active == True)

    # حذف تنخواه از محاسبه
    if petty_cash:
        query = query.filter(Vault.id != petty_cash.id)

    if exclude_vault_id:
        query = query.filter(Vault.id != exclude_vault_id)

    result = query.scalar()
    return result if result else 0.0


def create_vault(db: Session, name: str, allocation_percentage: float = 0.0) -> Optional[Vault]:
    """ایجاد صندوق جدید"""
    # اطمینان از وجود تنخواه
    ensure_petty_cash_vault(db)

    # بررسی محدودیت 100 درصد
    current_total = get_total_allocation_percentage(db)

    if current_total + allocation_percentage > 100:
        raise ValueError(f"مجموع درصد تخصیص نمی‌تواند بیشتر از 100% باشد. "
                         f"درصد فعلی: {current_total}%، درصد درخواستی: {allocation_percentage}%")

    vault = Vault(
        name=name,
        balance=0.0,
        allocation_percentage=allocation_percentage
    )
    db.add(vault)
    db.commit()
    db.refresh(vault)

    # بروزرسانی درصد تنخواه
    update_petty_cash_percentage(db)

    return vault




def update_vault_allocation(db: Session, vault_id: int, new_percentage: float) -> Optional[Vault]:
    """بروزرسانی درصد تخصیص صندوق"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        return None

    # جلوگیری از تغییر دستی درصد تنخواه
    if vault.name == "تنخواه گردان":
        raise ValueError("درصد تنخواه گردان به صورت خودکار محاسبه می‌شود و قابل تغییر نیست")

    # بررسی محدودیت 100 درصد (بدون احتساب صندوق فعلی)
    current_total = get_total_allocation_percentage(db, exclude_vault_id=vault_id)

    if current_total + new_percentage > 100:
        raise ValueError(f"مجموع درصد تخصیص نمی‌تواند بیشتر از 100% باشد. "
                         f"درصد سایر صندوق‌ها: {current_total}%، درصد درخواستی: {new_percentage}%")

    vault.allocation_percentage = new_percentage
    db.commit()
    db.refresh(vault)

    # بروزرسانی درصد تنخواه
    update_petty_cash_percentage(db)

    return vault

def update_vault_name(db: Session, vault_id: int, new_name: str) -> Optional[Vault]:
    """تغییر نام صندوق"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        return None

    vault.name = new_name
    db.commit()
    db.refresh(vault)
    return vault


def delete_vault(db: Session, vault_id: int) -> bool:
    """حذف صندوق (فقط اگر موجودی نقد و طلا هر دو صفر باشند)"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        return False

    # جلوگیری از حذف تنخواه گردان
    if vault.name == "تنخواه گردان":
        raise ValueError("صندوق تنخواه گردان قابل حذف نیست")

    if vault.balance != 0:
        raise ValueError(f"نمی‌توان صندوق با موجودی نقد غیرصفر را حذف کرد. "
                         f"موجودی نقد فعلی: ${vault.balance:.2f}")

    if vault.gold_balance != 0:
        raise ValueError(f"نمی‌توان صندوق با موجودی طلا غیرصفر را حذف کرد. "
                         f"موجودی طلا فعلی: {vault.gold_balance:.3f} گرم")

    vault.is_active = False
    db.commit()

    # بروزرسانی درصد تنخواه
    update_petty_cash_percentage(db)

    return True


# ==================== تراکنش‌های صندوق ====================


def create_vault_transaction(db: Session, vault_id: int, amount: float,
                             transaction_type: str, description: str,
                             receipt_id: int = None, created_by: int = None) -> VaultTransaction:
    """ایجاد تراکنش صندوق"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        raise ValueError("صندوق یافت نشد")

    # چک موجودی حذف شد - صندوق می‌تواند منفی شود

    # ایجاد تراکنش
    transaction = VaultTransaction(
        vault_id=vault_id,
        amount=amount,
        transaction_type=transaction_type,
        description=description,
        receipt_id=receipt_id,
        created_by=created_by
    )
    db.add(transaction)

    # بروزرسانی موجودی صندوق
    vault.balance += amount

    db.commit()
    db.refresh(transaction)
    db.refresh(vault)  # این خط رو اضافه کنید

    return transaction
def get_vault_transactions(db: Session, vault_id: int, limit: int = 50) -> List[VaultTransaction]:
    """دریافت تراکنش‌های یک صندوق"""
    return db.query(VaultTransaction).filter(
        VaultTransaction.vault_id == vault_id
    ).order_by(desc(VaultTransaction.created_at)).limit(limit).all()


def allocate_receipt_to_vaults(db: Session, receipt_amount: float, receipt_id: int, admin_id: int) -> List[
    VaultTransaction]:
    """تخصیص خودکار مبلغ رسید به صندوق‌ها بر اساس درصدها"""
    vaults = get_all_vaults(db)
    transactions = []

    print(f"DEBUG allocate - receipt_amount: {receipt_amount}, receipt_id: {receipt_id}")
    print(f"DEBUG allocate - تعداد صندوق‌ها: {len(vaults)}")

    for vault in vaults:
        print(f"DEBUG allocate - صندوق {vault.name}: {vault.allocation_percentage}%")
        if vault.allocation_percentage > 0:
            allocated_amount = (receipt_amount * vault.allocation_percentage) / 100
            print(f"DEBUG allocate - مبلغ تخصیص: ${allocated_amount}")

            transaction = create_vault_transaction(
                db=db,
                vault_id=vault.id,
                amount=allocated_amount,
                transaction_type="auto_allocation",
                description=f"تخصیص خودکار از رسید #{receipt_id} ({vault.allocation_percentage}% از ${receipt_amount:.2f})",
                receipt_id=receipt_id,
                created_by=admin_id
            )
            transactions.append(transaction)
            print(f"DEBUG allocate - تراکنش ایجاد شد: {transaction.id}")

    print(f"DEBUG allocate - تعداد تراکنش‌ها: {len(transactions)}")
    return transactions

def record_vault_expense(db: Session, vault_id: int, amount: float,
                         description: str, admin_id: int) -> VaultTransaction:
    """ثبت هزینه (برداشت از صندوق)"""
    if amount > 0:
        amount = -amount  # تبدیل به منفی برای برداشت

    return create_vault_transaction(
        db=db,
        vault_id=vault_id,
        amount=amount,
        transaction_type="manual_expense",
        description=description,
        created_by=admin_id
    )


def get_vaults_summary(db: Session) -> dict:
    """خلاصه آمار صندوق‌ها"""
    vaults = get_all_vaults(db)
    total_balance = sum(v.balance for v in vaults)
    total_percentage = sum(v.allocation_percentage for v in vaults)

    return {
        'total_vaults': len(vaults),
        'total_balance': total_balance,
        'total_allocated_percentage': total_percentage,
        'remaining_percentage': 100 - total_percentage
    }


def ensure_petty_cash_vault(db: Session) -> Vault:
    """اطمینان از وجود صندوق تنخواه گردان"""
    # جستجوی صندوق تنخواه
    petty_cash = db.query(Vault).filter(
        Vault.name == "تنخواه گردان",
        Vault.is_active == True
    ).first()

    if not petty_cash:
        # ایجاد صندوق تنخواه با درصد 100
        petty_cash = Vault(
            name="تنخواه گردان",
            balance=0.0,
            allocation_percentage=100.0,
            is_active=True
        )
        db.add(petty_cash)
        db.commit()
        db.refresh(petty_cash)

    return petty_cash


def update_petty_cash_percentage(db: Session):
    """بروزرسانی درصد تنخواه گردان بر اساس سایر صندوق‌ها"""
    petty_cash = ensure_petty_cash_vault(db)

    # محاسبه مجموع درصد سایر صندوق‌ها (به جز تنخواه)
    other_vaults_total = db.query(func.sum(Vault.allocation_percentage)).filter(
        Vault.is_active == True,
        Vault.id != petty_cash.id
    ).scalar() or 0.0

    # درصد تنخواه = 100 - مجموع بقیه
    petty_cash.allocation_percentage = 100.0 - other_vaults_total
    db.commit()
    db.refresh(petty_cash)

    return petty_cash


def withdraw_from_petty_cash(db: Session, amount: float, description: str, admin_id: int):
    """برداشت از تنخواه و توزیع بین صندوق‌ها (فقط وقتی درصد تنخواه = 0)"""
    petty_cash = ensure_petty_cash_vault(db)

    # بررسی درصد تنخواه
    if petty_cash.allocation_percentage != 0:
        raise ValueError(f"برداشت از تنخواه فقط زمانی مجاز است که درصد تخصیص آن صفر باشد. "
                         f"درصد فعلی: {petty_cash.allocation_percentage}%")

    # بررسی موجودی کافی
    if petty_cash.balance < amount:
        raise ValueError(f"موجودی تنخواه کافی نیست. "
                         f"موجودی فعلی: ${petty_cash.balance:.2f}")

    # برداشت از تنخواه
    create_vault_transaction(
        db=db,
        vault_id=petty_cash.id,
        amount=-amount,
        transaction_type="withdraw_for_distribution",
        description=f"برداشت برای توزیع بین صندوق‌ها: {description}",
        created_by=admin_id
    )

    # توزیع بین سایر صندوق‌ها
    other_vaults = db.query(Vault).filter(
        Vault.is_active == True,
        Vault.id != petty_cash.id
    ).all()

    total_percentage = sum(v.allocation_percentage for v in other_vaults)

    if total_percentage == 0:
        raise ValueError("هیچ صندوق دیگری برای توزیع وجود ندارد")

    transactions = []
    for vault in other_vaults:
        if vault.allocation_percentage > 0:
            allocated_amount = (amount * vault.allocation_percentage) / total_percentage

            transaction = create_vault_transaction(
                db=db,
                vault_id=vault.id,
                amount=allocated_amount,
                transaction_type="petty_cash_distribution",
                description=f"توزیع از تنخواه ({vault.allocation_percentage / total_percentage * 100:.1f}%): {description}",
                created_by=admin_id
            )
            transactions.append(transaction)

    return transactions


from .models import VaultGoldTransaction


# ==================== مدیریت دارایی طلای صندوق‌ها ====================

def buy_gold_for_vault(db: Session, vault_id: int, gold_weight: float,
                       price_per_gram_dollar: float, price_per_gram_toman: float,
                       description: str, admin_id: int):
    """خرید طلا برای صندوق (کاهش نقد، افزایش طلا) - موجودی می‌تواند منفی شود"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        raise ValueError("صندوق یافت نشد")

    total_amount = gold_weight * price_per_gram_dollar

    # حذف چک موجودی - اجازه منفی شدن

    # کاهش موجودی نقد
    vault.balance -= total_amount

    # افزایش موجودی طلا
    vault.gold_balance += gold_weight

    # ثبت تراکنش نقدی (برداشت)
    create_vault_transaction(
        db=db,
        vault_id=vault_id,
        amount=-total_amount,
        transaction_type="gold_purchase",
        description=f"خرید {gold_weight} گرم طلا - {description}",
        created_by=admin_id
    )

    # ثبت معامله طلا
    gold_transaction = VaultGoldTransaction(
        vault_id=vault_id,
        transaction_type="buy",
        gold_weight_grams=gold_weight,
        price_per_gram_dollar=price_per_gram_dollar,
        price_per_gram_toman=price_per_gram_toman,
        total_amount=total_amount,
        description=description,
        created_by=admin_id
    )
    db.add(gold_transaction)

    db.commit()
    db.refresh(vault)
    db.refresh(gold_transaction)

    return gold_transaction


def sell_gold_from_vault(db: Session, vault_id: int, gold_weight: float,
                         price_per_gram_dollar: float, price_per_gram_toman: float,
                         description: str, admin_id: int):
    """فروش طلا از صندوق (کاهش طلا، افزایش نقد)"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        raise ValueError("صندوق یافت نشد")

    # بررسی موجودی طلا کافی - این چک باقی بمونه
    if vault.gold_balance < gold_weight:
        raise ValueError(f"موجودی طلا کافی نیست. موجودی فعلی: {vault.gold_balance:.3f} گرم")

    total_amount = gold_weight * price_per_gram_dollar

    # کاهش موجودی طلا
    vault.gold_balance -= gold_weight

    # افزایش موجودی نقد
    vault.balance += total_amount

    # ثبت تراکنش نقدی (واریز)
    create_vault_transaction(
        db=db,
        vault_id=vault_id,
        amount=total_amount,
        transaction_type="gold_sale",
        description=f"فروش {gold_weight} گرم طلا - {description}",
        created_by=admin_id
    )

    # ثبت معامله طلا
    gold_transaction = VaultGoldTransaction(
        vault_id=vault_id,
        transaction_type="sell",
        gold_weight_grams=gold_weight,
        price_per_gram_dollar=price_per_gram_dollar,
        price_per_gram_toman=price_per_gram_toman,
        total_amount=total_amount,
        description=description,
        created_by=admin_id
    )
    db.add(gold_transaction)

    db.commit()
    db.refresh(vault)
    db.refresh(gold_transaction)

    return gold_transaction


def get_vault_gold_transactions(db: Session, vault_id: int, limit: int = 50) -> List[VaultGoldTransaction]:
    """دریافت تاریخچه معاملات طلای یک صندوق"""
    return db.query(VaultGoldTransaction).filter(
        VaultGoldTransaction.vault_id == vault_id
    ).order_by(desc(VaultGoldTransaction.created_at)).limit(limit).all()


def get_vault_gold_summary(db: Session, vault_id: int, current_gold_price: float = None) -> dict:
    """خلاصه اطلاعات دارایی طلای صندوق"""
    vault = get_vault_by_id(db, vault_id)
    if not vault:
        return None

    transactions = get_vault_gold_transactions(db, vault_id, limit=1000)

    total_bought = sum(t.gold_weight_grams for t in transactions if t.transaction_type == "buy")
    total_sold = sum(t.gold_weight_grams for t in transactions if t.transaction_type == "sell")

    total_buy_cost = sum(t.total_amount for t in transactions if t.transaction_type == "buy")
    total_sell_revenue = sum(t.total_amount for t in transactions if t.transaction_type == "sell")

    # محاسبه میانگین قیمت خرید
    avg_buy_price = total_buy_cost / total_bought if total_bought > 0 else 0

    # محاسبه سود/زیان
    profit_loss = None
    if current_gold_price and vault.gold_balance > 0:
        current_value = vault.gold_balance * current_gold_price
        purchase_value = vault.gold_balance * avg_buy_price
        profit_loss = current_value - purchase_value

    return {
        'current_balance_grams': vault.gold_balance,
        'total_bought': total_bought,
        'total_sold': total_sold,
        'total_buy_cost': total_buy_cost,
        'total_sell_revenue': total_sell_revenue,
        'avg_buy_price': avg_buy_price,
        'profit_loss': profit_loss,
        'transaction_count': len(transactions)
    }


# این تابع را به انتهای فایل database/crud.py اضافه کنید:

def allocate_independent_income_to_vaults(db: Session, income_amount: float,
                                          description: str, admin_id: int) -> List[VaultTransaction]:
    """
    تخصیص درآمد مستقل (خارج از شارژ حساب مشتری) به صندوق‌ها
    این تابع درآمد را بدون نیاز به رسید، مستقیماً به صندوق‌ها اختصاص می‌دهد

    Args:
        db: Session دیتابیس
        income_amount: مبلغ درآمد (دلار)
        description: توضیحات درآمد
        admin_id: شناسه ادمین ثبت‌کننده

    Returns:
        لیست تراکنش‌های ایجاد شده برای هر صندوق
    """
    vaults = get_all_vaults(db)
    transactions = []

    logger.info(f"DEBUG allocate_independent_income - income_amount: {income_amount}")
    logger.info(f"DEBUG allocate_independent_income - تعداد صندوق‌ها: {len(vaults)}")

    for vault in vaults:
        if vault.allocation_percentage > 0:
            allocated_amount = (income_amount * vault.allocation_percentage) / 100
            logger.info(f"DEBUG allocate - صندوق {vault.name}: {vault.allocation_percentage}%")
            logger.info(f"DEBUG allocate - مبلغ تخصیص: ${allocated_amount}")

            transaction = create_vault_transaction(
                db=db,
                vault_id=vault.id,
                amount=allocated_amount,
                transaction_type="independent_income",  # نوع جدید
                description=f"درآمد مستقل: {description}",
                receipt_id=None,  # بدون رسید
                created_by=admin_id
            )
            transactions.append(transaction)
            logger.info(f"DEBUG allocate - تراکنش ایجاد شد: {transaction.id}")

    logger.info(f"DEBUG allocate - تعداد تراکنش‌ها: {len(transactions)}")
    return transactions


# این توابع را به انتهای فایل database/crud.py اضافه کنید:

def toggle_customer_notification_status(db: Session, user_id: int) -> Optional[User]:
    """
    تغییر وضعیت دریافت پیام مشتری به صورت چرخشی:
    all (🟢) -> promotional_only (🟡) -> none (🔴) -> all (🟢)
    """
    user = get_user(db, user_id)
    if not user:
        return None

    current_status = user.notification_status or "all"

    # چرخش وضعیت
    if current_status == "all":
        user.notification_status = "promotional_only"
    elif current_status == "promotional_only":
        user.notification_status = "none"
    else:  # none
        user.notification_status = "all"

    db.commit()
    db.refresh(user)
    return user


def get_notification_status_emoji(status: str) -> str:
    """دریافت ایموجی مناسب برای وضعیت پیام"""
    status_map = {
        "all": "🟢",  # سبز - همه پیام‌ها
        "promotional_only": "🟡",  # زرد - فقط تبلیغات
        "none": "🔴"  # قرمز - هیچ پیامی
    }
    return status_map.get(status, "🟢")


def get_notification_status_text(status: str) -> str:
    """دریافت متن توضیح وضعیت"""
    status_map = {
        "all": "دریافت همه پیام‌ها (تخفیف‌های مناسبتی + تبلیغات)",
        "promotional_only": "فقط پیام‌های تبلیغاتی",
        "none": "عدم دریافت هیچ پیامی"
    }
    return status_map.get(status, "دریافت همه پیام‌ها")


def get_customers_for_notification(db: Session, notification_type: str = "promotional") -> List[User]:
    """
    دریافت مشتریانی که می‌توانند نوع خاصی از پیام را دریافت کنند

    Args:
        notification_type: نوع پیام - "promotional" یا "occasional"
    """
    if notification_type == "occasional":
        # پیام‌های تخفیف مناسبتی - فقط کسانی که all دارند
        return db.query(User).filter(
            User.role == "customer",
            User.notification_status == "all"
        ).all()
    else:  # promotional
        # پیام‌های تبلیغاتی - کسانی که all یا promotional_only دارند
        return db.query(User).filter(
            User.role == "customer",
            User.notification_status.in_(["all", "promotional_only"])
        ).all()


# ==================== STAFF MANAGEMENT ====================

from .models import Staff


def get_staff_by_user_id(db: Session, user_id: int) -> Optional[Staff]:
    """دریافت کارمند بر اساس user_id"""
    return db.query(Staff).filter(Staff.user_id == user_id).first()


def get_staff_by_role(db: Session, role: str, active_only: bool = True) -> List[Staff]:
    """دریافت لیست کارکنان بر اساس نقش"""
    query = db.query(Staff).filter(Staff.role == role)
    if active_only:
        query = query.filter(Staff.is_active == True)
    return query.all()


def get_all_staff(db: Session, active_only: bool = True) -> List[Staff]:
    """دریافت همه کارکنان"""
    query = db.query(Staff)
    if active_only:
        query = query.filter(Staff.is_active == True)
    return query.order_by(Staff.role, Staff.created_at.desc()).all()


def add_staff(db: Session, user_id: int, role: str, name: str = None,
              phone: str = None, added_by: int = None) -> Staff:
    """افزودن کارمند جدید - اصلاح شده"""
    from .models import Staff

    # 1. ثبت در Staff
    existing_staff = get_staff_by_user_id(db, user_id)
    if existing_staff:
        existing_staff.role = role
        existing_staff.name = name or existing_staff.name
        existing_staff.phone = phone or existing_staff.phone
        existing_staff.is_active = True
        existing_staff.added_by = added_by
        db.commit()
        db.refresh(existing_staff)
        staff = existing_staff
    else:
        staff = Staff(
            user_id=user_id,
            role=role,
            name=name,
            phone=phone,
            is_active=True,
            added_by=added_by
        )
        db.add(staff)
        db.commit()
        db.refresh(staff)

    # 2. ثبت در Users - این قسمت جدیده و مشکل رو حل می‌کنه
    existing_user = get_user(db, user_id)
    if existing_user:
        if existing_user.role != role:
            existing_user.role = role
            existing_user.full_name = name or existing_user.full_name
            db.commit()
    else:
        new_user = User(
            id=user_id,
            full_name=name or f"کارمند {user_id}",
            phone_number=phone,
            role=role
        )
        db.add(new_user)
        db.commit()

    return staff


def remove_staff(db: Session, user_id: int) -> bool:
    """غیرفعال کردن کارمند"""
    staff = get_staff_by_user_id(db, user_id)
    if staff:
        staff.is_active = False
        db.commit()
        return True
    return False


def delete_staff(db: Session, user_id: int) -> bool:
    """حذف کامل کارمند"""
    staff = get_staff_by_user_id(db, user_id)
    if staff:
        db.delete(staff)
        db.commit()
        return True
    return False


def is_editor(db: Session, user_id: int) -> bool:
    """چک کردن ادیتور بودن"""
    staff = get_staff_by_user_id(db, user_id)
    return staff is not None and staff.role == "editor" and staff.is_active


def is_operator(db: Session, user_id: int) -> bool:
    """چک کردن اپراتور بودن"""
    staff = get_staff_by_user_id(db, user_id)
    return staff is not None and staff.role == "operator" and staff.is_active


def is_visitor(db: Session, user_id: int) -> bool:
    """چک کردن ویزیتور بودن"""
    staff = get_staff_by_user_id(db, user_id)
    return staff is not None and staff.role == "visitor" and staff.is_active


def get_editors_ids(db: Session) -> List[int]:
    """دریافت لیست آیدی‌های ادیتورها"""
    editors = get_staff_by_role(db, "editor")
    return [e.user_id for e in editors]


def get_operators_ids(db: Session) -> List[int]:
    """دریافت لیست آیدی‌های اپراتورها"""
    operators = get_staff_by_role(db, "operator")
    return [o.user_id for o in operators]


def get_visitors_ids(db: Session) -> List[int]:
    """دریافت لیست آیدی‌های ویزیتورها"""
    visitors = get_staff_by_role(db, "visitor")
    return [v.user_id for v in visitors]

def get_customer_in_progress_files(db: Session, user_id: int) -> List[FileOrder]:
    """
    دریافت فایل‌های "در حال انجام" مشتری

    فایل‌های در حال انجام = فایل‌هایی که:
    1. مشتری ثبت کرده
    2. زمان ادیت تموم شده (edit_deadline گذشته)
    3. هنوز فاکتور/پرینت نشده (status != invoiced و cancelled)

    Args:
        db: Database session
        user_id: شناسه کاربر مشتری

    Returns:
        لیست فایل‌های در حال انجام
    """
    now = now_utc()

    files = db.query(FileOrder).filter(
        and_(
            FileOrder.user_id == user_id,
            FileOrder.status.in_(["pending", "confirmed"]),  # هنوز فاکتور نشده
            FileOrder.edit_deadline.isnot(None),  # زمان ادیت تعیین شده
            FileOrder.edit_deadline < now  # زمان ادیت گذشته
        )
    ).order_by(desc(FileOrder.created_at)).all()

    return files

def initialize_default_settings(db: Session):
    """مقداردهی اولیه تنظیمات سیستم"""
    # بررسی و تنظیم مقدار پیش‌فرض تاخیر دسترسی ادیتورها
    delay_setting = get_system_setting(db, "editor_access_delay_minutes", None)
    if delay_setting is None:
        set_system_setting(
            db,
            "editor_access_delay_minutes",
            "5",  # مقدار پیش‌فرض 5 دقیقه
            "تاخیر دسترسی ادیتورها به فایل‌های جدید (به دقیقه)"
        )
        logger.info("✅ تنظیم پیش‌فرض تاخیر ادیتورها: 5 دقیقه")