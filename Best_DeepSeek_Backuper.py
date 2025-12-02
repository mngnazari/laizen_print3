import os
import zipfile
import re
import jdatetime
from pathlib import Path


def select_bot_folder(backup_base_dir):
    """انتخاب یا ایجاد پوشه بات"""
    os.makedirs(backup_base_dir, exist_ok=True)

    # لیست پوشه‌های موجود
    existing_folders = [f for f in os.listdir(backup_base_dir)
                        if os.path.isdir(os.path.join(backup_base_dir, f))]

    if existing_folders:
        print("\nپوشه‌های بات موجود:")
        for i, folder in enumerate(existing_folders, 1):
            print(f"{i}. {folder}")

        print(f"{len(existing_folders) + 1}. ایجاد پوشه جدید")

        choice = input("\nلطفاً شماره پوشه مورد نظر را انتخاب کنید: ")

        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(existing_folders):
                return os.path.join(backup_base_dir, existing_folders[choice_num - 1])
            elif choice_num == len(existing_folders) + 1:
                # ایجاد پوشه جدید
                new_folder = input("نام پوشه جدید برای بات را وارد کنید: ")
                new_folder_path = os.path.join(backup_base_dir, new_folder)
                os.makedirs(new_folder_path, exist_ok=True)
                return new_folder_path
            else:
                print("انتخاب نامعتبر. پوشه پیش‌فرض ایجاد شد.")
        except ValueError:
            print("ورودی نامعتبر. پوشه پیش‌فرض ایجاد شد.")

    # اگر پوشه‌ای وجود ندارد یا انتخاب نامعتبر بود
    default_folder = input("نام پوشه برای بات جدید را وارد کنید: ")
    default_folder_path = os.path.join(backup_base_dir, default_folder)
    os.makedirs(default_folder_path, exist_ok=True)
    return default_folder_path


def get_next_backup_number(backup_dir):
    """دریافت شماره بعدی برای بک‌آپ"""
    if not os.path.exists(backup_dir):
        return 1

    existing_files = [f for f in os.listdir(backup_dir) if f.endswith('.zip')]
    numbers = []

    for file in existing_files:
        # استخراج شماره از ابتدای نام فایل
        match = re.match(r'^(\d+)', file)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1


def get_description_with_option(backup_dir):
    """دریافت توضیحات با امکان اضافه کردن به توضیحات قبلی"""
    log_file = os.path.join(backup_dir, 'backups_log.txt')

    # بررسی وجود فایل لاگ و دریافت آخرین توضیحات
    last_description = ""
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # پیدا کردن آخرین توضیحات
            matches = re.findall(r'توضیحات: (.*?)(?=\n=|\Z)', content, re.DOTALL)
            if matches:
                last_description = matches[0].strip()

    if last_description:
        print(f"\nآخرین توضیحات:\n{last_description}\n")
        print("1. اضافه کردن به توضیحات قبلی")
        print("2. وارد کردن توضیحات جدید")

        choice = input("\nلطفاً گزینه مورد نظر را انتخاب کنید (1 یا 2): ")

        if choice == "1":
            addition = input("توضیحات جدید خود را اضافه کنید:\n")
            return last_description + "\n" + addition

    # اگر توضیحات قبلی وجود ندارد یا کاربر گزینه 2 را انتخاب کرده
    return input("\nتوضیحات کامل را وارد کنید:\n")


def update_backup_log(backup_dir, backup_number, timestamp, commit_message, description):
    """به‌روزرسانی فایل لاگ کلی بک‌آپ‌ها"""
    log_file = os.path.join(backup_dir, 'backups_log.txt')

    log_entry = f"""--- بک‌آپ شماره {backup_number} ---
تاریخ: {timestamp}
عنوان: {commit_message}
توضیحات: {description}
{'=' * 50}
"""

    # اگر فایل لاگ وجود ندارد، ایجاد می‌کنیم
    if not os.path.exists(log_file):
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("فهرست بک‌آپ‌های ایجاد شده\n")
            f.write("=" * 50 + "\n\n")

    # اضافه کردن ورودی جدید به ابتدای فایل
    with open(log_file, 'r+', encoding='utf-8') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(log_entry + content)


def create_backup_zip(backup_dir, backup_number, commit_message, description):
    """ایجاد فایل زیپ بک‌آپ"""
    project_root = os.getcwd()

    # استثناها
    EXCLUDED_DIRS = {
        '__pycache__', '.pytest_cache', '.git', '.vscode', '.idea',
        'venv', 'env', '.venv', 'virtualenv', 'node_modules', 'backups'
    }
    EXCLUDED_FILES = {'.gitignore', '.gitattributes', '.env', 'env.bak'}
    EXCLUDED_EXTENSIONS = {'.pyc', '.pyo', '.log', '.tmp', '.bak', '.swp', '.db', '.sqlite3', '.zip'}

    # نام فایل بک‌آپ
    now = jdatetime.datetime.now()
    timestamp = now.strftime("%Y%m%d-%H%M")
    clean_commit_msg = re.sub(r'[^\w\sآ-ی]', '', commit_message).replace(' ', '-')[:50]
    zip_filename = f"{backup_number:03d}-{timestamp}-{clean_commit_msg}.zip"
    zip_path = os.path.join(backup_dir, zip_filename)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # ایجاد فایل توضیحات در زیپ
        description_file = "توضیحات.txt"
        with open(description_file, 'w', encoding='utf-8') as f:
            f.write(description)

        zipf.write(description_file, description_file)
        os.remove(description_file)  # حذف فایل موقت

        # افزودن فایل‌های پروژه
        for root, dirs, files in os.walk(project_root):
            # حذف پوشه‌های استثنا
            dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.')]

            for file in files:
                # رد کردن فایل‌های زیپ
                if file.endswith('.zip'):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_root)

                # بررسی استثناها
                if (file in EXCLUDED_FILES or
                        any(file.endswith(ext) for ext in EXCLUDED_EXTENSIONS) or
                        any(ex_dir in relative_path.split(os.sep) for ex_dir in EXCLUDED_DIRS)):
                    continue

                zipf.write(file_path, relative_path)

    return zip_path


if __name__ == "__main__":
    # مسیر اصلی ذخیره بک‌آپ‌ها
    backup_base_dir = r"C:\Bot_Backups"

    # انتخاب پوشه بات
    bot_folder = select_bot_folder(backup_base_dir)

    # دریافت شماره بک‌آپ بعدی
    backup_number = get_next_backup_number(bot_folder)

    # دریافت اطلاعات از کاربر
    commit_msg = input("\nعنوان بک‌آپ را وارد کنید: ")
    description = get_description_with_option(bot_folder)

    # ایجاد بک‌آپ
    zip_file = create_backup_zip(bot_folder, backup_number, commit_msg, description)

    # به‌روزرسانی فایل لاگ
    now = jdatetime.datetime.now()
    timestamp = now.strftime("%Y/%m/%d %H:%M")
    update_backup_log(bot_folder, backup_number, timestamp, commit_msg, description)

    print(f"\n!فایل پشتیبان با موفقیت ایجاد شد: {zip_file}")