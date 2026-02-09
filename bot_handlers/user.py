from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import db.queries as db
from bot_handlers.common import REGISTER_NAME, REGISTER_REGION, check_is_subscribed
from services.grader import normalize_answers, grade_submission
from datetime import datetime
import config
import logging

logger = logging.getLogger(__name__)

# Static Main Menu Keyboard
MAIN_MENU = [
    ["📢 Kanalimiz (Obuna bo'ling)"],
    ["📞 Admin bilan aloqa"]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Check Subscription
    is_sub = await check_is_subscribed(context.bot, user.id)
    if not is_sub:
        keyboard = [
            [InlineKeyboardButton("Kanalga a'zo bo'lish 📢", url=f"https://t.me/{config.REQUIRED_CHANNEL_USERNAME}")],
            [InlineKeyboardButton("A'zo bo'ldim ✅", callback_data="check_subscription")]
        ]
        await update.message.reply_text(
            f"Assalomu alaykum, {user.first_name}!\n\n"
            "Botdan foydalanish uchun <b>BluePrep Academy</b> kanaliga a'zo bo'lishingiz shart.",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    db_user = db.get_user_by_tg_id(user.id)
    
    if db_user:
        await update.message.reply_text(
            f"Xush kelibsiz, {db_user['full_name']}! 👋\n\n"
            "Test ishlashga tayyormisiz? Javoblarni yuborish uchun quyidagi formatdan foydalaning:\n\n"
            "<code>TestID*Javoblar</code> (masalan: <code>101*abcde...</code>)",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
        )
        return ConversationHandler.END
        
    await update.message.reply_text(
        "<b>BluePrep botiga xush kelibsiz!</b> 🎓\n\n"
        "Botdan to'liq foydalanish uchun ro'yxatdan o'tishingiz kerak.\n"
        "Iltimos, <b>to'liq ismingizni</b> kiriting (Familiya Ism):",
        parse_mode='HTML'
    )
    return REGISTER_NAME

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    is_sub = await check_is_subscribed(context.bot, user.id)
    if is_sub:
        await query.message.delete()
        db_user = db.get_user_by_tg_id(user.id)
        if db_user:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"Xush kelibsiz, {db_user['full_name']}! 👋\n\nTestID*Javoblar formatida yuboring.",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
            )
        else:
            await context.bot.send_message(
                chat_id=user.id,
                text=(
                    "<b>Rahmat!</b> ✅\n\n"
                    "Endi ro'yxatdan o'tamiz. Iltimos, <b>to'liq ismingizni</b> kiriting:"
                ),
                parse_mode='HTML'
            )
            return REGISTER_NAME
    else:
        await query.message.reply_text("❌ Hali kanalga a'zo bo'lmadingiz. Iltimos, qaytadan urinib ko'ring.", quote=False)
        return ConversationHandler.END


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['full_name'] = name
    
    regions = [
        ["Toshkent shahri", "Toshkent vil."],
        ["Andijon", "Farg'ona", "Namangan"],
        ["Sirdaryo", "Jizzax", "Samarqand"],
        ["Buxoro", "Navoiy", "Qashqadaryo"],
        ["Surxondaryo", "Xorazm", "Qoraqalpog'iston"],
        ["O'tkazib yuborish"]
    ]
    await update.message.reply_text(
        "Yashash hududingizni tanlang 👇\n(yoki 'O'tkazib yuborish'ni bosing)",
        reply_markup=ReplyKeyboardMarkup(regions, one_time_keyboard=True, resize_keyboard=True)
    )
    return REGISTER_REGION

async def register_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    region = update.message.text
    if region == "O'tkazib yuborish":
        region = None
        
    user = update.effective_user
    db.upsert_user(user.id, user.username, context.user_data['full_name'], region)
    
    await update.message.reply_text(
        "<b>Tabriklaymiz! Ro'yxatdan o'tish muvaffaqiyatli yakunlandi.</b> 🎉\n\n"
        "Endi siz bot orqali test javoblarini yuborishingiz mumkin.\n\n"
        "<b>Yo'riqnoma:</b>\n"
        "Test javoblarini yuborish uchun ID va kalitlarni * belgisi bilan ajratib yozing:\n"
        "👉 <code>TestID*Javoblar</code>\n\n"
        "<i>Misol:</i> <code>105*abcdac...</code>",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True)
    )
    return ConversationHandler.END

