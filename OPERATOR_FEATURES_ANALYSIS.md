# تحلیل کامل کدهای موجود اپراتور

## تاریخ: 3 دسامبر 2025

این سند تحلیل جامعی از تمام فرایندهای پیاده‌سازی شده برای اپراتور در بات ارائه می‌دهد.

---

## 📁 فایل‌های مربوط به اپراتور

### 1. Handlers
- `handlers/operator.py` - مدیریت منو، صدور فاکتور، آمار
- `handlers/operator_files.py` - مدیریت فایل‌ها و ارسال به اپراتور

### 2. Keyboards
- `keyboards/operator.py` - کیبوردهای منوی اصلی و فاکتور
- `keyboards/operator_files.py` - کیبوردهای مدیریت فایل‌ها

---

## 🔧 فرایندهای پیاده‌سازی شده

### 1️⃣ منوی اصلی اپراتور

**فایل:** `handlers/operator.py`
**تابع:** `handle_operator_menu()`, `show_operator_main_menu()`

**عملکرد:**
- نمایش منوی اصلی با کیبورد شیشه‌ای (inline)
- دسترسی به زیرمنوهای مختلف:
  * صدور فاکتور
  * مدیریت فایل‌ها
  * آمار کارها
  * لیست مشتریان
  * تنظیمات

**دکمه‌های موجود:**
```
📋 صدور فاکتور
📁 فایل‌ها (مدیریت فایل‌های پرینت)
📊 آمار من
👥 مشتریان
⚙️ تنظیمات
```

---

### 2️⃣ فرایند صدور فاکتور (Invoice Process)

**فایل:** `handlers/operator.py`
**توابع:** `show_customers_for_invoice()`, `handle_customer_file_selection()`, `get_weight_handler()`, `get_photo_handler()`

**گردش کار (Workflow):**

#### مرحله 1: انتخاب مشتری
```
show_customers_for_invoice()
│
├─ Query: get_customers_with_pending_orders(db)
├─ نمایش لیست مشتریانی که سفارش pending دارند
└─ دکمه برای هر مشتری: select_customer_{customer_id}
```

#### مرحله 2: مدیریت فایل‌های مشتری
```
handle_customer_file_selection()
│
├─ دریافت فایل‌های pending مشتری
├─ نمایش لیست فایل‌ها با وضعیت (None/Success/Failed)
├─ دکمه‌های تعاملی:
│   ├─ toggle_file_{order_id} - تغییر وضعیت فایل
│   │   └─ چرخه: None → Success → Failed → Success
│   └─ issue_invoice_{customer_id} - صدور فاکتور
└─ Context Storage:
    ├─ file_statuses = {order_id: status}
    ├─ current_customer_id
    └─ successful_files = [order_ids]
```

**نمایش وضعیت:**
- ⚪ دایره خالی: تعیین تکلیف نشده (None)
- 🟢 دایره سبز: پرینت موفق (Success)
- 🔴 دایره قرمز: پرینت ناموفق (Failed)

#### مرحله 3: دریافت وزن
```
get_weight_handler()
│
├─ دریافت وزن به گرم از اپراتور
├─ اعتبارسنجی (باید عدد مثبت باشد)
├─ محاسبه مبلغ کل:
│   └─ total_amount = weight × price_per_gram
└─ ذخیره در context: invoice_weight
```

**State:** `GET_WEIGHT`

#### مرحله 4: دریافت عکس و ایجاد فاکتور
```
get_photo_handler()
│
├─ دریافت عکس مدل‌های پرینت شده
├─ ایجاد فاکتور:
│   ├─ customer_id
│   ├─ operator_id
│   ├─ weight_grams
│   ├─ price_per_gram
│   ├─ total_amount (محاسبه شده)
│   └─ photo_file_id
│
├─ به‌روزرسانی وضعیت فایل‌ها:
│   ├─ Successful files → status = "invoiced"
│   └─ Failed files → status = "failed"
│
├─ ارسال تأیید به اپراتور
└─ ارسال فاکتور + عکس به مشتری
```

**State:** `GET_PHOTO`

**فاکتور شامل:**
- 🆔 شماره فاکتور
- ⚖️ وزن (گرم)
- 💰 قیمت هر گرم
- 💵 مبلغ کل
- 📅 تاریخ صدور
- 📊 آمار: تعداد فایل‌های موفق/ناموفق
- 📸 عکس مدل‌های پرینت شده

---

### 3️⃣ مدیریت فایل‌های پرینت

**فایل:** `handlers/operator_files.py`
**توابع:** `show_operator_files_main()`, `show_delivery_customers()`, `send_customer_files()`, `send_all_delivery_files()`

