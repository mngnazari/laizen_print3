# database/editor_crud.py
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import logging
import unicodedata

from .editor_models import EditorWorkSession, EditorOriginalFile, EditorFileMapping, ProcessedFile
from .models import FileOrder, User
from utils.timezone_utils import now_utc

logger = logging.getLogger(__name__)


def log_filename_details(filename, label=""):
    """لاگ تفصیلی برای نام فایل"""
    logger.info(f"🔍 {label} فایل: '{filename}'")
    logger.info(f"📏 طول: {len(filename)}")
    logger.info(f"🔤 نوع: {type(filename)}")

    # نمایش هر کاراکتر با کد ASCII/Unicode
    char_details = []
    for i, char in enumerate(filename):
        char_code = ord(char)
        char_name = unicodedata.name(char, f"UNKNOWN-{char_code}")
        char_details.append(f"[{i}]='{char}'(U+{char_code:04X}:{char_name})")

    logger.info(f"🔤 کاراکترها: {' '.join(char_details)}")

    # بررسی whitespace و کاراکترهای مخفی
    stripped = filename.strip()
    if stripped != filename:
        logger.warning(f"⚠️ فایل دارای whitespace اضافی است: قبل='{filename}' بعد='{stripped}'")

    # بررسی encoding
    try:
        encoded_utf8 = filename.encode('utf-8')
        logger.info(f"🔢 UTF-8 bytes: {encoded_utf8}")
    except Exception as e:
        logger.error(f"❌ خطا در encoding UTF-8: {e}")


def normalize_filename(filename):
    """نرمال‌سازی نام فایل برای مقایسه"""
    logger.info(f"🔧 شروع نرمال‌سازی: '{filename}'")

    # حذف whitespace
    normalized = filename.strip()
    logger.info(f"🔧 بعد از حذف whitespace: '{normalized}'")

    # Unicode normalization
    normalized = unicodedata.normalize('NFKC', normalized)
    logger.info(f"🔧 بعد از Unicode normalization: '{normalized}'")

    return normalized


def get_editor_current_session(db: Session, editor_id: int) -> Optional[EditorWorkSession]:
    """دریافت جلسه کاری فعلی ادیتور"""
    return db.query(EditorWorkSession).filter(
        EditorWorkSession.editor_id == editor_id,
        EditorWorkSession.status.in_(["working"])
    ).first()


def create_editor_session(db: Session, editor_id: int, file_orders: List[FileOrder]) -> EditorWorkSession:
    """ایجاد جلسه کاری جدید برای ادیتور"""
    try:
        # ایجاد جلسه جدید
        session = EditorWorkSession(
            editor_id=editor_id,
            status="working",
            original_file_count=len(file_orders)
        )
        db.add(session)
        db.flush()  # برای گرفتن ID

        # اضافه کردن فایل‌های اصلی
        for file_order in file_orders:
            original_file = EditorOriginalFile(
                session_id=session.id,
                file_order_id=file_order.id,
                original_filename=file_order.file_name,
                file_id=file_order.file_id
            )
            db.add(original_file)

        db.commit()
        db.refresh(session)
        logger.info(f"جلسه کاری جدید برای ادیتور {editor_id} با {len(file_orders)} فایل ایجاد شد")
        return session

    except Exception as e:
        db.rollback()
        logger.error(f"خطا در ایجاد جلسه کاری ادیتور: {e}")
        raise


def get_editor_status(db: Session, editor_id: int) -> str:
    """تشخیص وضعیت فعلی ادیتور"""
    session = get_editor_current_session(db, editor_id)

    if not session:
        return "idle"  # وضعیت 1 و 4: هیچ فایلی ندارد

    if not session.file_mapping:
        return "waiting_mapping"  # وضعیت 2: فایل دارد اما نقشه نفرستاده

    # بررسی آیا همه فایل‌ها کامل شده‌اند
    processed_files = db.query(ProcessedFile).join(EditorOriginalFile).filter(
        EditorOriginalFile.session_id == session.id
    ).all()

    if not processed_files:
        return "mapping_received"  # نقشه دریافت شده اما هنوز پردازش نشده

    incomplete_files = [f for f in processed_files if not f.is_completed]

    if incomplete_files:
        return "waiting_files"  # وضعیت 3: منتظر دریافت فایل‌ها

    # همه فایل‌ها کامل شده، جلسه را به completed تغییر دهیم
    session.status = "completed"
    session.completed_at = datetime.now()
    db.commit()

    return "completed"  # کار تمام شده


