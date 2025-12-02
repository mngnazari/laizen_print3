from telegram import Update
from telegram.ext import ContextTypes
import database.crud
import database.connection
from database.models import User, FileOrder
from keyboards.customer import get_customer_kb
from datetime import datetime, timedelta


async def show_group_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار گروهی ساده"""
    user_id = update.effective_user.id

    with database.connection.SessionLocal() as db:
        user = database.crud.get_user(db, user_id)

        if not user:
            await update.message.reply_text("کاربر یافت نشد")
            return

        # دریافت زیرمجموعه‌ها
        referrals = db.query(User).filter(User.referrer_id == user_id).all()

        # اعضای گروه
        group_members = [user] + referrals

        # اگر کاربر خودش دعوت شده
        if user.referrer_id:
            referrer = db.query(User).filter(User.id == user.referrer_id).first()
            if referrer and referrer not in group_members:
                group_members.append(referrer)

                # سایر زیرمجموعه‌های همسطح
                siblings = db.query(User).filter(
                    User.referrer_id == user.referrer_id,
                    User.id != user_id
                ).all()
                group_members.extend(siblings)

        # حذف تکراری
        unique_members = list({m.id: m for m in group_members}.values())

        # محاسبه فایل‌های امروز
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        tomorrow_start = today_start + timedelta(days=1)

        total_today_files = 0
        user_today_files = 0

        for member in unique_members:
            member_files = db.query(FileOrder).filter(
                FileOrder.user_id == member.id,
                FileOrder.created_at >= today_start,
                FileOrder.created_at < tomorrow_start
            ).count()

            total_today_files += member_files
            if member.id == user_id:
                user_today_files = member_files

        # ایجاد پیام
        message = f"📊 **آمار گروه {user.full_name}**\n\n"
        message += f"📅 **تاریخ:** {today.strftime('%Y/%m/%d')}\n\n"
        message += f"👥 **اعضای گروه:** {len(unique_members)} نفر\n"
        message += f"📂 **کل فایل‌های گروه امروز:** {total_today_files}\n"
        message += f"🎯 **سهم شما:** {user_today_files} فایل\n\n"

        message += "👥 **اعضای گروه:**\n"
        for i, member in enumerate(unique_members[:5], 1):
            message += f"   {i}. {member.full_name}\n"

        if len(unique_members) > 5:
            message += f"   ... و {len(unique_members) - 5} نفر دیگر\n"

        if total_today_files >= 10:
            message += "\n🎉 **تبریک!** گروه شما امروز به حد نصاب تخفیف رسیده است!"
        else:
            remaining = 10 - total_today_files
            message += f"\n💡 **نکته:** برای کسب تخفیف، گروه شما {remaining} فایل دیگر نیاز دارد."

        await update.message.reply_text(
            message,
            parse_mode="Markdown",
            reply_markup=get_customer_kb(user_id)
        )