**گردش کار:**

#### مرحله 1: انتخاب زمان تحویل
```
show_operator_files_main()
│
├─ Query: group_files_by_delivery_time()
├─ نمایش لیست زمان‌های تحویل با تعداد فایل
└─ دکمه برای هر زمان: operator_delivery_{time}
```

#### مرحله 2: انتخاب مشتری
```
show_delivery_customers()
│
├─ دریافت مشتریان برای زمان تحویل خاص
├─ گروه‌بندی فایل‌ها بر اساس مشتری
├─ نمایش دکمه‌ها:
│   ├─ operator_customer_{code}_{time} - فایل‌های یک مشتری
│   └─ operator_send_all_{time} - همه فایل‌ها
└─ Tracking: جلوگیری از ارسال مجدد (✅)
```

#### مرحله 3: ارسال فایل‌ها
```
send_customer_files() / send_all_delivery_files()
│
├─ Query فایل‌های pending
├─ تبدیل زمان شمسی به میلادی
├─ ارسال فایل‌ها به اپراتور:
│   └─ send_files_to_operator(files)
│       ├─ نام‌گذاری خودکار: generate_operator_filename()
│       ├─ Caption شامل:
│       │   ├─ نام مشتری
│       │   ├─ کد مشتری
│       │   ├─ تعداد پرینت
│       │   └─ توضیحات
│       └─ ارسال به صورت document
└─ Tracking: context.chat_data['sent_files']
```

**ویژگی Tracking:**
- جلوگیری از ارسال مجدد فایل‌های ارسال شده
- نمایش علامت ✅ برای مشتریان ارسال شده
- Key format: `{delivery_time}_{customer_code}`

---

### 4️⃣ آمار اپراتور

**فایل:** `handlers/operator.py`
**تابع:** `show_operator_stats()`

**اطلاعات نمایش داده شده:**
- 📊 تعداد کل فاکتورهای صادر شده
- 💵 مجموع درآمد
- ⚖️ مجموع وزن کارها
- 📈 میانگین وزن هر فاکتور
- 🏆 آمار عملکرد

**Query:**
```sql
SELECT * FROM invoices
WHERE operator_id = {operator_id}
```

---

### 5️⃣ لیست مشتریان

**فایل:** `handlers/operator.py`
**تابع:** `show_customers_list()`

**عملکرد:**
- نمایش لیست همه مشتریان
- اطلاعات نمایش داده شده:
  * نام کامل
  * کد مشتری
  * شماره تلفن
  * تعداد سفارشات
- فیلتر بر اساس سفارش pending

---

### 6️⃣ تنظیمات اپراتور

**فایل:** `handlers/operator.py`
**تابع:** `show_operator_settings()`

**قابلیت‌ها:**
- مشاهده تنظیمات فعلی
- تغییر تنظیمات (در حال توسعه)

---

## 🗂️ ساختار دیتابیس

### جدول: `invoices`
```python
Invoice:
├─ id (Primary Key)
├─ customer_id (FK → users.id)
├─ operator_id (FK → users.id)
├─ file_order_id (FK → file_orders.id, nullable)
├─ weight_grams (Float)
├─ price_per_gram (Float)
├─ total_amount (Float, calculated)
├─ photo_file_id (String, Telegram File ID)
└─ created_at (DateTime)
```

### جدول: `file_orders` (تغییرات)
```python
FileOrder:
├─ status (String)
│   ├─ "pending" - در انتظار پردازش
│   ├─ "confirmed" - تایید شده
│   ├─ "invoiced" - فاکتور شده (پرینت موفق)
│   ├─ "failed" - پرینت ناموفق
│   └─ "cancelled" - لغو شده
├─ has_invoice (Boolean, default=False)
├─ sent_to_operator (Boolean, default=False)
├─ operator_filename (String, nullable)
└─ sent_to_operator_at (DateTime, nullable)
```

---

## 🔄 Conversation Handler (ConversationHandler)

**فایل:** `handlers/operator.py`

**States:**
```python
GET_WEIGHT = 0  # دریافت وزن
GET_PHOTO = 1   # دریافت عکس
```

**Flow:**
```
START (issue_invoice_)
  ↓
GET_WEIGHT (دریافت وزن از اپراتور)
  ↓
GET_PHOTO (دریافت عکس)
  ↓
END (ایجاد فاکتور و ارسال)
```

**Cancel Handler:**
- `cancel_invoice_handler()` - لغو فرایند در هر مرحله

---

## 📊 Utilities استفاده شده

### 1. `utils/file_naming.py`
```python
generate_operator_filename(customer_code, file_name, print_count)
│
└─ Format: "{customer_code}_{original_name}_x{count}.ext"
    Example: "c25_ring_x3.stl"
```