def save_mapping_file(db: Session, editor_id: int, mapping_content: str) -> bool:
    """ذخیره فایل نقشه و ایجاد رکوردهای فایل‌های مورد انتظار"""
    logger.info(f"💾 شروع ذخیره فایل نقشه برای ادیتور {editor_id}")

    try:
        session = get_editor_current_session(db, editor_id)
        if not session:
            logger.warning(f"❌ جلسه کاری برای ادیتور {editor_id} یافت نشد")
            return False

        # ذخیره فایل نقشه
        mapping = EditorFileMapping(
            session_id=session.id,
            mapping_content=mapping_content
        )
        db.add(mapping)
        session.mapping_received_at = datetime.now()

        logger.info(f"📝 فایل نقشه در دیتابیس ذخیره شد")

        # پردازش محتوای نقشه و ایجاد فایل‌های مورد انتظار
        from utils.mapping_parser import parse_mapping_content
        processed_files_data = parse_mapping_content(mapping_content, session)

        logger.info(f"📋 تعداد فایل‌های پردازش شده: {len(processed_files_data)}")

        for i, file_data in enumerate(processed_files_data, 1):
            logger.info(f"➕ اضافه کردن فایل {i}: '{file_data['processed_filename']}'")
            log_filename_details(file_data['processed_filename'], f"فایل {i} - نام پردازش شده")

            processed_file = ProcessedFile(
                original_file_id=file_data['original_file_id'],
                original_filename=file_data['original_filename'],
                processed_filename=file_data['processed_filename'],
                stl_required=file_data['stl_required'],
                jpg_required=file_data['jpg_required'],
                zip_required=file_data['zip_required']
            )
            db.add(processed_file)

        db.commit()

        # لاگ نهایی فایل‌های مورد انتظار
        logger.info("📋 خلاصه فایل‌های مورد انتظار ایجاد شده:")
        final_files = db.query(ProcessedFile).join(EditorOriginalFile).filter(
            EditorOriginalFile.session_id == session.id
        ).all()

        for i, pf in enumerate(final_files, 1):
            logger.info(
                f"  {i}. '{pf.processed_filename}' (STL:{pf.stl_required}, JPG:{pf.jpg_required}, ZIP:{pf.zip_required})")

        logger.info(f"✅ فایل نقشه برای ادیتور {editor_id} ذخیره شد")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"💥 خطا در ذخیره فایل نقشه: {e}", exc_info=True)
        return False


def get_pending_files_for_editor(db: Session, editor_id: int) -> List[ProcessedFile]:
    """دریافت لیست فایل‌های در انتظار دریافت از ادیتور"""
    session = get_editor_current_session(db, editor_id)
    if not session:
        return []

    return db.query(ProcessedFile).join(EditorOriginalFile).filter(
        EditorOriginalFile.session_id == session.id,
        ProcessedFile.is_completed == False
    ).all()


