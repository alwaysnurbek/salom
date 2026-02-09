import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot_handlers.common import is_admin, ASK_TITLE, ASK_QUESTIONS, ASK_DURATION, ASK_CONFIRM, ASK_ANSWER_KEY, ASK_BROADCAST_MSG
import db.queries as db
from services.grader import normalize_answers
from services.exporter import generate_leaderboard_html
from datetime import datetime, timedelta
from io import BytesIO
import config

logger = logging.getLogger(__name__)

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Kirish taqiqlangan.")
        return

    text = f"👨‍💼 <b>Admin Panel</b>\n\nXush kelibsiz, {user.first_name}!"
    reply_markup = InlineKeyboardMarkup(ADMIN_KEYBOARD)

    if update.callback_query:
        # avoid "message is not modified" error
        try:
            await update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='HTML')
        except Exception:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')

async def admin_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "👨‍💼 <b>Admin Panel</b>",
        reply_markup=InlineKeyboardMarkup(ADMIN_KEYBOARD),
        parse_mode='HTML'
    )

async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    count = db.get_user_count()
    
    keyboard = [[InlineKeyboardButton("⬅️ Orqaga", callback_data="admin_home")]]
    await query.edit_message_text(
        f"📈 <b>Statistika</b>\n\n"
        f"👤 Jami foydalanuvchilar: <b>{count}</b> ta",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='HTML'
    )

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "<b>Admin Yordam</b>\n\n"
        "<b>Test Yaratish:</b> Yangi test ochish uchun sehrgar.\n"
        "<b>Kalit Kiritish:</b> Test yaratilgach, javoblarni kiritish.\n"
        "<b>Boshlash:</b> Testni faollashtirish.\n"
        "<b>Natijalar:</b> Tugagan yoki faol testlar natijalarini yuklab olish.\n"
        "<b>Xabar Yuborish:</b> Barcha foydalanuvchilarga xabar yo'llash.\n\n"
        "<i>Vaqt tugaganda natijalar avtomatik yuboriladi.</i>"
    )
    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_home")]]
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_home_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_start(update, context)

# --- Create Test Wizard ---
async def start_create_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("1-qadam: Test nomini kiriting (yoki /skip):")
    return ASK_TITLE

async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text
    if title == '/skip':
        title = "Nomsiz Test"
    context.user_data['test_title'] = title
    await update.message.reply_text("2-qadam: Savollar sonini kiriting (1-300):")
    return ASK_QUESTIONS

async def receive_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        n = int(text)
        if not (1 <= n <= 300):
            raise ValueError
        context.user_data['num_questions'] = n
        await update.message.reply_text("3-qadam: Davomiylik (soat) (1-168):")
        return ASK_DURATION
    except ValueError:
        await update.message.reply_text("Noto'g'ri raqam. 1-300 oralig'ida kiriting.")
        return ASK_QUESTIONS

async def receive_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        h = int(text)
        if not (1 <= h <= 168):
            raise ValueError
        context.user_data['duration_hours'] = h
        
        # Summary
        summary = (
            f"<b>Testni Tasdiqlash</b>\n"
            f"Nom: {context.user_data['test_title']}\n"
            f"Savollar: {context.user_data['num_questions']}\n"
            f"Vaqt: {h} soat"
        )
        keyboard = [
            [InlineKeyboardButton("✅ Yaratish (Qoralama)", callback_data="create_draft")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="create_cancel")]
        ]
        await update.message.reply_text(summary, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
        return ASK_CONFIRM
    except ValueError:
        await update.message.reply_text("Noto'g'ri vaqt. 1-168 soat kiriting.")
        return ASK_DURATION

async def confirm_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    
    if action == "create_cancel":
        await query.edit_message_text("❌ Test yaratish bekor qilindi.")
        return ConversationHandler.END
        
    title = context.user_data['test_title']
    n = context.user_data['num_questions']
    h = context.user_data['duration_hours']
    
    test_id = db.create_test(title, n, h)
    
    msg = f"Test yaratildi! ID = <b>{test_id}</b>"
    
    keyboard = [
        [InlineKeyboardButton("✍️ Kalitni Kiritish", callback_data=f"set_key_{test_id}")],
        [InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_test_{test_id}")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_home")]
    ]
    
    await query.edit_message_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    return ConversationHandler.END


# --- Answer Key Flow ---
async def set_key_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    test_id = int(query.data.split("_")[-1])
    test = db.get_test(test_id)
    if not test:
        await query.edit_message_text("Test topilmadi.")
        return ConversationHandler.END
        
    context.user_data['key_test_id'] = test_id
    context.user_data['key_num_questions'] = test['num_questions']
    
    await query.message.reply_text(
        f"Test <b>{test_id}</b> uchun javoblarni yuboring ({test['num_questions']} ta).\n"
        "Format: 'ABCD...' yoki '1A 2B...'", 
        parse_mode='HTML'
    )
    return ASK_ANSWER_KEY

