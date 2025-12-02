# utils/mapping_parser.py
from typing import List, Dict
import logging
import unicodedata

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


def debug_mapping_content(content: str):
    """Debug محتوای فایل mapping"""
    logger.info("🗺️ شروع debug محتوای mapping")
    logger.info(f"📏 طول کل: {len(content)}")

    lines = content.split('\n')
    logger.info(f"📄 تعداد خطوط: {len(lines)}")

    for i, line in enumerate(lines):
        logger.info(f"📝 خط {i + 1}: '{line}'")
        log_filename_details(line.strip(), f"خط {i + 1}")

        # پردازش خط برای استخراج نام فایل
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) >= 2:
                source = parts[0].strip()
                target = parts[1].strip()
                logger.info(f"🎯 مبدا: '{source}' مقصد: '{target}'")
                log_filename_details(source, "مبدا")
                log_filename_details(target, "مقصد")


def parse_mapping_content(mapping_content: str, session) -> List[Dict]:
    """پردازش محتوای فایل نقشه و تولید لیست فایل‌های مورد انتظار"""
    logger.info("🗺️ شروع پردازش محتوای mapping")

    # Debug کامل محتوای mapping
    debug_mapping_content(mapping_content)

    try:
        processed_files_data = []
        lines = mapping_content.strip().split('\n')

        # دریافت فایل‌های اصلی جلسه
        original_files = {f.original_filename: f for f in session.original_files}
        logger.info(f"📋 فایل‌های اصلی موجود: {list(original_files.keys())}")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            logger.info(f"\n--- پردازش خط {line_num} ---")
            log_filename_details(line, f"خط {line_num} خام")

            if not line or ':' not in line:
                logger.warning(f"⚠️ خط {line_num} نادیده گرفته شد: خالی یا بدون ':'")
                continue

            try:
                original_filename, processed_filename = line.split(':', 1)
                original_filename = original_filename.strip()
                processed_filename = processed_filename.strip()

                logger.info(f"🔍 استخراج شده - اصلی: '{original_filename}' پردازش شده: '{processed_filename}'")
                log_filename_details(original_filename, f"خط {line_num} - اصلی")
                log_filename_details(processed_filename, f"خط {line_num} - پردازش شده")

                # یافتن فایل اصلی مربوطه
                if original_filename not in original_files:
                    logger.warning(f"❌ فایل اصلی '{original_filename}' در جلسه یافت نشد")

                    # پیشنهاد فایل‌های مشابه
                    suggestions = []
                    for available_file in original_files.keys():
                        if original_filename.lower() in available_file.lower() or available_file.lower() in original_filename.lower():
                            suggestions.append(available_file)

                    if suggestions:
                        logger.info(f"💡 فایل‌های مشابه موجود: {suggestions}")

                    continue

                original_file = original_files[original_filename]
                logger.info(f"✅ فایل اصلی یافت شد: ID={original_file.id}")

                # تعیین فایل‌های مورد نیاز
                file_requirements = determine_file_requirements(original_filename, processed_filename)
                logger.info(
                    f"📋 نیازهای فایل: STL={file_requirements['stl_required']}, JPG={file_requirements['jpg_required']}, ZIP={file_requirements['zip_required']}")

                processed_files_data.append({
                    'original_file_id': original_file.id,
                    'original_filename': original_filename,
                    'processed_filename': processed_filename,
                    'stl_required': file_requirements['stl_required'],
                    'jpg_required': file_requirements['jpg_required'],
                    'zip_required': file_requirements['zip_required']
                })

                logger.info(f"✅ خط {line_num} با موفقیت پردازش شد")

            except ValueError as e:
                logger.error(f"❌ خطا در پردازش خط {line_num}: {line} - {e}")
                continue

        logger.info(f"🎉 فایل نقشه پردازش شد: {len(processed_files_data)} فایل شناسایی شد")

        # لاگ نهایی لیست فایل‌های مورد انتظار
        logger.info("📋 لیست نهایی فایل‌های مورد انتظار:")
        for i, file_data in enumerate(processed_files_data, 1):
            logger.info(
                f"  {i}. '{file_data['processed_filename']}' (STL:{file_data['stl_required']}, JPG:{file_data['jpg_required']}, ZIP:{file_data['zip_required']})")

        return processed_files_data

    except Exception as e:
        logger.error(f"💥 خطا در پردازش محتوای نقشه: {e}", exc_info=True)
        return []


# در فایل utils/mapping_parser.py
# فقط این تابع را تغییر بده:

