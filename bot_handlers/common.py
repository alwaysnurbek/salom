from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import config

# Conversation states
ASK_TITLE, ASK_QUESTIONS, ASK_DURATION, ASK_CONFIRM, ASK_ANSWER_KEY = range(5)
REGISTER_NAME, REGISTER_REGION = range(2)
# New state for broadcast
ASK_BROADCAST_MSG = 10

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_USER_IDS

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Amal bekor qilindi.")
    return ConversationHandler.END

async def check_is_subscribed(bot, user_id: int) -> bool:
    """Checks if the user is a member of the required channel."""
    try:
        member = await bot.get_chat_member(chat_id=config.REQUIRED_CHANNEL_ID, user_id=user_id)
        # 'left' means they are not a member. 'kicked' means banned.
        # 'creator', 'administrator', 'member', 'restricted' are valid (restricted depends, but usually implies presence)
        if member.status in ['left', 'kicked']:
            return False
        return True
    except Exception as e:
        # If bot is not admin in channel or ID is wrong, it might raise error. 
        # Assume False or log error? For safety, let's log and assume True to not block users if config is wrong?
        # No, strict mode: False. User implies they WANT to block.
        # But if bot can't see the channel, it's a problem. 
        # Let's assume False and let the user complain if it's broken configuration.
        # Actually, better to print/log it.
        print(f"Error checking subscription: {e}")
        return False

