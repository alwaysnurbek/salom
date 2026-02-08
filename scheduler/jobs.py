from telegram.ext import ContextTypes
import db.queries as db
from services.exporter import generate_leaderboard_html
from io import BytesIO
from datetime import datetime
import logging
import config

logger = logging.getLogger(__name__)

async def check_active_tests(context: ContextTypes.DEFAULT_TYPE):
    """
    Periodic job to check for expired tests.
    """
    now = datetime.now()
    expired_tests = db.get_active_tests_needing_end(now)
    
    for test in expired_tests:
        test_id = test['id']
        logger.info(f"Auto-ending expired test #{test_id}")
        
        # End it
        db.end_test_db(test_id)
        
        # Generate Leaderboard
        submissions = db.get_test_submissions(test_id)
        if not submissions:
            continue
            
        html_content = generate_leaderboard_html(test['title'], submissions)
        file_obj = BytesIO(html_content.encode('utf-8'))
        file_obj.name = f"leaderboard_test_{test_id}_{now.strftime('%H%M')}.html"
        
        # Send to valid admins
        # We need a chat_id to send to. Usually we send to ADMIN_USER_IDS.
        # But send_document requires a chat_id (which is user_id in private chat).
        # We'll try to send to all admins defined in config.
        message = (
            f"🏁 <b>Test #{test_id} has ended!</b>\n"
            f"Title: {test['title']}\n"
            f"Total Submissions: {len(submissions)}\n\n"
            "Top 3:\n"
        )
        
        for i, sub in enumerate(submissions[:3], 1):
             message += f"{i}. {sub['full_name']} - {sub['percent']}%\n"
             
        for admin_id in config.ADMIN_USER_IDS:
            try:
                # Reset stream position for each send
                file_obj.seek(0)
                await context.bot.send_document(
                    chat_id=admin_id,
                    document=file_obj,
                    caption=message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Failed to send leaderboard to admin {admin_id}: {e}")