def determine_file_requirements(original_filename: str, processed_filename: str) -> Dict[str, bool]:
    """تعیین نوع فایل‌های مورد نیاز بر اساس نام فایل‌های اصلی و پردازش شده"""
    logger.info(f"🔍 تعیین نیازهای فایل: '{original_filename}' -> '{processed_filename}'")

    # حذف پسوند برای مقایسه دقیق‌تر
    original_base = original_filename.rsplit('.', 1)[0] if '.' in original_filename else original_filename
    processed_base = processed_filename.rsplit('.', 1)[0] if '.' in processed_filename else processed_filename

    logger.info(f"🔧 نام پایه اصلی: '{original_base}' -> نام پایه پردازش شده: '{processed_base}'")

    # بررسی آیا فایل پردازش شده شامل # است (تقسیم شده)
    if '#' in processed_base:
        # استخراج نام اصلی قبل از #
        base_name_before_hash = processed_base.split('#')[0]
        logger.info(f"🔧 نام قبل از #: '{base_name_before_hash}'")

        # اگر نام قبل از # با نام اصلی یکی باشد - فایل تقسیم شده
        if base_name_before_hash == original_base:
            logger.info("📌 فایل تقسیم شده با # - همه فایل‌ها مورد نیاز")
            return {
                'stl_required': True,  # فایل STL جدید مورد نیاز است
                'jpg_required': True,  # عکس مورد نیاز است
                'zip_required': True  # فایل ZIP مورد نیاز است
            }

    # بررسی آیا فقط پسوند تغییر کرده (مثل 3dm.3dm -> 3dm.stl)
    original_name_only = original_base
    processed_name_only = processed_base

    # اگر نام پایه یکسان است - فقط تبدیل فرمت
    if original_name_only == processed_name_only:
        # بررسی پسوندها
        original_ext = original_filename.rsplit('.', 1)[1] if '.' in original_filename else ''
        processed_ext = processed_filename.rsplit('.', 1)[1] if '.' in processed_filename else ''

        logger.info(f"🔧 پسوند اصلی: '{original_ext}' -> پسوند پردازش شده: '{processed_ext}'")

        # اگر از STL به STL - فایل تغییر نکرده
        if original_ext.lower() == 'stl' and processed_ext.lower() == 'stl':
            logger.info("📌 فایل STL بدون تغییر - فقط JPG و ZIP مورد نیاز")
            return {
                'stl_required': False,  # فایل STL از قبل موجود است
                'jpg_required': True,  # عکس مورد نیاز است
                'zip_required': True  # فایل ZIP مورد نیاز است
            }

        # اگر از فرمت دیگر به STL - تبدیل فرمت
        elif processed_ext.lower() == 'stl':
            logger.info("📌 تبدیل فرمت به STL - همه فایل‌ها مورد نیاز")
            return {
                'stl_required': True,  # فایل STL جدید مورد نیاز است
                'jpg_required': True,  # عکس مورد نیاز است
                'zip_required': True  # فایل ZIP مورد نیاز است
            }

    # در غیر این صورت - فایل تغییر کرده یا تبدیل شده
    logger.info("📌 فایل تغییر کرده - همه فایل‌ها مورد نیاز")
    return {
        'stl_required': True,  # فایل STL جدید مورد نیاز است
        'jpg_required': True,  # عکس مورد نیاز است
        'zip_required': True  # فایل ZIP مورد نیاز است
    }


def get_expected_filenames(mapping_content: str) -> Dict[str, List[str]]:
    """استخراج نام فایل‌های مورد انتظار از محتوای نقشه"""
    logger.info("📋 استخراج نام فایل‌های مورد انتظار")

    expected_files = {
        'stl': [],
        'jpg': [],
        'zip': []
    }

    try:
        lines = mapping_content.strip().split('\n')

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or ':' not in line:
                continue

            try:
                original_filename, processed_filename = line.split(':', 1)
                original_filename = original_filename.strip()
                processed_filename = processed_filename.strip()

                # تعیین فایل‌های مورد نیاز
                requirements = determine_file_requirements(original_filename, processed_filename)

                base_name = processed_filename.rsplit('.', 1)[0]  # حذف پسوند
                logger.info(f"🔧 نام پایه استخراج شده: '{base_name}' از '{processed_filename}'")

                if requirements['stl_required']:
                    stl_filename = f"{base_name}.stl"
                    expected_files['stl'].append(stl_filename)
                    logger.info(f"➕ فایل STL اضافه شد: '{stl_filename}'")

                if requirements['jpg_required']:
                    jpg_filename = f"{base_name}.jpg"
                    expected_files['jpg'].append(jpg_filename)
                    logger.info(f"➕ فایل JPG اضافه شد: '{jpg_filename}'")

                if requirements['zip_required']:
                    zip_filename = f"{base_name}.zip"
                    expected_files['zip'].append(zip_filename)
                    logger.info(f"➕ فایل ZIP اضافه شد: '{zip_filename}'")

            except ValueError:
                logger.warning(f"⚠️ خط {line_num} نادیده گرفته شد: فرمت نادرست")
                continue

        logger.info(f"📊 خلاصه فایل‌های مورد انتظار:")
        logger.info(f"  STL: {len(expected_files['stl'])} فایل")
        logger.info(f"  JPG: {len(expected_files['jpg'])} فایل")
        logger.info(f"  ZIP: {len(expected_files['zip'])} فایل")

    except Exception as e:
        logger.error(f"💥 خطا در استخراج نام فایل‌های مورد انتظار: {e}")

    return expected_files


