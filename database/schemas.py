# database/schemas.py
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    id: int
    full_name: str
    phone_number: str
    referrer_id: Optional[int] = None
    referral_code: Optional[str] = None
    role: Optional[str] = None
    notification_status: Optional[str] = "all"  # پیش‌فرض: دریافت همه پیام‌ها



class InvoiceCreate(BaseModel):
    customer_id: int
    operator_id: int
    file_order_id: Optional[int] = None
    weight_grams: float
    price_per_gram: float
    photo_file_id: str

    @field_validator('weight_grams')
    @classmethod
    def validate_weight(cls, v):
        """Ensures weight is positive."""
        if v <= 0:
            raise ValueError('وزن باید مثبت باشد')
        return v

    @field_validator('price_per_gram')
    @classmethod
    def validate_price(cls, v):
        """Ensures price is positive."""
        if v <= 0:
            raise ValueError('قیمت باید مثبت باشد')
        return v

# در database/schemas.py:
class FileOrderCreate(BaseModel):
    user_id: int
    username: Optional[str] = None
    file_id: str
    file_name: str
    file_size: int
    print_count: int = 1
    description: Optional[str] = None
    message_id: int
    delivery_datetime: Optional[datetime] = None
    edit_deadline: Optional[datetime] = None  # فیلد جدید
    created_at: Optional[datetime] = None