def check_filename_expected(db: Session, editor_id: int, filename: str) -> bool:
    """بررسی آیا فایل با این نام در انتظار دریافت است - با لاگ تفصیلی"""
    logger.info(f"🔍 شروع بررسی فایل: '{filename}' برای ادیتور {editor_id}")

    session = get_editor_current_session(db, editor_id)
    if not session:
        logger.warning(f"❌ جلسه کاری برای ادیتور {editor_id} یافت نشد")
        return False

    # دریافت همه فایل‌های مورد انتظار
    expected_files = db.query(ProcessedFile).join(EditorOriginalFile).filter(
        EditorOriginalFile.session_id == session.id,
        ProcessedFile.is_completed == False
    ).all()

    logger.info(f"📋 تعداد فایل‌های مورد انتظار: {len(expected_files)}")

    # لاگ تفصیلی فایل دریافتی
    log_filename_details(filename, "دریافتی")

    # حذف پسوند از فایل دریافتی
    base_filename_received = filename.rsplit('.', 1)[0]
    logger.info(f"🔧 نام پایه فایل دریافتی: '{base_filename_received}'")
    log_filename_details(base_filename_received, "نام پایه دریافتی")

    # مقایسه با هر فایل مورد انتظار
    for i, processed_file in enumerate(expected_files):
        expected_name = processed_file.processed_filename
        logger.info(f"\n--- مقایسه {i + 1} ---")
        log_filename_details(expected_name, f"مورد انتظار {i + 1}")

        # حذف پسوند از فایل مورد انتظار
        base_expected = expected_name.rsplit('.', 1)[0] if '.' in expected_name else expected_name
        logger.info(f"🔧 نام پایه مورد انتظار: '{base_expected}'")
        log_filename_details(base_expected, f"نام پایه مورد انتظار {i + 1}")

        # مقایسه‌های مختلف
        exact_match = base_filename_received == base_expected
        logger.info(f"🔍 مقایسه دقیق: {exact_match}")

        # مقایسه بعد از نرمال‌سازی
        normalized_received = normalize_filename(base_filename_received)
        normalized_expected = normalize_filename(base_expected)
        normalized_match = normalized_received == normalized_expected
        logger.info(f"🔍 مقایسه نرمال‌شده: {normalized_match}")

        # مقایسه case-insensitive
        case_insensitive_match = base_filename_received.lower() == base_expected.lower()
        logger.info(f"🔍 مقایسه case-insensitive: {case_insensitive_match}")

        # اگر هیچ‌کدام match نکرد، تفاوت‌ها را نشان بده
        if not any([exact_match, normalized_match, case_insensitive_match]):
            logger.warning(f"❌ هیچ match یافت نشد برای '{expected_name}'")

            # نمایش تفاوت‌های کاراکتر به کاراکتر
            min_len = min(len(normalized_received), len(normalized_expected))
            for j in range(min_len):
                if normalized_received[j] != normalized_expected[j]:
                    logger.warning(
                        f"⚠️ تفاوت در موقعیت {j}: دریافتی='{normalized_received[j]}'(U+{ord(normalized_received[j]):04X}) vs مورد انتظار='{normalized_expected[j]}'(U+{ord(normalized_expected[j]):04X})")

            if len(normalized_received) != len(normalized_expected):
                logger.warning(
                    f"⚠️ تفاوت در طول: دریافتی={len(normalized_received)} vs مورد انتظار={len(normalized_expected)}")
        else:
            logger.info(f"✅ Match یافت شد با فایل '{expected_name}'")
            return True

    logger.warning(f"❌ هیچ match برای فایل '{filename}' یافت نشد")
    return False


