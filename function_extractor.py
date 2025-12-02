import os
import re

# مسیر اصلی پروژه (محل اجرای فایل)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(ROOT_DIR, "project_tree_summary.txt")

# پوشه‌هایی که باید حذف شوند
EXCLUDE_DIR_NAMES = {
    ".venv", "venv", "env", "__pycache__", ".git", "build", "dist", ".idea",
    ".mypy_cache", ".pytest_cache", "node_modules", "site-packages", "egg-info", "dist-info"
}
EXCLUDE_KEYWORDS = ["venv", "env", "site-packages", "egg-info"]

# الگوهای استخراج بخش‌های مهم کد
patterns = {
    "class": re.compile(r"^[ \t]*class\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    "function": re.compile(r"^[ \t]*def\s+([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    "handlers": re.compile(r"(CallbackQueryHandler|CommandHandler|MessageHandler|ConversationHandler)", re.MULTILINE),
    "callback_functions": re.compile(r"CallbackQueryHandler\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)", re.MULTILINE),
    "commands": re.compile(r"CommandHandler\s*\(\s*['\"]([^'\"]+)['\"]", re.MULTILINE),
    "conversation_states": re.compile(r"ConversationHandler\s*\([^)]*states\s*=\s*\{([^}]+)\}", re.MULTILINE | re.DOTALL),
    "entry_points": re.compile(r"entry_points\s*=\s*\[[^\]]+\]", re.MULTILINE),
    "fallbacks": re.compile(r"fallbacks\s*=\s*\[[^\]]+\]", re.MULTILINE),
    "sqlalchemy_models": re.compile(r"class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(Base\)", re.MULTILINE),
}

MAX_DISPLAY = 20


def is_excluded_dir(dirname: str) -> bool:
    """بررسی می‌کند که آیا پوشه باید نادیده گرفته شود یا نه."""
    name = dirname.lower()
    if name in EXCLUDE_DIR_NAMES:
        return True
    if any(kw in name for kw in EXCLUDE_KEYWORDS):
        return True
    if dirname.startswith("."):
        return True
    return False


def summarize_file(file_path: str) -> dict:
    """متن فایل را می‌خواند و الگوهای تعریف‌شده را استخراج می‌کند."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            content = f.read()
    except Exception as e:
        return {"error": f"Error reading file: {e}"}

    details = {}
    for key, pattern in patterns.items():
        matches = pattern.findall(content)
        if not matches:
            details[key] = []
            continue

        # در صورت وجود tuple، بازکردن آنها
        flat = []
        for m in matches:
            if isinstance(m, tuple):
                for part in m:
                    if isinstance(part, str) and part.strip():
                        flat.append(part.strip())
            elif isinstance(m, str):
                flat.append(m.strip())

        uniq = sorted(set(flat))
        details[key] = uniq
    return details


def ensure_node(root_node: dict, relpath: str) -> dict:
    """اطمینان حاصل می‌کند که مسیر نسبی در ساختار درختی وجود دارد."""
    if relpath in (".", ""):
        return root_node
    parts = relpath.split(os.sep)
    node = root_node
    for p in parts:
        if not p:
            continue
        if p not in node["dirs"]:
            node["dirs"][p] = {"dirs": {}, "files": {}}
        node = node["dirs"][p]
    return node


def build_tree_structure() -> tuple:
    """پوشه‌ها را پیمایش می‌کند و ساختار پروژه را می‌سازد."""
    root_node = {"dirs": {}, "files": {}}
    total_files = 0

    for current_dir, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if not is_excluded_dir(d)]
        rel = os.path.relpath(current_dir, ROOT_DIR)
        node = ensure_node(root_node, rel)

        for f in sorted(files):
            if not f.endswith(".py") or f.startswith("."):
                continue
            full_path = os.path.join(current_dir, f)
            details = summarize_file(full_path)
            node["files"][f] = details
            total_files += 1

    return root_node, total_files


def pretty_print(node: dict, prefix: str = "") -> list:
    """درخت پروژه را به صورت زیبا و خوانا چاپ می‌کند."""
    lines = []
    dir_names = sorted(node["dirs"].keys())
    file_names = sorted(node["files"].keys())

    entries = [(n, "dir") for n in dir_names] + [(n, "file") for n in file_names]

    for i, (name, typ) in enumerate(entries):
        is_last = i == len(entries) - 1
        branch = "└── " if is_last else "├── "
        next_prefix = prefix + ("    " if is_last else "│   ")

        if typ == "dir":
            lines.append(f"{prefix}{branch}{name}\\")
            lines.extend(pretty_print(node["dirs"][name], next_prefix))
        else:
            lines.append(f"{prefix}{branch}{name}")
            details = node["files"].get(name, {})
            if not details:
                lines.append(f"{next_prefix}• (no details)")
                continue

            for key, items in details.items():
                if items:
                    display = ", ".join(items[:MAX_DISPLAY])
                    more = f" (+{len(items)-MAX_DISPLAY} more)" if len(items) > MAX_DISPLAY else ""
                    lines.append(f"{next_prefix}• {key} ({len(items)}): {display}{more}")
            if all(not v for v in details.values()):
                lines.append(f"{next_prefix}• (no significant definitions)")

    return lines


def main():
    print(f"📂 Scanning project: {ROOT_DIR}\n")
    root_node, total_files = build_tree_structure()

    lines = [ROOT_DIR]
    lines.extend(pretty_print(root_node))
    tree_output = "\n".join(lines)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(tree_output)

    print(f"✅ ساختار درختی پروژه در '{OUTPUT_FILE}' ذخیره شد.")
    print(f"📄 تعداد فایل‌های پایتون بررسی‌شده: {total_files}")


if __name__ == "__main__":
    main()