async def receive_answer_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_key = update.message.text
    normalized = normalize_answers(raw_key)
    target_n = context.user_data['key_num_questions']
    
    if len(normalized) != target_n:
        await update.message.reply_text(
            f"❌ Uzunlik noto'g'ri. {len(normalized)} ta harf topildi, {target_n} ta kerak.\n"
            "Qaytadan yuboring yoki /cancel."
        )
        return ASK_ANSWER_KEY
        
    test_id = context.user_data['key_test_id']
    db.update_test_answer_key(test_id, normalized)
    
    keyboard = [
        [InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_test_{test_id}")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_home")]
    ]
    await update.message.reply_text(
        f"✅ Test {test_id} kalitlari saqlandi.\nKalit: {normalized}", 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ConversationHandler.END


# --- Manage Tests ---
async def manage_tests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    tests = db.get_all_tests(limit=10)
    if not tests:
        await query.edit_message_text("Testlar topilmadi.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_home")]]))
        return

    keyboard = []
    for t in tests:
        status_icon = "🟢" if t['status'] == 'active' else "🔴" if t['status'] == 'ended' else "📝"
        btn_text = f"{status_icon} #{t['id']} {t['title']} ({t['num_questions']}Q)"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"view_test_{t['id']}")])
        
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_home")])
    await query.edit_message_text("Testni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def view_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    target_test_id = int(query.data.split("_")[-1])
    test = db.get_test(target_test_id)
    
    if not test:
        await query.answer("Test topilmadi", show_alert=True)
        return

    info = (
        f"<b>Test #{test['id']}</b>\n"
        f"Nom: {test['title']}\n"
        f"Savollar: {test['num_questions']}\n"
        f"Status: {test['status']}\n"
        f"Kalit: {'✅' if test['answer_key'] else '❌'}\n"
    )
    
    buttons = []
    if test['status'] == 'draft':
        buttons.append([InlineKeyboardButton("✍️ Kalit kiritish", callback_data=f"set_key_{test['id']}")])
        if test['answer_key']:
            buttons.append([InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_test_{test['id']}")])
            
    if test['status'] == 'active':
        buttons.append([InlineKeyboardButton("⏹ Yakunlash", callback_data=f"end_test_{test['id']}")])
        
    buttons.append([InlineKeyboardButton("📊 Natijalar (Fayl)", callback_data=f"get_leaderboard_{test['id']}")])
    buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_manage_tests")])
    
    await query.edit_message_text(info, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(buttons))


async def start_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    test_id = int(query.data.split("_")[-1])
    test = db.get_test(test_id)
    
    if not test['answer_key']:
        await query.answer("Kalit kiritilmagan!", show_alert=True)
        return
        
    now = datetime.now()
    end_at = now + timedelta(hours=test['duration_hours'])
    
    db.start_test_db(test_id, now, end_at)
    await query.answer("Test Boshlandi!")
    await view_test(update, context)

async def end_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    test_id = int(query.data.split("_")[-1])
    
    db.end_test_db(test_id)
    await query.answer("Test Yakunlandi.")
    # Show view again
    await view_test(update, context)

# --- Leaderboard Logic ---
async def admin_leaderboard_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows list of tests to generate leaderboard for."""
    query = update.callback_query
    await query.answer()
    
    tests = db.get_all_tests(limit=20)
    if not tests:
        await query.edit_message_text("Testlar yo'q.")
        return

    keyboard = []
    for t in tests:
        btn_text = f"#{t['id']} {t['title']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"get_leaderboard_{t['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="admin_home")])
    await query.edit_message_text("Natijalarni olish uchun testni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

async def send_leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    test_id = int(query.data.split("_")[-1])
    
    submissions = db.get_test_submissions(test_id)
    test = db.get_test(test_id)
    
    if not submissions:
        await query.answer("Javoblar yo'q.", show_alert=True)
        return
        
    await query.answer("Fayl tayyorlanmoqda...")
    
    html_content = generate_leaderboard_html(test['title'], submissions)
    file_obj = BytesIO(html_content.encode('utf-8'))
    file_obj.name = f"leaderboard_test_{test_id}.html"
    
    caption = f"📊 <b>{test['title']}</b> - Natijalar\nJami ishtirokchilar: {len(submissions)}"
    
    await context.bot.send_document(
        chat_id=update.effective_chat.id,
        document=file_obj,
        caption=caption,
        parse_mode='HTML'
    )


# --- Broadcast Feature ---
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting (matn yoki forward):")
    return ASK_BROADCAST_MSG

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    users = db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    status_msg = await update.message.reply_text(f"Yuborilmoqda... Jami: {len(users)}")
    
    for row in users:
        user_id = row['tg_user_id']
        try:
            await message.copy(chat_id=user_id)
            success_count += 1
        except Exception:
            fail_count += 1
            
    await status_msg.edit_text(
        f"✅ Xabar yuborildi!\n\n"
        f"Muvaffaqiyatli: {success_count}\n"
        f"Xatolik: {fail_count}"
    )
    
    return ConversationHandler.END