def receive_editor_file(db: Session, editor_id: int, filename: str, file_id: str, file_type: str) -> tuple[bool, str]:
    """ثبت دریافت فایل از ادیتور - با لاگ‌های تفصیلی"""
    logger.info(f"📥 شروع دریافت فایل: '{filename}' نوع: {file_type} از ادیتور {editor_id}")

    try:
        session = get_editor_current_session(db, editor_id)
        if not session:
            return False, "جلسه کاری فعال یافت نشد"

        # لاگ تفصیلی فایل دریافتی
        log_filename_details(filename, "فایل دریافتی")

        # یافتن فایل مورد انتظار
        base_filename = filename.rsplit('.', 1)[0]  # حذف پسوند
        logger.info(f"🔧 جستجو برای نام پایه: '{base_filename}'")
        log_filename_details(base_filename, "نام پایه برای جستجو")

        # دریافت همه فایل‌های مورد انتظار برای debugging
        all_expected = db.query(ProcessedFile).join(EditorOriginalFile).filter(
            EditorOriginalFile.session_id == session.id
        ).all()

        logger.info(f"📋 لیست کامل فایل‌های مورد انتظار:")
        for i, pf in enumerate(all_expected):
            logger.info(f"  {i + 1}. '{pf.processed_filename}' - کامل: {pf.is_completed}")
            log_filename_details(pf.processed_filename, f"انتظار {i + 1}")

        # جستجوی فایل با criteria های مختلف
        processed_file = None

        # جستجوی دقیق
        processed_file = db.query(ProcessedFile).join(EditorOriginalFile).filter(
            EditorOriginalFile.session_id == session.id,
            ProcessedFile.processed_filename == base_filename
        ).first()

        if processed_file:
            logger.info(f"✅ فایل با جستجوی دقیق یافت شد")
        else:
            logger.warning(f"❌ جستجوی دقیق نتیجه نداد، تلاش برای جستجوی نرمال‌شده")

            # جستجوی با نرمال‌سازی
            normalized_base = normalize_filename(base_filename)

            for pf in all_expected:
                expected_base = pf.processed_filename.rsplit('.', 1)[
                    0] if '.' in pf.processed_filename else pf.processed_filename
                normalized_expected = normalize_filename(expected_base)

                if normalized_base == normalized_expected:
                    processed_file = pf
                    logger.info(f"✅ فایل با جستجوی نرمال‌شده یافت شد: '{pf.processed_filename}'")
                    break

        if not processed_file:
            logger.error(f"❌ فایل '{base_filename}' در لیست انتظار یافت نشد")

            # ارائه پیشنهادات
            suggestions = []
            for pf in all_expected:
                if not pf.is_completed:
                    expected_base = pf.processed_filename.rsplit('.', 1)[
                        0] if '.' in pf.processed_filename else pf.processed_filename
                    suggestions.append(expected_base)

            if suggestions:
                logger.info(f"💡 فایل‌های مورد انتظار: {suggestions}")
                return False, f"این فایل در لیست انتظار نیست. فایل‌های مورد انتظار: {', '.join(suggestions)}"
            else:
                return False, "هیچ فایل در انتظار دریافت نیست"

        # ثبت دریافت بر اساس نوع فایل
        now = datetime.now()
        logger.info(f"📝 ثبت دریافت فایل نوع {file_type}")

        if file_type == "stl":
            if not processed_file.stl_required:
                return False, "فایل STL برای این آیتم مورد نیاز نیست"
            processed_file.stl_file_id = file_id
            processed_file.stl_received = True
            processed_file.stl_received_at = now

        elif file_type == "jpg":
            if not processed_file.jpg_required:
                return False, "فایل JPG برای این آیتم مورد نیاز نیست"
            processed_file.jpg_file_id = file_id
            processed_file.jpg_received = True
            processed_file.jpg_received_at = now

        elif file_type == "zip":
            if not processed_file.zip_required:
                return False, "فایل ZIP برای این آیتم مورد نیاز نیست"
            processed_file.zip_file_id = file_id
            processed_file.zip_received = True
            processed_file.zip_received_at = now

        else:
            return False, "نوع فایل نامشخص"

        # بررسی کامل بودن این فایل
        check_file_completion(processed_file)

        logger.info(f"✅ فایل '{filename}' با موفقیت ثبت شد. کامل: {processed_file.is_completed}")

        db.commit()
        return True, "فایل دریافت شد"

    except Exception as e:
        db.rollback()
        logger.error(f"💥 خطا در دریافت فایل از ادیتور: {e}", exc_info=True)
        return False, f"خطا در ثبت فایل: {str(e)}"


def check_file_completion(processed_file: ProcessedFile):
    """بررسی کامل بودن یک فایل پردازش شده"""
    stl_ok = not processed_file.stl_required or processed_file.stl_received
    jpg_ok = not processed_file.jpg_required or processed_file.jpg_received
    zip_ok = not processed_file.zip_required or processed_file.zip_received

    processed_file.is_completed = stl_ok and jpg_ok and zip_ok