async def handle_static_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user
    
    if "Kanalimiz" in text:
        # Send channel link with inline button
        keyboard = [[InlineKeyboardButton("Kanalga o'tish ↗️", url=f"https://t.me/{config.REQUIRED_CHANNEL_USERNAME}")]]
        await update.message.reply_text(
            f"<b>BluePrep Academy</b> rasmiy kanali!\n\n"
            "Eng so'nggi yangiliklar, testlar va natijalar shu kanalda e'lon qilinadi 👇",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='HTML'
        )
    elif "Admin" in text:
        # Send admin contact
        keyboard = [[InlineKeyboardButton("Admin bilan bog'lanish 👨‍💻", url="https://t.me/blueprep_admin")]]
        await update.message.reply_text(
            "Savollar, takliflar yoki muammolar bo'lsa, adminga murojaat qiling:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    parts = text.split('*', 1)
    if len(parts) != 2:
        return
        
    test_id_str, raw_answers = parts
    
    # Check user/test/time logic same as before...
    user = update.effective_user
    db_user = db.get_user_by_tg_id(user.id)
    if not db_user:
        await update.message.reply_text("Iltimos, avval /start buyrug'ini bosing.")
        return

    test_id = int(test_id_str)
    test = db.get_test(test_id)
    
    if not test:
        await update.message.reply_text(f"❌ Test #{test_id} topilmadi.")
        return
        
    if test['status'] != 'active':
        await update.message.reply_text(f"Test #{test_id} faol emas (Status: {test['status']}).")
        return
        
    if not test['answer_key']:
        await update.message.reply_text("Xatolik: Test kaliti yo'q.")
        return

    now = datetime.now()
    if test['end_at'] and isinstance(test['end_at'], str):
        end_at_dt = datetime.fromisoformat(test['end_at'])
        if now > end_at_dt:
             await update.message.reply_text("⏰ Test vaqti tugagan.")
             return
    elif test['end_at'] and now > test['end_at']: 
         await update.message.reply_text("⏰ Test vaqti tugagan.")
         return

    normalized = normalize_answers(raw_answers)
    
    if len(normalized) != test['num_questions']:
        await update.message.reply_text(
            f"❌ Javoblar soni noto'g'ri.\n"
            f"Kutilgan: {test['num_questions']} ta\n"
            f"Sizniki: {len(normalized)} ta"
        )
        return

    existing = db.get_submission(test_id, db_user['id'])
    if existing:
        await update.message.reply_text(f"⚠️ Siz Test #{test_id} ga javob yuborgansiz.")
        return

    correct, wrong, percent = grade_submission(normalized, test['answer_key'])
    started_at = now
    time_taken = 0
    
    success = db.create_submission(
        test_id, db_user['id'], raw_answers, normalized, 
        correct, wrong, percent, started_at, time_taken
    )
    
    if success:
        await update.message.reply_text(
            f"✅ <b>Test #{test_id} qabul qilindi!</b>\n\n"
            f"🟢 To'g'ri: {correct} ta\n"
            f"🔴 Noto'g'ri: {wrong} ta\n"
            f"📊 Natija: {percent}%\n"
            f"⏱ Vaqt: --:--",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("Xatolik yuz berdi (Ma'lumotlar bazasi).")

async def handle_invalid_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "⚠️ <b>Noto'g'ri format!</b>\n\n"
        "Test javoblarini yuborish uchun quyidagi formatdan foydalaning:\n"
        "<code>TestID*Javoblar</code>\n\n"
        "Misol: <code>101*abcde...</code>\n"
        "Yoki pastdagi menyudan foydalaning 👇"
    )
    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