def is_filename_expected(mapping_content: str, filename: str) -> bool:
    """بررسی آیا نام فایل در لیست انتظار است"""
    logger.info(f"🔍 بررسی انتظار فایل: '{filename}'")
    log_filename_details(filename, "فایل مورد بررسی")

    expected_files = get_expected_filenames(mapping_content)

    # بررسی در همه انواع فایل
    for file_type, file_list in expected_files.items():
        logger.info(f"🔍 بررسی در لیست {file_type}: {file_list}")

        for expected_file in file_list:
            log_filename_details(expected_file, f"مورد انتظار {file_type}")

            # مقایسه دقیق
            if filename == expected_file:
                logger.info(f"✅ فایل '{filename}' در لیست {file_type} یافت شد (مقایسه دقیق)")
                return True

            # مقایسه نرمال‌شده
            normalized_filename = normalize_filename(filename)
            normalized_expected = normalize_filename(expected_file)

            if normalized_filename == normalized_expected:
                logger.info(f"✅ فایل '{filename}' در لیست {file_type} یافت شد (مقایسه نرمال‌شده)")
                return True

    logger.warning(f"❌ فایل '{filename}' در هیچ لیستی یافت نشد")
    return False


def get_file_type_from_extension(filename: str) -> str:
    """تعیین نوع فایل بر اساس پسوند"""
    logger.info(f"🔍 تشخیص نوع فایل: '{filename}'")

    if not filename or '.' not in filename:
        logger.warning(f"❌ فایل بدون پسوند: '{filename}'")
        return "unknown"

    extension = filename.rsplit('.', 1)[1].lower()
    logger.info(f"🔧 پسوند استخراج شده: '{extension}'")

    if extension == 'stl':
        logger.info("✅ نوع فایل: STL")
        return 'stl'
    elif extension in ['jpg', 'jpeg']:
        logger.info("✅ نوع فایل: JPG")
        return 'jpg'
    elif extension == 'zip':
        logger.info("✅ نوع فایل: ZIP")
        return 'zip'
    else:
        logger.warning(f"❌ نوع فایل نامشخص: '{extension}'")
        return 'unknown'


def validate_mapping_format(mapping_content: str) -> tuple[bool, str]:
    """اعتبارسنجی فرمت فایل نقشه"""
    logger.info("🔍 شروع اعتبارسنجی فرمت فایل نقشه")

    try:
        if not mapping_content or not mapping_content.strip():
            logger.error("❌ محتوای فایل نقشه خالی است")
            return False, "محتوای فایل نقشه خالی است"

        lines = mapping_content.strip().split('\n')
        valid_lines = 0
        logger.info(f"📄 تعداد خطوط: {len(lines)}")

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            logger.info(f"🔍 بررسی خط {line_num}: '{line}'")

            if not line:  # خط خالی قابل قبول است
                logger.info(f"ℹ️ خط {line_num}: خالی - نادیده گرفته شد")
                continue

            if ':' not in line:
                logger.error(f"❌ خط {line_num}: فرمت نادرست - ':' یافت نشد")
                return False, f"خط {line_num}: فرمت نادرست - ':' یافت نشد"

            parts = line.split(':', 1)
            if len(parts) != 2:
                logger.error(f"❌ خط {line_num}: فرمت نادرست - تعداد قسمت‌ها: {len(parts)}")
                return False, f"خط {line_num}: فرمت نادرست"

            original, processed = parts[0].strip(), parts[1].strip()
            logger.info(f"🔧 خط {line_num} - اصلی: '{original}' پردازش شده: '{processed}'")

            if not original or not processed:
                logger.error(f"❌ خط {line_num}: نام فایل خالی")
                return False, f"خط {line_num}: نام فایل خالی"

            valid_lines += 1
            logger.info(f"✅ خط {line_num}: معتبر")

        if valid_lines == 0:
            logger.error("❌ هیچ خط معتبر در فایل نقشه یافت نشد")
            return False, "هیچ خط معتبر در فایل نقشه یافت نشد"

        logger.info(f"✅ فایل نقشه معتبر است - {valid_lines} خط پردازش خواهد شد")
        return True, f"فایل نقشه معتبر است - {valid_lines} خط پردازش خواهد شد"

    except Exception as e:
        logger.error(f"💥 خطا در اعتبارسنجی: {str(e)}", exc_info=True)
        return False, f"خطا در اعتبارسنجی: {str(e)}"