def get_editor_progress_stats(db: Session, editor_id: int) -> Dict:
    """دریافت آمار پیشرفت کار ادیتور"""
    session = get_editor_current_session(db, editor_id)
    if not session:
        return {
            "status": "idle",
            "total_files": 0,
            "completed_files": 0,
            "pending_files": 0
        }

    processed_files = db.query(ProcessedFile).join(EditorOriginalFile).filter(
        EditorOriginalFile.session_id == session.id
    ).all()

    completed_count = len([f for f in processed_files if f.is_completed])

    return {
        "status": get_editor_status(db, editor_id),
        "total_files": len(processed_files),
        "completed_files": completed_count,
        "pending_files": len(processed_files) - completed_count,
        "original_file_count": session.original_file_count,
        "mapping_received": session.file_mapping is not None
    }


def complete_editor_session(db: Session, editor_id: int) -> bool:
    """تکمیل جلسه کاری ادیتور"""
    try:
        session = get_editor_current_session(db, editor_id)
        if not session:
            return False

        session.status = "completed"
        session.completed_at = datetime.now()
        db.commit()

        logger.info(f"جلسه کاری ادیتور {editor_id} تکمیل شد")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"خطا در تکمیل جلسه کاری: {e}")
        return False


def is_file_accessible_for_editor(file_order, delay_minutes: int = 0) -> bool:
    """بررسی اینکه آیا فایل برای ادیتور قابل دسترسی هست یا نه"""
    from datetime import timezone, timedelta

    logger.info(f"🔍 بررسی دسترسی فایل: {file_order.file_name}")
    logger.info(f"⏰ تاخیر تنظیم شده: {delay_minutes} دقیقه")

    if delay_minutes == 0:
        logger.info(f"✅ حالت تست - فایل فوری قابل دسترس است")
        return True

        # محاسبه زمان قابل دسترسی
        access_time = None

        if file_order.edit_deadline:
            access_time = file_order.edit_deadline
            logger.info(f"📅 استفاده از edit_deadline: {access_time}")
        elif file_order.created_at:
            access_time = file_order.created_at + timedelta(minutes=delay_minutes)
            logger.info(f"📅 محاسبه از created_at: {file_order.created_at} + {delay_minutes} دقیقه = {access_time}")

        if access_time is None:
            logger.warning(f"⚠️ زمان دسترسی None است - فایل قابل دسترس در نظر گرفته میشه")
            return True

        # حذف timezone اگه داره
        if hasattr(access_time, 'tzinfo') and access_time.tzinfo:
            access_time = access_time.replace(tzinfo=None)

        # زمان فعلی (بدون timezone)
        now = datetime.now()

        is_accessible = now >= access_time
        time_diff_minutes = (access_time - now).total_seconds() / 60

        logger.info(f"🕐 زمان فعلی: {now}")
        logger.info(f"🕐 زمان دسترسی: {access_time}")
        logger.info(f"⏳ تفاوت: {time_diff_minutes:.2f} دقیقه")
        logger.info(f"{'✅ قابل دسترس' if is_accessible else '🔒 هنوز قابل دسترس نیست'}")

        return is_accessible

def get_accessible_files_for_editor(db: Session, status: str = "pending") -> List[FileOrder]:
    """
    دریافت فایل‌هایی که برای ادیتور قابل دسترسن

    Args:
        db: database session
        status: وضعیت فایل‌ها (پیش‌فرض: pending)

    Returns:
        لیست فایل‌های قابل دسترس
    """
    from database.crud import get_system_setting

    # دریافت تنظیم تاخیر
    delay_minutes = int(get_system_setting(db, "editor_access_delay_minutes", "0"))

    logger.info(f"دریافت فایل‌های قابل دسترس با تاخیر {delay_minutes} دقیقه")

    # دریافت همه فایل‌های pending
    all_pending = db.query(FileOrder).filter(
        FileOrder.status == status
    ).options(joinedload(FileOrder.user)).all()

    logger.info(f"تعداد کل فایل‌های {status}: {len(all_pending)}")

    # فیلتر بر اساس قابلیت دسترسی
    accessible_files = [
        f for f in all_pending
        if is_file_accessible_for_editor(f, delay_minutes)
    ]

    logger.info(f"تعداد فایل‌های قابل دسترس: {len(accessible_files)}")

    return accessible_files