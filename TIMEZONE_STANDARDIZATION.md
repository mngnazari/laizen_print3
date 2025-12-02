# استانداردسازی مدیریت Timezone

## خلاصه تغییرات

این تغییرات برای حل مشکل عدم هماهنگی در مدیریت timezone‌ها در پروژه انجام شده است.

## مشکلات قبلی

1. **تعریف چندگانه IRAN_TZ** در فایل‌های مختلف
2. **ذخیره‌سازی ناهماهنگ** در دیتابیس (بعضی UTC، بعضی زمان ایران)
3. **تبدیلات timezone پراکنده** در کدها
4. **آمیختگی منطق تبدیل تاریخ شمسی با timezone**

## راه‌حل پیاده‌سازی شده

### 1. ماژول مرکزی `utils/timezone_utils.py`

یک ماژول مرکزی برای تمام عملیات timezone ایجاد شده است که شامل:

- `now_utc()`: دریافت زمان فعلی UTC
- `now_iran()`: دریافت زمان فعلی ایران (به صورت naive)
- `utc_to_iran()`: تبدیل UTC به زمان ایران
- `iran_to_utc()`: تبدیل زمان ایران به UTC
- `format_shamsi()`: فرمت کردن datetime به تاریخ شمسی
- `format_shamsi_short()`: فرمت کوتاه تاریخ شمسی
- `parse_shamsi_datetime()`: پارس تاریخ شمسی به datetime

### 2. استاندارد ذخیره‌سازی

**قانون کلی:** همه datetime‌ها در دیتابیس به UTC ذخیره می‌شوند (naive datetime برای سازگاری با SQLite)

### 3. استاندارد نمایش

**قانون کلی:** تبدیل به زمان ایران و تاریخ شمسی فقط برای نمایش به کاربر انجام می‌شود

## فایل‌های به‌روزرسانی شده

### ماژول‌های اصلی

1. **utils/timezone_utils.py** - ماژول مرکزی جدید
2. **utils/broadcast_utils.py** - استفاده از ماژول مرکزی
3. **utils/delivery_grouping.py** - حذف تبدیلات پراکنده
4. **utils/notification_scheduler.py** - استفاده از توابع مرکزی

### Handlers

5. **handlers/file_submission.py** - حذف IRAN_TZ و استفاده از ماژول مرکزی
6. **handlers/delivery_scheduler.py** - ساده‌سازی محاسبات timezone
7. **handlers/editor.py** - استفاده از توابع مرکزی برای نمایش

### Database

8. **database/crud.py** - حذف IRAN_TZ و استفاده از now_utc()
9. **database/editor_crud.py** - استفاده از ماژول مرکزی

### Keyboards

10. **keyboards/editor.py** - ساده‌سازی مدیریت timezone

## نحوه استفاده

### دریافت زمان فعلی

```python
from utils.timezone_utils import now_utc, now_iran

# برای ذخیره در دیتابیس (UTC)
current_time = now_utc()

# برای نمایش به کاربر (زمان ایران)
iran_time = now_iran()
```

### فرمت کردن تاریخ شمسی

```python
from utils.timezone_utils import format_shamsi, format_shamsi_short

# فرمت کامل: "1404/07/18 - 14:30"
full_format = format_shamsi(datetime_utc, include_time=True)

# فرمت کوتاه: "07/18-14:30"
short_format = format_shamsi_short(datetime_utc)
```

### تبدیل timezone

```python
from utils.timezone_utils import utc_to_iran, iran_to_utc

# تبدیل UTC به ایران
iran_dt = utc_to_iran(utc_datetime)

# تبدیل ایران به UTC (برای ذخیره)
utc_dt = iran_to_utc(iran_datetime)
```

## مزایای این رویکرد

1. ✅ **یک منبع حقیقت:** همه توابع timezone در یک جا
2. ✅ **سادگی:** کدهای پیچیده timezone حذف شدند
3. ✅ **سازگاری:** همه قسمت‌های برنامه از یک روش استفاده می‌کنند
4. ✅ **قابل نگهداری:** تغییرات آینده فقط در یک فایل
5. ✅ **استاندارد:** ذخیره در UTC، نمایش در زمان محلی

## نکات مهم برای توسعه‌دهندگان

1. **همیشه** از `utils/timezone_utils` برای عملیات timezone استفاده کنید
2. **هرگز** IRAN_TZ را مستقیماً تعریف نکنید
3. **در دیتابیس** همیشه UTC ذخیره کنید
4. **برای نمایش** از توابع format استفاده کنید
5. **datetime.now()** را مستقیماً استفاده نکنید، از `now_utc()` یا `now_iran()` استفاده کنید

## Backward Compatibility

فایل `utils/broadcast_utils.py` به عنوان wrapper نگه داشته شده تا کدهای قدیمی کار کنند.

## تست

پس از این تغییرات، باید موارد زیر تست شوند:

- [ ] ثبت فایل جدید و چک زمان‌های edit_deadline و delivery_datetime
- [ ] نمایش تاریخ‌ها در منوهای ادیتور
- [ ] broadcast messages با زمان‌بندی
- [ ] گزارشات و آمار با فیلتر تاریخ
- [ ] تقویم تعطیلات

## نویسندگان

- تغییرات توسط Claude انجام شده است
- تاریخ: 2025-12-02
