# utils/delivery_grouping.py

from collections import defaultdict
from datetime import datetime
from typing import List, Dict
import database.models

# در utils/delivery_grouping.py اصلاح کنید:

import jdatetime


def group_files_by_delivery_time(files: List[database.models.FileOrder]) -> Dict[str, List[database.models.FileOrder]]:
    """گروه‌بندی فایل‌ها بر اساس زمان تحویل با تاریخ شمسی"""
    grouped = defaultdict(list)

    for file_order in files:
        if file_order.delivery_datetime:
            # تبدیل به تاریخ شمسی
            jd = jdatetime.datetime.fromgregorian(datetime=file_order.delivery_datetime)
            delivery_key = jd.strftime("%Y/%m/%d %H:%M")
            grouped[delivery_key].append(file_order)

    return dict(grouped)


def group_files_by_customer(files: List[database.models.FileOrder]) -> Dict[str, List[database.models.FileOrder]]:
    """گروه‌بندی فایل‌ها بر اساس کد مشتری"""
    grouped = defaultdict(list)

    for file_order in files:
        customer_code = file_order.user.customer_code
        grouped[customer_code].append(file_order)

    return dict(grouped)


def count_pending_files_by_delivery() -> Dict[str, int]:
    """شمارش فایل‌های pending بر اساس زمان تحویل"""
    import database.connection
    import database.crud

    with database.connection.SessionLocal() as db:
        pending_files = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending"
        ).options(database.crud.joinedload(database.models.FileOrder.user)).all()

        delivery_groups = group_files_by_delivery_time(pending_files)
        return {delivery_time: len(files) for delivery_time, files in delivery_groups.items()}


def count_total_pending_files() -> int:
    """شمارش کل فایل‌های pending"""
    import database.connection

    with database.connection.SessionLocal() as db:
        return db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending"
        ).count()


# در utils/delivery_grouping.py اصلاح کنید:

def count_ready_files_by_delivery() -> Dict[str, int]:
    """شمارش فایل‌های pending بر اساس زمان تحویل"""
    import database.connection
    import jdatetime

    with database.connection.SessionLocal() as db:
        ready_files = db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending"
            # حذف شرط sent_to_operator
        ).options(database.crud.joinedload(database.models.FileOrder.user)).all()

        grouped = defaultdict(int)

        for file_order in ready_files:
            if file_order.delivery_datetime:
                jd = jdatetime.datetime.fromgregorian(datetime=file_order.delivery_datetime)
                delivery_key = jd.strftime("%Y/%m/%d %H:%M")
                grouped[delivery_key] += 1

        return dict(grouped)

def count_total_ready_files() -> int:
    """شمارش کل فایل‌های pending"""
    import database.connection

    with database.connection.SessionLocal() as db:
        return db.query(database.models.FileOrder).filter(
            database.models.FileOrder.status == "pending"
            # حذف شرط sent_to_operator
        ).count()