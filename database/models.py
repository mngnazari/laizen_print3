# database/models.py
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, func, Float, Text, Boolean
from sqlalchemy.orm import relationship, Mapped
from .connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    full_name = Column(String, index=True)
    phone_number = Column(String, unique=True, index=True)
    customer_code = Column(String, unique=True, index=True, nullable=True)  # کد اختصاری مشتری مثل c1, c2, ...
    referral_code = Column(String, unique=True, index=True, nullable=True)
    referrer_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    referrals_count = Column(Integer, default=0)
    max_referrals = Column(Integer, default=3)
    discount_credit = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String, nullable=True, default=None, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    role = Column(String, nullable=True, default=None, index=True)  # admin, operator, editor, visitor, customer
    wallet_balance = Column(Float, default=0.0)


    # فیلد جدید برای وضعیت دریافت پیام‌های تبلیغاتی
    notification_status = Column(String, default="all")  # all, promotional_only, none

    # فیلد جدید برای قیمت پرینت اختصاصی هر مشتری
    print_price_per_gram = Column(Float, nullable=True)

    # فیلد جدید برای قیمت پرینت اختصاصی هر مشتری
    print_price_per_gram = Column(Float, nullable=True)  # اگر null باشد از قیمت کلی سیستم استفاده شود

    # Relationships (بدون تغییر)
    referrer: Mapped["User"] = relationship("User", back_populates="referred_users", remote_side=[id])
    referred_users: Mapped[list["User"]] = relationship("User", back_populates="referrer")
    file_orders: Mapped[list["FileOrder"]] = relationship("FileOrder", back_populates="user")

    # رابطه با فاکتورها - مشخص کردن foreign key برای رفع مشکل AmbiguousForeignKeysError
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="customer",
        foreign_keys="Invoice.customer_id"
    )

    # رابطه با تراکنش‌های کیف پول - اصلاح شده برای رفع مشکل AmbiguousForeignKeysError
    wallet_transactions: Mapped[list["WalletTransaction"]] = relationship(
        "WalletTransaction",
        back_populates="user",
        foreign_keys="WalletTransaction.user_id"
    )


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(BigInteger, ForeignKey("users.id"))
    creator_role = Column(String, nullable=False)  # admin، customer، editor، visitor
    referral_code = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # رابطه با جدول کاربران
    creator: Mapped["User"] = relationship("User", foreign_keys=[creator_id])


class FileOrder(Base):
    __tablename__ = "file_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=True)
    file_id = Column(String, nullable=False)  # Telegram File ID
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    edit_deadline = Column(DateTime, nullable=True)  # فیلد جدید
    print_count = Column(Integer, default=1)
    description = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, confirmed, cancelled, invoiced
    message_id = Column(Integer, nullable=False)
    delivery_datetime = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)
    has_invoice = Column(Boolean, default=False)  # آیا فاکتور صادر شده یا نه
    sent_to_operator = Column(Boolean, default=False)
    operator_filename = Column(String, nullable=True)  # نام فایل تغییر یافته
    sent_to_operator_at = Column(DateTime, nullable=True)
    assigned_editor_id = Column(BigInteger, nullable=True)  # آی‌دی ادیتور مسئول
    editor_status = Column(String, default="pending")  # pending, assigned, approved, rejected
    editor_assigned_at = Column(DateTime, nullable=True)  # زمان تخصیص به ادیتور
    editor_notes = Column(Text, nullable=True)  # یادداشت ادیتور

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="file_orders")


class Invoice(Base):
    """جدول فاکتورها"""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    operator_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    file_order_id = Column(Integer, ForeignKey("file_orders.id"), nullable=True)  # ارتباط با سفارش فایل

    # اطلاعات فاکتور
    weight_grams = Column(Float, nullable=False)  # وزن به گرم
    price_per_gram = Column(Float, nullable=False)  # قیمت هر گرم
    total_amount = Column(Float, nullable=False)  # مبلغ کل

    # عکس مدل‌های پرینت شده
    photo_file_id = Column(String, nullable=False)  # Telegram File ID عکس

    # تاریخ‌ها
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    customer: Mapped["User"] = relationship("User", back_populates="invoices", foreign_keys=[customer_id])
    operator: Mapped["User"] = relationship("User", foreign_keys=[operator_id])
    file_order: Mapped["FileOrder"] = relationship("FileOrder")


class WalletTransaction(Base):
    """جدول تراکنش‌های کیف پول"""
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    admin_id = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # در صورت نیاز
    amount = Column(Float, nullable=False)  # مبلغ (مثبت = شارژ، منفی = خرج)
    transaction_type = Column(String, nullable=False)  # referral_bonus, invoice_payment, admin_adjustment
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    user: Mapped["User"] = relationship("User", back_populates="wallet_transactions", foreign_keys=[user_id])
    admin: Mapped["User"] = relationship("User", foreign_keys=[admin_id])


