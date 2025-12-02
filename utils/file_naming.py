# utils/file_naming.py

# در utils/file_naming.py اصلاح کنید:

def generate_operator_filename(customer_code: str, print_count: int, original_filename: str,
                               max_length: int = 40) -> str:
    """تولید نام فایل برای ارسال به اپراتور"""

    # ساخت prefix - فقط اگر تعداد بیشتر از 1 باشد
    if print_count > 1:
        prefix = f"{customer_code}-X{print_count}-"
    else:
        prefix = f"{customer_code}-"

    # محاسبه فضای باقی‌مانده برای نام اصلی
    remaining_length = max_length - len(prefix)

    # کوتاه کردن نام فایل در صورت نیاز
    if len(original_filename) > remaining_length:
        name_part, extension = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, '')
        extension_part = f".{extension}" if extension else ""

        available_for_name = remaining_length - len(extension_part)

        if available_for_name > 0:
            truncated_name = name_part[:available_for_name]
            final_filename = f"{truncated_name}{extension_part}"
        else:
            final_filename = name_part[:remaining_length]
    else:
        final_filename = original_filename

    return f"{prefix}{final_filename}"


def parse_operator_filename(operator_filename: str) -> dict:
    """تجزیه نام فایل اپراتور برای بازگرداندن اطلاعات اصلی"""
    try:
        # جدا کردن قسمت‌های مختلف
        parts = operator_filename.split('-', 2)
        if len(parts) >= 3:
            customer_code = parts[0]
            print_count = int(parts[1][1:])  # حذف X از ابتدا
            original_filename = parts[2]

            return {
                'customer_code': customer_code,
                'print_count': print_count,
                'original_filename': original_filename
            }
    except:
        pass

    return None