### 2. `utils/delivery_grouping.py`
```python
group_files_by_delivery_time(files)
├─ گروه‌بندی بر اساس delivery_datetime
└─ Return: Dict[datetime, List[FileOrder]]

group_files_by_customer(files)
├─ گروه‌بندی بر اساس customer_code
└─ Return: Dict[str, List[FileOrder]]

count_total_ready_files()
├─ شمارش فایل‌های pending
└─ Return: int

count_ready_files_by_delivery(delivery_time)
├─ شمارش فایل‌های یک زمان تحویل
└─ Return: int
```

---

## 🎯 نقاط قوت پیاده‌سازی فعلی

### ✅ مزایا:
1. **فرایند کامل صدور فاکتور**: از انتخاب مشتری تا ارسال فاکتور
2. **Tracking**: جلوگیری از ارسال مجدد فایل‌ها
3. **وضعیت‌های متعدد**: Success/Failed برای هر فایل
4. **Conversation Handler**: فرایند قدم به قدم با state management
5. **نام‌گذاری خودکار**: فایل‌ها با فرمت یکسان به اپراتور ارسال می‌شوند
6. **آمار جامع**: نمایش عملکرد اپراتور
7. **گروه‌بندی هوشمند**: بر اساس زمان تحویل و مشتری

---

## 🔴 نقاط ضعف و محدودیت‌ها

### ❌ مشکلات فعلی:

1. **عدم ادغام با ادیتور**:
   - فایل‌های ادیت شده جداگانه مدیریت می‌شوند
   - نیاز به لینک بین فایل اصلی و فایل ادیت شده

2. **محدودیت Tracking**:
   - `context.chat_data` در session فعلی ذخیره می‌شود
   - اگر بات restart شود، tracking از بین می‌رود
   - راه‌حل: ذخیره `sent_to_operator` در دیتابیس

3. **عدم پشتیبانی از ویرایش فاکتور**:
   - بعد از صدور فاکتور، امکان ویرایش نیست
   - نیاز به قابلیت اصلاح اشتباهات

4. **عدم تأیید قبل از ارسال**:
   - فایل‌ها بدون تأیید نهایی ارسال می‌شوند
   - خطر ارسال اشتباه به اپراتور

5. **محدودیت در مدیریت زمان**:
   - استفاده از jdatetime برای تبدیل (نه timezone_utils)
   - احتمال مشکلات timezone

6. **عدم لاگ کامل**:
   - فعالیت‌های اپراتور لاگ نمی‌شوند
   - سخت‌تر کردن debugging

7. **UI/UX**:
   - کیبوردها می‌توانند بهبود یابند
   - نیاز به feedback بهتر برای کاربر

---

## 🚀 پیشنهادات برای توسعه

### 1. ادغام با سیستم ادیتور
```
FileOrder
├─ edited_file_id (FK → FileOrder.id, nullable)
├─ is_edited (Boolean, default=False)
└─ editor_notes (Text, nullable)
```

### 2. بهبود Tracking
```python
FileOrder.sent_to_operator = True
FileOrder.sent_to_operator_at = datetime.now()
FileOrder.operator_filename = generated_name
```

### 3. سیستم Log
```python
OperatorActivity:
├─ operator_id
├─ action (view_files, send_files, issue_invoice)
├─ target (customer_id, file_ids, invoice_id)
├─ timestamp
└─ details (JSON)
```

### 4. بهبود فرایند فاکتور
- تأیید نهایی قبل از ارسال
- امکان ویرایش فاکتور
- پیش‌نمایش فاکتور
- ارسال چند عکس
- افزودن نوتیفیکیشن به مشتری

### 5. استاندارد کردن Timezone
- استفاده از `timezone_utils` به جای `jdatetime`
- همسان‌سازی با بقیه سیستم

### 6. Dashboard اپراتور
- نمایش فایل‌های در حال پرینت
- وضعیت real-time
- فیلترهای پیشرفته

---

## 📝 نتیجه‌گیری

**وضعیت کلی:** 🟢 پایه خوب، نیاز به توسعه و بهبود

**امتیاز ویژگی‌ها:**
- ✅ صدور فاکتور: 8/10
- ✅ مدیریت فایل‌ها: 7/10
- ⚠️ Tracking: 5/10
- ⚠️ UI/UX: 6/10
- ❌ Integration با ادیتور: 2/10
- ❌ Logging: 3/10

**توصیه:** ابتدا بهبود Tracking و ادغام با ادیتور، سپس بهبود UI/UX و افزودن Dashboard