class SystemSettings(Base):
    """جدول تنظیمات سیستم"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, nullable=False)  # مثل price_per_gram, last_customer_number
    setting_value = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# اضافه کردن این جداول به انتهای فایل database/models.py

class Holiday(Base):
    """جدول روزهای تعطیل"""
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, nullable=False, unique=True)  # فرمت YYYY-MM-DD
    is_holiday = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# در database/models.py - اضافه کردن به کلاس DeliverySchedule

class DeliverySchedule(Base):
    """جدول تنظیمات زمان‌بندی تحویل"""
    __tablename__ = "delivery_schedules"

    id = Column(Integer, primary_key=True, index=True)
    delivery_number = Column(Integer, nullable=False)  # 1, 2, 3 (شماره تحویل در روز)
    cutoff_time = Column(String, nullable=False)  # فرمت HH:MM
    cutoff_day_offset = Column(Integer, default=0)  # 0=همان روز، -1=روز قبل
    delivery_offset_hours = Column(Integer, nullable=False)  # تعداد ساعت تا تحویل

    # فیلد جدید برای زمان مجاز ادیت
    edit_deadline_hours = Column(Integer, nullable=False, default=2)  # چند ساعت بعد از cutoff_time برای ادیت

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# در انتهای فایل models.py
# اضافه کردن این مدل به آخر فایل database/models.py

class Receipt(Base):
    """جدول رسیدهای کارت به کارت"""
    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    file_id = Column(String, nullable=False)  # Telegram File ID عکس
    file_name = Column(String, nullable=True)  # نام فایل (اختیاری)
    file_size = Column(Integer, nullable=True)  # سایز فایل
    description = Column(Text, nullable=True)  # توضیح اختیاری از کاربر
    status = Column(String, default="pending")  # pending, approved, rejected
    admin_notes = Column(Text, nullable=True)  # یادداشت ادمین
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # ادمین بررسی‌کننده

    # روابط
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    reviewer: Mapped["User"] = relationship("User", foreign_keys=[reviewed_by])

# Import مدل‌های ادیتور
from .editor_models import EditorWorkSession, EditorOriginalFile, EditorFileMapping, ProcessedFile

class Vault(Base):
    __tablename__ = "vaults"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    balance = Column(Float, default=0.0)  # موجودی نقد
    gold_balance = Column(Float, default=0.0)  # موجودی طلا به گرم
    allocation_percentage = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # رابطه با تراکنش‌ها
    transactions: Mapped[list["VaultTransaction"]] = relationship("VaultTransaction", back_populates="vault")
    gold_transactions: Mapped[list["VaultGoldTransaction"]] = relationship("VaultGoldTransaction", back_populates="vault")


class VaultTransaction(Base):
    """جدول تراکنش‌های صندوق"""
    __tablename__ = "vault_transactions"

    id = Column(Integer, primary_key=True, index=True)
    vault_id = Column(Integer, ForeignKey("vaults.id"), nullable=False)
    amount = Column(Float, nullable=False)  # مبلغ (مثبت = واریز، منفی = برداشت)
    transaction_type = Column(String, nullable=False)  # auto_allocation, manual_expense, adjustment
    description = Column(Text, nullable=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=True)  # ارتباط با رسید (در صورت تخصیص خودکار)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)  # کسی که تراکنش را ثبت کرده
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    vault: Mapped["Vault"] = relationship("Vault", back_populates="transactions")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    receipt: Mapped["Receipt"] = relationship("Receipt", foreign_keys=[receipt_id])

class VaultGoldTransaction(Base):
    """جدول معاملات طلای صندوق‌ها"""
    __tablename__ = "vault_gold_transactions"

    id = Column(Integer, primary_key=True, index=True)
    vault_id = Column(Integer, ForeignKey("vaults.id"), nullable=False)
    transaction_type = Column(String, nullable=False)  # buy, sell
    gold_weight_grams = Column(Float, nullable=False)  # وزن طلا به گرم
    price_per_gram_dollar = Column(Float, nullable=False)  # قیمت هر گرم به دلار
    price_per_gram_toman = Column(Float, nullable=True)  # قیمت هر گرم به تومان (اختیاری)
    total_amount = Column(Float, nullable=False)  # مبلغ کل معامله به دلار
    description = Column(Text, nullable=True)
    created_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # روابط
    vault: Mapped["Vault"] = relationship("Vault", back_populates="gold_transactions")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])

class Staff(Base):
    """جدول کارکنان (ادیتور، اپراتور، ویزیتور)"""
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False, index=True)  # editor, operator, visitor
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    added_by = Column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # روابط
    added_by_user: Mapped["User"] = relationship("User", foreign_keys=[added_by])