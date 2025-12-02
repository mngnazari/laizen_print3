from PIL import Image, ImageDraw, ImageFont

def generate_invoice(data, template_path, output_path):
    # باز کردن تمپلت
    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    # بارگذاری فونت ایران‌سنس (باید ttf فونت رو داشته باشی)
    font_path = "IRANSans.ttf"   # مسیر فایل فونت
    font_big = ImageFont.truetype(font_path, 32)   # برای عنوان‌ها
    font_normal = ImageFont.truetype(font_path, 24)

    # 📝 چاپ اطلاعات بالای فاکتور
    draw.text((350, 50), f"شماره: {data['invoice_number']}", font=font_normal, fill="black")
    draw.text((350, 90), f"تاریخ: {data['date']}", font=font_normal, fill="black")

    # 📝 اطلاعات مشتری
    draw.text((350, 150), f"نام مشتری: {data['customer_name']}", font=font_normal, fill="black")
    draw.text((350, 190), f"شماره تماس: {data['customer_phone']}", font=font_normal, fill="black")
    draw.text((350, 230), f"آدرس: {data['customer_address']}", font=font_normal, fill="black")

    # 📝 جدول کالاها
    start_y = 300
    for i, item in enumerate(data["items"]):
        y = start_y + i * 40
        draw.text((100, y), item["description"], font=font_normal, fill="black")   # شرح
        draw.text((300, y), f"{item['weight']} گرم", font=font_normal, fill="black")  # وزن
        draw.text((450, y), f"{item['unit_price']} تومان", font=font_normal, fill="black")  # قیمت واحد

        # محاسبه مبلغ هر ردیف (بعد از تخفیف)
        price_after_discount = item["weight"] * item["unit_price"] * (1 - item["discount"]/100)
        draw.text((650, y), f"{int(price_after_discount)}", font=font_normal, fill="black")

    # 📝 جمع کل پایین جدول
    draw.text((500, 600), f"جمع کل: {data['total']} تومان", font=font_big, fill="black")

    # ذخیره خروجی
    img.save(output_path, "JPEG")

# --- تست ---
invoice_data = {
    "invoice_number": "INV-2025-001",
    "date": "2025-10-03",
    "customer_name": "علی رضایی",
    "customer_phone": "0912xxxxxxx",
    "customer_address": "تهران، خیابان آزادی",
    "items": [
        {"description": "پرینت قطعه A", "weight": 120, "unit_price": 500, "discount": 0},
        {"description": "پرینت قطعه B", "weight": 300, "unit_price": 450, "discount": 10},
    ],
    "total": 180000
}

generate_invoice(invoice_data, "e926412d-58ff-48af-9d3c-eb1d349ba289.png", "invoice_output.jpg")
