import os


def list_root_items():
    """لیست فایل‌ها و پوشه‌های موجود در ریشه پروژه"""
    items = []
    for item in os.listdir('.'):
        # نادیده گرفتن پوشه‌های مخفی و __pycache__ اما شامل شدن فایل .env
        if (item.startswith('.') and not item == '.env' and os.path.isdir(item)) or item == '__pycache__':
            continue

        full_path = os.path.normpath(item)
        if os.path.isfile(item) and (item.endswith('.py') or item == '.env'):
            items.append(('file', full_path))
        elif os.path.isdir(item):
            items.append(('folder', full_path))
    return items


def collect_python_files_in_folder(folder_path):
    """جمع‌آوری بازگشتی تمام فایل‌های پایتون و فایل .env در یک پوشه"""
    python_files = []
    for root, dirs, files in os.walk(folder_path):
        # حذف پوشه‌های مخفی و __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']

        for file in files:
            # شامل شدن فایل‌های پایتون و فایل .env
            if file.endswith('.py') or file == '.env':
                full_path = os.path.normpath(os.path.join(root, file))
                python_files.append(full_path)
    return python_files


def generate_project_structure(file_paths):
    """تولید ساختار درختی پروژه با قابلیت پرش به بخش‌ها"""
    structure = {}

    # سازماندهی فایل‌ها بر اساس مسیر
    for path in file_paths:
        parts = path.split(os.sep)
        current_level = structure

        for part in parts[:-1]:
            if part not in current_level:
                current_level[part] = {}
            current_level = current_level[part]

        current_level[parts[-1]] = path

    # تابع بازگشتی برای تولید نمایش درختی
    def build_tree(level, indent=0, parent_path=""):
        tree_str = ""
        prefix = "│   " * indent
        items = sorted(level.items(), key=lambda x: (isinstance(x[1], dict), x[0]))

        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = prefix + ("└── " if is_last else "├── ")

            if isinstance(value, dict):
                full_path = os.path.join(parent_path, name) if parent_path else name
                tree_str += f"{prefix}{'└── ' if is_last else '├── '}{name}/\n"
                tree_str += build_tree(value, indent + 1, full_path)
            else:
                # ایجاد لینک به بخش مربوطه
                section_id = value.replace(os.sep, "_").replace(".", "_")
                tree_str += f"{current_prefix}[{name}](#{section_id})\n"

        return tree_str

    return "ساختار پروژه:\n" + build_tree(structure) + "\n\n"


def combine_files(file_paths, output_file='combined_modules.txt'):
    """ترکیب محتوای فایل‌های پایتون و .env در یک فایل متنی"""
    if os.path.exists(output_file):
        with open(output_file, 'w') as f:
            f.write('')

    with open(output_file, 'a', encoding='utf-8') as out_file:
        # تولید و نوشتن ساختار پروژه
        structure = generate_project_structure(file_paths)
        out_file.write("# ساختار پروژه\n\n")
        out_file.write(structure)
        out_file.write("=" * 80 + "\n\n")

        # نوشتن محتوای هر فایل
        for i, path in enumerate(file_paths, 1):
            if not os.path.exists(path):
                print(f"خطا: فایل {path} یافت نشد!")
                continue

            try:
                with open(path, 'r', encoding='utf-8') as in_file:
                    content = in_file.read()

                # ایجاد لنگر برای فایل فعلی
                section_id = path.replace(os.sep, "_").replace(".", "_")
                out_file.write(f"\n\n<a id='{section_id}'></a>\n")
                out_file.write(f"{'=' * 50}\n")
                out_file.write(f"# بخش {i}: {path}\n")
                out_file.write(f"{'=' * 50}\n\n")
                out_file.write(content)

                print(f"فایل {path} با موفقیت اضافه شد.")

            except Exception as e:
                print(f"خطا در پردازش فایل {path}: {str(e)}")

    print(f"\nترکیب فایل‌ها با موفقیت در فایل {output_file} ذخیره شد.")


