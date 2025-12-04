# handlers/operator.py
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
import database.crud
import database.connection
from keyboards.operator import (
    get_operator_main_inline_keyboard,
    get_operator_invoice_submenu,
    get_operator_kb,
    create_customers_invoice_keyboard,
    create_customer_files_keyboard
)

# States برای conversation handler
(GET_WEIGHT, GET_PHOTO) = range(2)


async def handle_operator_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت منوی اپراتور - نسخه جدید با کیبورد شیشه‌ای"""

    print(f"🔍 DEBUG handle_operator_menu CALLED!")
    print(f"🔍 DEBUG user_id: {update.effective_user.id}")
    print(f"🔍 DEBUG message text: {update.message.text}")

    # کیبورد شیشه‌ای اصلی
    inline_keyboard = get_operator_main_inline_keyboard()

    # حذف کیبورد ثابت و استفاده از یک کیبورد ساده
    simple_keyboard = get_operator_kb()

    print(f"🔍 DEBUG Sending operator menu messages...")

    await update.message.reply_text(
        "🔧 **منوی اپراتور**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
        reply_markup=simple_keyboard,
        parse_mode="Markdown"
    )

    # ارسال کیبورد شیشه‌ای اصلی
    await update.message.reply_text(
        "📋 **منوی اصلی اپراتور:**",
        reply_markup=inline_keyboard,
        parse_mode="Markdown"
    )

    print(f"🔍 DEBUG Messages sent successfully!")


async def show_operator_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش منوی اصلی اپراتور - جدید"""
    query = update.callback_query
    await query.answer()

    inline_keyboard = get_operator_main_inline_keyboard()

    await query.edit_message_text(
        "🔧 **منوی اصلی اپراتور**\n\nلطفاً عملیات مورد نظر را انتخاب کنید:",
        reply_markup=inline_keyboard,
        parse_mode="Markdown"
    )


async def show_operator_invoice_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش زیرمنوی صدور فاکتور"""
    query = update.callback_query
    await query.answer()

    keyboard = get_operator_invoice_submenu()

    await query.edit_message_text(
        "📋 **منوی صدور فاکتور**\n\n"
        "💡 **گزینه‌های موجود:**\n"
        "📁 **فایل‌ها:** مدیریت فایل‌های پرینت و ارسال به اپراتور\n"
        "📊 **آمار:** مشاهده عملکرد شما\n"
        "👥 **مشتریان:** لیست مشتریان\n"
        "⚙️ **تنظیمات:** تنظیمات اپراتور\n\n"
        "لطفاً گزینه مورد نظر را انتخاب کنید:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def handle_operator_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر callback های اپراتور"""
    query = update.callback_query

    if query.data == "operator_main_menu":
        await show_operator_main_menu(update, context)
    elif query.data == "operator_invoice_menu":
        await show_operator_invoice_menu(update, context)
    elif query.data == "operator_my_stats":
        await show_operator_stats(update, context)
    elif query.data == "operator_view_customers":
        await show_customers_list(update, context)
    elif query.data == "operator_settings":
        await show_operator_settings(update, context)
    else:
        await query.answer("گزینه نامشخص")


