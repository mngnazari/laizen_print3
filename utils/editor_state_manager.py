# utils/editor_state_manager.py
from sqlalchemy.orm import Session
from typing import Dict, Optional
import logging

import database.editor_crud as editor_crud

logger = logging.getLogger(__name__)


class EditorStateManager:
    """مدیریت وضعیت‌های مختلف ادیتور"""

    STATES = {
        'idle': 'آماده دریافت فایل جدید',
        'waiting_mapping': 'منتظر ارسال فایل نقشه',
        'mapping_received': 'فایل نقشه دریافت شده، در حال پردازش',
        'waiting_files': 'منتظر دریافت فایل‌های پردازش شده',
        'completed': 'کار تمام شده، آماده دریافت فایل جدید'
    }

    def __init__(self, db: Session, editor_id: int):
        self.db = db
        self.editor_id = editor_id

    def get_current_state(self) -> str:
        """دریافت وضعیت فعلی ادیتور"""
        return editor_crud.get_editor_status(self.db, self.editor_id)

    def get_state_description(self, state: str = None) -> str:
        """دریافت توضیحات وضعیت"""
        if state is None:
            state = self.get_current_state()
        return self.STATES.get(state, 'وضعیت نامشخص')

    def can_receive_new_files(self) -> bool:
        """آیا ادیتور می‌تواند فایل جدید دریافت کند؟"""
        state = self.get_current_state()
        return state in ['idle', 'completed']

    def can_receive_mapping(self) -> bool:
        """آیا ادیتور می‌تواند فایل نقشه دریافت کند؟"""
        state = self.get_current_state()
        return state == 'waiting_mapping'

    def can_receive_processed_files(self) -> bool:
        """آیا ادیتور می‌تواند فایل‌های پردازش شده ارسال کند؟"""
        state = self.get_current_state()
        return state == 'waiting_files'

    def get_detailed_status(self) -> Dict:
        """دریافت وضعیت کامل ادیتور"""
        state = self.get_current_state()
        stats = editor_crud.get_editor_progress_stats(self.db, self.editor_id)

        return {
            'state': state,
            'state_description': self.get_state_description(state),
            'can_receive_new_files': self.can_receive_new_files(),
            'can_receive_mapping': self.can_receive_mapping(),
            'can_receive_processed_files': self.can_receive_processed_files(),
            'stats': stats
        }

    def process_file_reception(self, filename: str, file_id: str, file_content: str = None) -> tuple[bool, str]:
        """پردازش دریافت فایل از ادیتور"""
        state = self.get_current_state()

        # بررسی فایل نقشه
        if filename.lower().endswith('.txt') and file_content:
            if not self.can_receive_mapping():
                if state == 'idle':
                    return False, "شما هیچ فایلی برای ادیت دریافت نکرده‌اید. ابتدا فایل جدید اختصاص دهید."
                elif state == 'waiting_files':
                    return False, "شما قبلاً فایل نقشه ارسال کرده‌اید. اکنون باید فایل‌های پردازش شده را ارسال کنید."
                elif state == 'completed':
                    return False, "کار شما تمام شده است. می‌توانید فایل جدید اختصاص دهید."
                else:
                    return False, "در وضعیت فعلی امکان دریافت فایل نقشه وجود ندارد."

            # اعتبارسنجی فایل نقشه
            from utils.mapping_parser import validate_mapping_format
            is_valid, message = validate_mapping_format(file_content)
            if not is_valid:
                return False, f"فایل نقشه نامعتبر است: {message}"

            # ذخیره فایل نقشه
            success = editor_crud.save_mapping_file(self.db, self.editor_id, file_content)
            if success:
                return True, "فایل نقشه دریافت و پردازش شد. اکنون می‌توانید فایل‌های پردازش شده را ارسال کنید."
            else:
                return False, "خطا در پردازش فایل نقشه."

        # بررسی فایل‌های پردازش شده (STL, JPG, ZIP)
        else:
            if not self.can_receive_processed_files():
                if state == 'idle':
                    return False, "شما هیچ فایلی برای ادیت دریافت نکرده‌اید."
                elif state == 'waiting_mapping':
                    return False, "ابتدا باید فایل نقشه (.txt) را ارسال کنید."
                elif state == 'completed':
                    return False, "کار شما تمام شده است."
                else:
                    return False, "در وضعیت فعلی امکان دریافت این فایل وجود ندارد."

            # تشخیص نوع فایل
            from utils.mapping_parser import get_file_type_from_extension
            file_type = get_file_type_from_extension(filename)

            if file_type == 'unknown':
                return False, "نوع فایل پشتیبانی نمی‌شود. فقط فایل‌های STL، JPG و ZIP قابل قبول هستند."

            # بررسی آیا فایل مورد انتظار است
            if not editor_crud.check_filename_expected(self.db, self.editor_id, filename):
                return False, "این فایل در لیست انتظار نیست. لطفاً فایل‌های باقی‌مانده را بررسی کنید."

            # ثبت دریافت فایل
            success, message = editor_crud.receive_editor_file(self.db, self.editor_id, filename, file_id, file_type)

            if success:
                # بررسی آیا همه فایل‌ها دریافت شده‌اند
                pending_files = editor_crud.get_pending_files_for_editor(self.db, self.editor_id)
                if not pending_files:
                    editor_crud.complete_editor_session(self.db, self.editor_id)
                    return True, f"{message}\n\nتبریک! شما همه فایل‌های مورد نیاز را ارسال کردید. اکنون می‌توانید از طریق دکمه فایل‌های در انتظار ادیت، فایل‌های جدید دریافت کنید."
                else:
                    return True, f"{message}\nتعداد فایل‌های باقی‌مانده: {len(pending_files)}"
            else:
                return False, message

    def get_pending_files_list(self) -> str:
        """دریافت لیست فایل‌های باقی‌مانده به صورت متن - بهبود یافته"""
        state = self.get_current_state()

        # حالت 1: هیچ فایلی نگرفته
        if state == 'idle':
            return "شما هیچ فایلی برای ادیت دریافت نکرده‌اید.\n\nابتدا از طریق دکمه 'فایل‌های در انتظار ادیت' فایل جدید اختصاص دهید."

        # حالت 2: فایل گرفته اما مپینگ نداده
        elif state == 'waiting_mapping':
            session = editor_crud.get_editor_current_session(self.db, self.editor_id)
            if session and session.original_files:
                file_list = []
                for i, original_file in enumerate(session.original_files, 1):
                    file_list.append(f"{i}. {original_file.original_filename}")

                return f"فایل‌های دریافتی برای ادیت ({len(session.original_files)} مورد):\n\n" + "\n".join(
                    file_list) + "\n\n⚠️ ابتدا باید فایل نقشه (.txt) را ارسال کنید."
            else:
                return "خطا در دریافت اطلاعات فایل‌های دریافتی."

        # حالت 3: مپینگ داده، منتظر فایل‌های نهایی
        elif state == 'waiting_files':
            pending_files = editor_crud.get_pending_files_for_editor(self.db, self.editor_id)

            if not pending_files:
                return "همه فایل‌ها دریافت شده‌اند."

            # گروه‌بندی بر اساس نوع فایل
            stl_files = []
            zip_files = []
            jpg_files = []

            for pf in pending_files:
                base_name = pf.processed_filename.rsplit('.', 1)[0]

                if pf.stl_required and not pf.stl_received:
                    stl_files.append(f"{base_name}.stl")
                if pf.zip_required and not pf.zip_received:
                    zip_files.append(f"{base_name}.zip")
                if pf.jpg_required and not pf.jpg_received:
                    jpg_files.append(f"{base_name}.jpg")

            result = f"فایل‌های باقی‌مانده ({len(stl_files + zip_files + jpg_files)} مورد):\n\n"

            if stl_files:
                result += "📄 فایل‌های STL:\n"
                for i, file in enumerate(stl_files, 1):
                    result += f"  {i}. {file}\n"
                result += "\n"

            if zip_files:
                result += "📦 فایل‌های ZIP:\n"
                for i, file in enumerate(zip_files, 1):
                    result += f"  {i}. {file}\n"
                result += "\n"

            if jpg_files:
                result += "📸 فایل‌های JPG:\n"
                for i, file in enumerate(jpg_files, 1):
                    result += f"  {i}. {file}\n"

            return result.strip()

        # حالت 4: کار تمام شده
        elif state == 'completed':
            return "کار شما تکمیل شده است.\n\nمی‌توانید از طریق دکمه 'فایل‌های در انتظار ادیت' فایل جدید اختصاص دهید."

        else:
            return "وضعیت نامشخص."

    def assign_new_files(self, file_orders) -> tuple[bool, str]:
        """اختصاص فایل‌های جدید به ادیتور"""
        if not self.can_receive_new_files():
            state = self.get_current_state()
            if state == 'waiting_mapping':
                return False, "ابتدا باید فایل نقشه را ارسال کنید."
            elif state == 'waiting_files':
                pending_count = len(editor_crud.get_pending_files_for_editor(self.db, self.editor_id))
                return False, f"ابتدا باید فایل‌های باقی‌مانده را ارسال کنید. ({pending_count} فایل باقی‌مانده)"
            else:
                return False, "در حال حاضر امکان دریافت فایل جدید وجود ندارد."

        try:
            session = editor_crud.create_editor_session(self.db, self.editor_id, file_orders)
            return True, f"{len(file_orders)} فایل جدید به شما اختصاص یافت."
        except Exception as e:
            logger.error(f"خطا در اختصاص فایل‌های جدید: {e}")
            return False, "خطا در اختصاص فایل‌های جدید."