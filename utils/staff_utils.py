# utils/staff_utils.py
"""توابع کمکی برای چک کردن نقش کارکنان - جایگزین لیست‌های ثابت در config"""

import database.connection
import database.crud as crud
from config import ADMIN_ID
from functools import lru_cache
from typing import List
import time

# Cache timeout: 60 seconds
_cache_timeout = 60
_cache_data = {}


def _get_cached_or_fetch(role: str) -> List[int]:
    """دریافت لیست با کش"""
    cache_key = f"{role}_ids"
    now = time.time()

    if cache_key in _cache_data:
        data, timestamp = _cache_data[cache_key]
        if now - timestamp < _cache_timeout:
            return data

    with database.connection.SessionLocal() as db:
        if role == "editor":
            ids = crud.get_editors_ids(db)
        elif role == "operator":
            ids = crud.get_operators_ids(db)
        elif role == "visitor":
            ids = crud.get_visitors_ids(db)
        else:
            ids = []

    _cache_data[cache_key] = (ids, now)
    return ids


def clear_staff_cache():
    """پاک کردن کش - بعد از تغییرات"""
    global _cache_data
    _cache_data = {}


def get_editors_ids() -> List[int]:
    """دریافت لیست آیدی ادیتورها"""
    return _get_cached_or_fetch("editor")


def get_operators_ids() -> List[int]:
    """دریافت لیست آیدی اپراتورها"""
    return _get_cached_or_fetch("operator")


def get_visitors_ids() -> List[int]:
    """دریافت لیست آیدی ویزیتورها"""
    return _get_cached_or_fetch("visitor")


def is_editor(user_id: int) -> bool:
    """آیا کاربر ادیتور است؟"""
    return user_id in get_editors_ids()


def is_operator(user_id: int) -> bool:
    """آیا کاربر اپراتور است؟"""
    return user_id in get_operators_ids()


def is_visitor(user_id: int) -> bool:
    """آیا کاربر ویزیتور است؟"""
    return user_id in get_visitors_ids()


def is_admin(user_id: int) -> bool:
    """آیا کاربر ادمین است؟"""
    return user_id == ADMIN_ID


def get_user_role(user_id: int) -> str:
    """دریافت نقش کاربر"""
    if is_admin(user_id):
        return "admin"
    if is_editor(user_id):
        return "editor"
    if is_operator(user_id):
        return "operator"
    if is_visitor(user_id):
        return "visitor"
    return "customer"