async def show_customers_for_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش مشتریانی که سفارش pending دارند"""
    print(f"📋 DEBUG: show_customers_for_invoice called")

    with database.connection.SessionLocal() as db:
        customers = database.crud.get_customers_with_pending_orders(db)

        print(f"📋 DEBUG: Found {len(customers)} customers with pending orders")

        if not customers:
            await update.message.reply_text(
                "❌ در حال حاضر هیچ مشتری با سفارش pending وجود ندارد.",
                reply_markup=get_operator_kb()
            )
            return

        keyboard = create_customers_invoice_keyboard(customers)
        print(f"📋 DEBUG: Keyboard created for customers")

        await update.message.reply_text(
            f"📋 **صدور فاکتور**\n\n"
            f"لطفاً مشتری مورد نظر را انتخاب کنید:\n"
            f"({len(customers)} مشتری با سفارش pending)",
            parse_mode="Markdown",
            reply_markup=keyboard
        )


async def handle_customer_file_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر انتخاب مشتری و مدیریت فایل‌ها"""
    query = update.callback_query
    await query.answer()

    # Debug logs
    print(f"🔍 DEBUG: Callback data received: {query.data}")
    print(f"🔍 DEBUG: User ID: {query.from_user.id}")
    print(f"🔍 DEBUG: Context user_data: {context.user_data}")

    if query.data.startswith("select_customer_"):
        print(f"📋 DEBUG: Processing select_customer...")
        customer_id = int(query.data.split("_")[-1])
        print(f"📋 DEBUG: Customer ID extracted: {customer_id}")

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            orders = database.crud.get_customer_pending_orders(db, customer_id)

            print(f"📋 DEBUG: Customer found: {customer.full_name if customer else 'None'}")
            print(f"📋 DEBUG: Orders count: {len(orders) if orders else 0}")

            if not customer:
                print(f"❌ DEBUG: Customer not found!")
                await query.edit_message_text("❌ خطا: مشتری یافت نشد.")
                return ConversationHandler.END

            if not orders:
                print(f"❌ DEBUG: No pending orders found!")
                await query.edit_message_text("❌ خطا: سفارش pending یافت نشد.")
                return ConversationHandler.END

            # ذخیره اطلاعات فایل‌ها در context برای مدیریت وضعیت
            context.user_data['current_customer_id'] = customer_id
            context.user_data['file_statuses'] = {}  # {order_id: "success"/"failed"/None}

            for order in orders:
                context.user_data['file_statuses'][order.id] = None  # پیش‌فرض: تعیین تکلیف نشده
                print(f"📋 DEBUG: Order added - ID: {order.id}, File: {order.file_name}, Count: {order.print_count}")

            # نمایش اطلاعات مشتری و فایل‌ها
            total_files = len(orders)
            total_print_count = sum(order.print_count for order in orders)

            print(f"📋 DEBUG: Creating keyboard for {total_files} files...")
            keyboard = create_customer_files_keyboard(orders, customer_id)
            print(f"📋 DEBUG: Keyboard created successfully")

            message_text = (
                f"📋 **انتخاب فایل‌های {customer.customer_code}**\n\n"
                f"👤 **مشتری:** {customer.full_name}\n"
                f"📞 **تلفن:** {customer.phone_number}\n\n"
                f"📦 **تعداد فایل‌ها:** {total_files}\n"
                f"📊 **مجموع پرینت:** {total_print_count}\n\n"
                f"🔹 **راهنما:**\n"
                f"⚪ دایره خالی: تعیین تکلیف نشده\n"
                f"🟢 دایره سبز: پرینت موفق\n"
                f"🔴 دایره قرمز: پرینت ناموفق\n\n"
                f"🔍 لطفاً وضعیت هر فایل را مشخص کنید:"
            )

            print(f"📋 DEBUG: Sending message to user...")
            try:
                await query.edit_message_text(message_text, parse_mode="Markdown", reply_markup=keyboard)
                print(f"✅ DEBUG: Message sent successfully!")
            except Exception as e:
                print(f"❌ DEBUG: Error sending message: {e}")
                await query.message.reply_text(message_text, parse_mode="Markdown", reply_markup=keyboard)

            return ConversationHandler.END  # برای ماندن در همین حالت

    elif query.data.startswith("toggle_file_"):
        print(f"🔄 DEBUG: Processing toggle_file...")
        order_id = int(query.data.split("_")[-1])

        # تغییر وضعیت فایل: None → success → failed → success → ...
        current_status = context.user_data['file_statuses'].get(order_id)

        if current_status is None:
            new_status = "success"
        elif current_status == "success":
            new_status = "failed"
        else:  # failed
            new_status = "success"

        context.user_data['file_statuses'][order_id] = new_status
        print(f"🔄 DEBUG: File {order_id} status changed to {new_status}")

        # به‌روزرسانی کیبورد
        customer_id = context.user_data['current_customer_id']

        with database.connection.SessionLocal() as db:
            orders = database.crud.get_customer_pending_orders(db, customer_id)

            # اضافه کردن وضعیت به orders
            for order in orders:
                order.print_status = context.user_data['file_statuses'].get(order.id)

            keyboard = create_customer_files_keyboard(orders, customer_id)

            await query.edit_message_reply_markup(reply_markup=keyboard)

        return ConversationHandler.END  # برای ماندن در همین حالت

    elif query.data.startswith("issue_invoice_"):
        print(f"💰 DEBUG: Processing issue_invoice...")
        customer_id = int(query.data.split("_")[-1])

        # بررسی اینکه همه فایل‌ها تعیین تکلیف شده‌اند
        file_statuses = context.user_data.get('file_statuses', {})
        undecided_files = [order_id for order_id, status in file_statuses.items() if status is None]

        if undecided_files:
            print(f"⚠️ DEBUG: Undecided files: {undecided_files}")
            await query.answer(
                "❌ لطفاً ابتدا وضعیت تمام فایل‌ها را مشخص کنید!",
                show_alert=True
            )
            return ConversationHandler.END

        # بررسی اینکه حداقل یک فایل موفق باشد
        successful_files = [order_id for order_id, status in file_statuses.items() if status == "success"]

        if not successful_files:
            print(f"⚠️ DEBUG: No successful files")
            await query.answer(
                "❌ حداقل یک فایل باید وضعیت موفق داشته باشد!",
                show_alert=True
            )
            return ConversationHandler.END

        # ذخیره وضعیت‌ها و شروع فرآیند صدور فاکتور
        context.user_data['invoice_customer_id'] = customer_id
        context.user_data['successful_files'] = successful_files

        with database.connection.SessionLocal() as db:
            customer = database.crud.get_user(db, customer_id)
            successful_orders = db.query(database.models.FileOrder).filter(
                database.models.FileOrder.id.in_(successful_files)
            ).all()

            total_successful_prints = sum(order.print_count for order in successful_orders)

            await query.edit_message_text(
                f"✅ **آماده صدور فاکتور**\n\n"
                f"👤 **مشتری:** {customer.full_name}\n"
                f"🟢 **فایل‌های موفق:** {len(successful_files)}\n"
                f"📊 **مجموع پرینت موفق:** {total_successful_prints}\n\n"
                f"⚖️ **لطفاً وزن کل کار موفق را به گرم وارد کنید:**",
                parse_mode="Markdown"
            )

            return GET_WEIGHT

    elif query.data == "back_to_customers_list":
        print(f"🔙 DEBUG: Processing back_to_customers_list...")
        # بازگشت به لیست مشتریان
        with database.connection.SessionLocal() as db:
            customers = database.crud.get_customers_with_pending_orders(db)
            keyboard = create_customers_invoice_keyboard(customers)

            await query.edit_message_text(
                f"📋 **صدور فاکتور**\n\n"
                f"لطفاً مشتری مورد نظر را انتخاب کنید:\n"
                f"({len(customers)} مشتری با سفارش pending)",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        return ConversationHandler.END

    elif query.data == "back_to_operator_menu":
        print(f"🔙 DEBUG: Processing back_to_operator_menu...")
        await show_operator_main_menu(update, context)
        return ConversationHandler.END

    else:
        print(f"❓ DEBUG: Unknown callback data: {query.data}")


async def get_weight_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت وزن کار از اپراتور"""
    try:
        weight = float(update.message.text.replace(',', '.'))
        if weight <= 0:
            await update.message.reply_text("❌ وزن باید عددی مثبت باشد. لطفاً دوباره وارد کنید:")
            return GET_WEIGHT

        context.user_data['invoice_weight'] = weight

        # دریافت قیمت هر گرم از دیتابیس
        with database.connection.SessionLocal() as db:
            price_per_gram = database.crud.get_price_per_gram(db)
            total_amount = weight * price_per_gram

        await update.message.reply_text(
            f"✅ **وزن ثبت شد:** {weight} گرم\n"
            f"💰 **قیمت هر گرم:** {price_per_gram} دلار\n"
            f"💵 **مبلغ کل:** {total_amount} دلار\n\n"
            f"📸 **حالا لطفاً عکس مدل‌های پرینت شده را ارسال کنید:**",
            parse_mode="Markdown"
        )

        return GET_PHOTO

    except ValueError:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید:")
        return GET_WEIGHT


async def get_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دریافت عکس کار از اپراتور و ایجاد فاکتور"""
    if not update.message.photo:
        await update.message.reply_text("❌ لطفاً یک عکس ارسال کنید:")
        return GET_PHOTO

    try:
        # دریافت بهترین کیفیت عکس
        photo = update.message.photo[-1]
        photo_file_id = photo.file_id

        customer_id = context.user_data.get('invoice_customer_id')
        weight = context.user_data.get('invoice_weight')
        successful_files = context.user_data.get('successful_files', [])
        operator_id = update.effective_user.id

        with database.connection.SessionLocal() as db:
            # دریافت قیمت هر گرم
            price_per_gram = database.crud.get_price_per_gram(db)

            # ایجاد فاکتور
            invoice_data = {
                'customer_id': customer_id,
                'operator_id': operator_id,
                'weight_grams': weight,
                'price_per_gram': price_per_gram,
                'photo_file_id': photo_file_id
            }

            invoice = database.crud.create_invoice(db, invoice_data)
            customer = database.crud.get_user(db, customer_id)

            # به‌روزرسانی وضعیت فایل‌های موفق به invoiced
            db.query(database.models.FileOrder).filter(
                database.models.FileOrder.id.in_(successful_files)
            ).update({
                "status": "invoiced",
                "has_invoice": True
            })

            # به‌روزرسانی وضعیت فایل‌های ناموفق به failed
            file_statuses = context.user_data.get('file_statuses', {})
            failed_files = [order_id for order_id, status in file_statuses.items() if status == "failed"]

            if failed_files:
                db.query(database.models.FileOrder).filter(
                    database.models.FileOrder.id.in_(failed_files)
                ).update({"status": "failed"})

            db.commit()

            # ارسال تأیید به اپراتور
            successful_count = len(successful_files)
            failed_count = len(failed_files)

            await update.message.reply_text(
                f"✅ **فاکتور با موفقیت صادر شد!**\n\n"
                f"🆔 **شماره فاکتور:** {invoice.id}\n"
                f"👤 **مشتری:** {customer.customer_code} - {customer.full_name}\n"
                f"⚖️ **وزن:** {weight} گرم\n"
                f"💰 **قیمت واحد:** {price_per_gram} دلار\n"
                f"💵 **مبلغ کل:** {invoice.total_amount} دلار\n\n"
                f"📊 **خلاصه:**\n"
                f"🟢 فایل‌های موفق: {successful_count}\n"
                f"🔴 فایل‌های ناموفق: {failed_count}",
                parse_mode="Markdown",
                reply_markup=get_operator_kb()
            )

            # ارسال فاکتور به مشتری
            caption = (
                f"🧾 **فاکتور جدید**\n\n"
                f"🆔 **شماره:** {invoice.id}\n"
                f"⚖️ **وزن:** {weight} گرم\n"
                f"💰 **قیمت هر گرم:** {price_per_gram} دلار\n"
                f"💵 **مبلغ کل:** {invoice.total_amount} دلار\n"
                f"📅 **تاریخ:** {invoice.created_at.strftime('%Y/%m/%d - %H:%M')}\n\n"
                f"📊 **وضعیت پرینت:**\n"
                f"🟢 موفق: {successful_count} فایل\n"
                f"🔴 ناموفق: {failed_count} فایل"
            )

            await context.bot.send_photo(
                chat_id=customer_id,
                photo=photo_file_id,
                caption=caption,
                parse_mode="Markdown"
            )

        # پاک کردن داده‌های conversation
        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(
            f"❌ خطا در ایجاد فاکتور: {str(e)}\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_operator_kb()
        )
    context.user_data.clear()
    return ConversationHandler.END


async def show_operator_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار کارهای اپراتور"""
    query = update.callback_query
    if query:
        await query.answer()
        operator_id = query.from_user.id
    else:
        operator_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        # تعداد فاکتورهای صادر شده توسط این اپراتور
        operator_invoices = db.query(database.models.Invoice).filter(
            database.models.Invoice.operator_id == operator_id
        ).all()

        total_invoices = len(operator_invoices)
        total_weight = sum(inv.weight_grams for inv in operator_invoices)
        total_amount = sum(inv.total_amount for inv in operator_invoices)

        # آمار امروز
        from datetime import datetime, date
        today = date.today()
        today_invoices = [inv for inv in operator_invoices
                          if inv.created_at.date() == today]

        today_count = len(today_invoices)
        today_weight = sum(inv.weight_grams for inv in today_invoices)
        today_amount = sum(inv.total_amount for inv in today_invoices)

        stats_message = f"""📊 **آمار کارهای شما**

📅 **امروز:**
• تعداد فاکتور: {today_count}
• وزن کل: {today_weight} گرم
• مبلغ کل: {today_amount} دلار

📈 **کل:**
• تعداد فاکتور: {total_invoices}
• وزن کل: {total_weight} گرم
• مبلغ کل: {total_amount} دلار

📋 **میانگین:**
• وزن هر فاکتور: {total_weight / total_invoices if total_invoices > 0 else 0:.1f} گرم
• مبلغ هر فاکتور: {total_amount / total_invoices if total_invoices > 0 else 0:.1f} دلار"""

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="operator_invoice_menu")]
        ])

        if query:
            await query.edit_message_text(
                stats_message.strip(),
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                stats_message.strip(),
                parse_mode="Markdown",
                reply_markup=get_operator_kb()
            )


async def show_customers_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست مشتریان"""
    query = update.callback_query
    if query:
        await query.answer()

    with database.connection.SessionLocal() as db:
        customers = db.query(database.models.User).filter(
            database.models.User.role == "customer"
        ).order_by(database.models.User.customer_code).all()

        if not customers:
            message = "❌ هنوز هیچ مشتری ثبت‌نام نکرده است."
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="operator_invoice_menu")]
            ])
        else:
            message = "👥 **لیست مشتریان:**\n\n"
            for customer in customers[:20]:  # نمایش 20 مشتری اول
                # تعداد سفارشات مشتری
                orders_count = db.query(database.models.FileOrder).filter(
                    database.models.FileOrder.user_id == customer.id
                ).count()

                # تعداد فاکتورهای مشتری
                invoices_count = db.query(database.models.Invoice).filter(
                    database.models.Invoice.customer_id == customer.id
                ).count()

                message += f"🔸 **{customer.customer_code}** - {customer.full_name}\n"
                message += f"   📱 {customer.phone_number}\n"
                message += f"   📦 سفارشات: {orders_count} | 🧾 فاکتورها: {invoices_count}\n\n"

            if len(customers) > 20:
                message += f"... و {len(customers) - 20} مشتری دیگر"

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="operator_invoice_menu")]
            ])

        if query:
            await query.edit_message_text(
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode="Markdown",
                reply_markup=get_operator_kb()
            )


