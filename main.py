import logging
# MONKEYPATCH: APScheduler < 4.0 refuses datetime.timezone.utc, demanding pytz.
# PTB v20+ uses datetime.timezone.utc by default.
# We patch apscheduler.util.astimezone to convert standard UTC to pytz.utc.
# This MUST be done before importing telegram.ext or apscheduler elsewhere.
import apscheduler.util
import pytz
from datetime import timezone as std_timezone

orig_astimezone = apscheduler.util.astimezone

def patched_astimezone(obj):
    if obj is std_timezone.utc:
        return pytz.utc
    return orig_astimezone(obj)
    
apscheduler.util.astimezone = patched_astimezone

# Now import the rest
import config
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler, JobQueue
from bot_handlers.admin import (
    admin_start, admin_help, admin_home_callback,
    start_create_test, receive_title, receive_questions, receive_duration, confirm_creation,
    manage_tests, view_test, start_test_callback, end_test_callback,
    set_key_start, receive_answer_key,
    admin_leaderboard_menu, send_leaderboard_callback,
    start_broadcast, send_broadcast
)
from bot_handlers.user import start, register_name, register_region, handle_submission, handle_invalid_message
from bot_handlers.common import cancel, ASK_TITLE, ASK_QUESTIONS, ASK_DURATION, ASK_CONFIRM, ASK_ANSWER_KEY, REGISTER_NAME, REGISTER_REGION, ASK_BROADCAST_MSG
from scheduler.jobs import check_active_tests
from db.init_db import init_db

# Initialize DB on startup
init_db()

def main():
    if not config.BOT_TOKEN:
        print("Error: BOT_TOKEN not found in .env")
        return

    # Fix for APScheduler/PTB on Python 3.12+ where no loop exists yet
    import asyncio
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Use custom JobQueue to enforce our pytz timezone
    class FixedJobQueue(JobQueue):
        @property
        def scheduler_configuration(self):
            conf = super().scheduler_configuration
            conf['timezone'] = pytz.timezone(config.TIMEZONE)
            return conf

    job_queue = FixedJobQueue()
    application = ApplicationBuilder().token(config.BOT_TOKEN).job_queue(job_queue).build()
    
    # --- Admin Conversations ---
    
    # Create Test Wizard
    create_test_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_create_test, pattern="^admin_create_test$")],
        states={
            ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            ASK_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_questions)],
            ASK_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_duration)],
            ASK_CONFIRM: [CallbackQueryHandler(confirm_creation, pattern="^create_.*")]
        },
        fallbacks=[CommandHandler("cancel", cancel), CallbackQueryHandler(cancel, pattern="^create_cancel$")]
    )
    
    # Set Answer Key Wizard
    set_key_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_key_start, pattern="^set_key_")],
        states={
            ASK_ANSWER_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer_key)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # Broadcast Wizard
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^admin_broadcast_start$")],
        states={
            ASK_BROADCAST_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, send_broadcast)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # User Registration
    register_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_region)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    # --- Handlers ---
    
    # Admin Commands
    application.add_handler(CommandHandler("admin", admin_start))
    application.add_handler(CallbackQueryHandler(admin_home_callback, pattern="^admin_home$"))
    application.add_handler(CallbackQueryHandler(admin_help, pattern="^admin_help$"))
    application.add_handler(CallbackQueryHandler(manage_tests, pattern="^admin_manage_tests$"))
    application.add_handler(CallbackQueryHandler(view_test, pattern="^view_test_"))
    application.add_handler(CallbackQueryHandler(start_test_callback, pattern="^start_test_"))
    application.add_handler(CallbackQueryHandler(end_test_callback, pattern="^end_test_"))
    application.add_handler(CallbackQueryHandler(admin_leaderboard_menu, pattern="^admin_leaderboard_menu$"))
    application.add_handler(CallbackQueryHandler(send_leaderboard_callback, pattern="^get_leaderboard_"))
    
    # Conversations
    application.add_handler(create_test_conv)
    application.add_handler(set_key_conv)
    application.add_handler(broadcast_conv)
    application.add_handler(register_conv)
    
    # Submission Listener (Regex match)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.Regex(r'^\d+\*'), handle_submission))
    
    # Catch-all for invalid messages (must be last)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_message))

    # --- Scheduler ---
    job_queue = application.job_queue
    # Run every 60 seconds
    job_queue.run_repeating(check_active_tests, interval=60, first=10)

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
