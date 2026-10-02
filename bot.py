import os
import logging
import aiosqlite
from datetime import timedelta
from dotenv import load_dotenv
from telegram import Update, ChatPermissions
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, Application
from google import genai

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Gemini Client for Smart Moderation
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Local basic filter (Cost Optimization before hitting AI)
LOCAL_BANNED_WORDS = {'scam', 'crypto dump', 'fake link', 'free money', 'ponzi'}

async def init_db(application: Application):
    """Database initialization on startup."""
    async with aiosqlite.connect("moderation.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, warnings INTEGER DEFAULT 0)")
        await db.commit()
    logger.info("Database initialized successfully.")

async def get_warnings(user_id: int) -> int:
    async with aiosqlite.connect("moderation.db") as db:
        async with db.execute("SELECT warnings FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_warning(user_id: int) -> int:
    async with aiosqlite.connect("moderation.db") as db:
        await db.execute(
            "INSERT INTO users (user_id, warnings) VALUES (?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET warnings = warnings + 1",
            (user_id,)
        )
        await db.commit()
        return await get_warnings(user_id)

async def log_audit(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Sends audit logs to a private admin channel."""
    logger.info(f"AUDIT: {message}")
    if LOG_CHANNEL_ID:
        try:
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"🚨 *Audit Log*\n{message}", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send audit log: {e}")

async def check_message_toxicity(text: str) -> bool:
    """Uses Google Gemini to classify if a message is severely toxic or spam."""
    if not ai_client or not text:
        return False
    try:
        prompt = f"""
        Analyze the following message for severe toxicity, hate speech, explicit content, or obvious spam.
        Message: "{text}"
        If it violates professional group rules, respond with exactly 'VIOLATION'. 
        Otherwise, respond with 'SAFE'.
        """
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return "VIOLATION" in response.text.upper()
    except Exception as e:
        logger.error(f"AI Classification Error: {e}")
        return False

async def apply_strike(update: Update, context: ContextTypes.DEFAULT_TYPE, user, reason: str):
    """Applies a strike to the user and enforces ban/mute rules."""
    warnings = await add_warning(user.id)
    chat_id = update.message.chat_id
    
    await log_audit(context, f"User {user.first_name} ({user.id}) received strike {warnings}. Reason: {reason}")
    
    if warnings == 1:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ {user.first_name}, this is your first warning: {reason}.")
    elif warnings == 2:
        await context.bot.restrict_chat_member(
            chat_id, user.id, permissions=ChatPermissions(can_send_messages=False), until_date=update.message.date + timedelta(hours=24)
        )
        await context.bot.send_message(chat_id=chat_id, text=f"🔇 {user.first_name} has been muted for 24 hours (Strike 2).")
    else:
        await context.bot.ban_chat_member(chat_id, user.id)
        await context.bot.send_message(chat_id=chat_id, text=f"⛔ {user.first_name} has been permanently banned (Strike 3).")

async def moderate_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor group messages and process through filters."""
    if not update.message or not update.message.text:
        return

    # Admin Bypass
    if update.message.chat.type in ['group', 'supergroup']:
        chat_admins = await context.bot.get_chat_administrators(update.message.chat_id)
        if any(admin.user.id == update.message.from_user.id for admin in chat_admins):
            return

    text = update.message.text
    user = update.message.from_user
    
    # 1. Local Cost-Optimization Filter
    if any(word in text.lower() for word in LOCAL_BANNED_WORDS):
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        await apply_strike(update, context, user, "Used banned keywords")
        return

    # 2. Advanced AI Filtering
    if await check_message_toxicity(text):
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        await apply_strike(update, context, user, "AI detected community guideline violation")

async def admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual ban command for admins: /ban (in reply to a message)"""
    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to a user's message to ban them.")
        return
        
    chat_admins = await context.bot.get_chat_administrators(update.message.chat_id)
    if not any(admin.user.id == update.message.from_user.id for admin in chat_admins):
        return # Not an admin

    target_user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.message.chat_id, target_user.id)
    await update.message.reply_text(f"🔨 {target_user.first_name} has been manually banned by an admin.")
    await log_audit(context, f"Admin {update.message.from_user.id} manually banned {target_user.id}.")

def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).post_init(init_db).build()

    # Commands
    application.add_handler(CommandHandler("ban", admin_ban))
    
    # Moderation
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), moderate_messages))

    logger.info("InkMind Enterprise Moderator Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