async def show_operator_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تنظیمات اپراتور"""
    query = update.callback_query
    if query:
        await query.answer()

    with database.connection.SessionLocal() as db:
        price_per_gram = database.crud.get_price_per_gram(db)

    settings_message = f"""⚙️ **تنظیمات**

💰 **قیمت فعلی هر گرم:** {price_per_gram} دلار

📝 **راهنما:**
• برای صدور فاکتور از منوی "📋 صدور فاکتور" استفاده کنید
• ابتدا وزن کار را به گرم وارد کنید
• سپس عکس کار را ارسال کنید
• فاکتور به صورت خودکار برای مشتری ارسال می‌شود"""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 بازگشت", callback_data="operator_invoice_menu")]
    ])

    if query:
        await query.edit_message_text(
            settings_message.strip(),
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            settings_message.strip(),
            parse_mode="Markdown",
            reply_markup=get_operator_kb()
        )


async def cancel_invoice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لغو فرآیند صدور فاکتور"""
    await update.message.reply_text(
        "❌ فرآیند صدور فاکتور لغو شد.",
        reply_markup=get_operator_kb()
    )
    context.user_data.clear()
    return ConversationHandler.END


# سازگاری با ورژن قبلی
async def handle_customer_selection_for_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر انتخاب مشتری برای صدور فاکتور - استفاده از تابع جدید"""
    return await handle_customer_file_selection(update, context)