def get_user_selection(root_items):
    """دریافت انتخاب‌های کاربر از محتویات ریشه"""
    selected_files = []
    history_stack = []  # برای پیگیری آخرین عملیات
    selected_set = set()  # جلوگیری از انتخاب تکراری

    print("\nدستورالعمل:")
    print("- برای انتخاب فایل/پوشه، عدد مربوط به آن را وارد کنید")
    print("- برای ترکیب همه موارد، کلید 'a' را بزنید")
    print("- برای پایان انتخاب‌ها و شروع ترکیب، کلید 's' را بزنید")
    print("- برای لغو آخرین انتخاب، کلید 'u' را بزنید")
    print("- برای مشاهده مجدد لیست، کلید 'l' را بزنید")

    while True:
        print("\n" + "-" * 50)
        print("موجودی ریشه پروژه:")
        for i, (item_type, item_path) in enumerate(root_items, 1):
            prefix = "[فایل]" if item_type == "file" else "[پوشه]"
            print(f"{i}: {prefix} {item_path}")

        print(f"\nتعداد فایل‌های انتخاب شده: {len(selected_files)}")
        print("عملیات مورد نظر را انتخاب کنید (عدد/a/s/u/l): ")
        user_input = input().strip().lower()

        # عملیات ویژه
        if user_input == 'a':  # انتخاب همه
            new_files = []
            for item_type, item_path in root_items:
                if item_type == "file" and item_path not in selected_set:
                    new_files.append(item_path)
                    selected_set.add(item_path)
                elif item_type == "folder":
                    folder_files = collect_python_files_in_folder(item_path)
                    for f in folder_files:
                        if f not in selected_set:
                            new_files.append(f)
                            selected_set.add(f)

            selected_files.extend(new_files)
            history_stack.append(new_files)
            print(f"تعداد {len(new_files)} فایل جدید اضافه شد.")
            continue

        if user_input == 's':  # شروع ترکیب
            if not selected_files:
                print("هیچ فایلی انتخاب نشده است!")
                continue
            return selected_files

        if user_input == 'u':  # لغو آخرین انتخاب
            if history_stack:
                last_selection = history_stack.pop()
                for f in last_selection:
                    if f in selected_set:
                        selected_files.remove(f)
                        selected_set.remove(f)
                print(f"آخرین انتخاب لغو شد ({len(last_selection)} فایل حذف شد).")
            else:
                print("تاریخچه‌ای برای لغو وجود ندارد!")
            continue

        if user_input == 'l':  # نمایش مجدد لیست
            continue

        # انتخاب بر اساس عدد
        try:
            index = int(user_input) - 1
            if 0 <= index < len(root_items):
                item_type, item_path = root_items[index]

                if item_type == "file":
                    if item_path in selected_set:
                        print("این فایل قبلاً انتخاب شده است!")
                    else:
                        selected_files.append(item_path)
                        selected_set.add(item_path)
                        history_stack.append([item_path])
                        print(f"فایل {item_path} اضافه شد.")

                elif item_type == "folder":
                    folder_files = collect_python_files_in_folder(item_path)
                    new_files = [f for f in folder_files if f not in selected_set]

                    if not new_files:
                        print("هیچ فایل جدیدی در این پوشه یافت نشد!")
                    else:
                        selected_files.extend(new_files)
                        selected_set.update(new_files)
                        history_stack.append(new_files)
                        print(f"تعداد {len(new_files)} فایل از پوشه {item_path} اضافه شد.")
            else:
                print("عدد وارد شده خارج از محدوده است!")
        except ValueError:
            print("ورودی نامعتبر! لطفاً عدد یا کلید عملیات را وارد کنید.")


if __name__ == "__main__":
    print("ترکیب‌کننده فایل‌های پایتون - نسخه پیشرفته")
    print("فقط محتویات ریشه پروژه نمایش داده می‌شود\n")

    root_items = list_root_items()

    if not root_items:
        print("هیچ فایل یا پوشه‌ای در ریشه پروژه یافت نشد!")
        exit()

    selected_files = get_user_selection(root_items)
    combine_files(selected_files)

    print("\nعملیات با موفقیت به پایان رسید!")
    print("می‌توانید نتایج را در فایل 'combined_modules.txt' مشاهده کنید.")