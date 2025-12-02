import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی
load_dotenv()

# Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# User IDs
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# تبدیل رشته‌های جداشده با کاما به لیست اعداد
OPERATORS_IDS = [int(id.strip()) for id in os.getenv('OPERATORS_IDS', '').split(',') if id.strip()]
EDITORS_IDS = [int(id.strip()) for id in os.getenv('EDITORS_IDS', '').split(',') if id.strip()]
VISITORS_IDS = [int(id.strip()) for id in os.getenv('VISITORS_IDS', '').split(',') if id.strip()]

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///print3d_orders.db')

# بررسی اینکه متغیرهای ضروری تنظیم شده‌اند
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN در فایل .env تنظیم نشده است!")

if ADMIN_ID == 0:
    raise ValueError("ADMIN_ID در فایل .env تنظیم نشده است!")