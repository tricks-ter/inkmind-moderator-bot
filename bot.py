import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Gemini Client for Smart Moderation
ai_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a professional welcome message when the command /start is issued."""
    welcome_text = (
        "🤖 Hello! I am the Exhibition Moderator Bot.\n\n"
        "I provide professional group management, including:\n"
        "🛡️ AI-powered toxicity & spam filtering\n"
        "👋 Automated welcome messages\n"
        "⚖️ Rule enforcement\n\n"
        "Add me to your group and grant me Admin privileges to begin."
    )
    await update.message.reply_text(welcome_text)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the group rules."""
    group_rules = (
        "📜 *Professional Exhibition Rules:*\n"
        "1. Be respectful to all members.\n"
        "2. No spam or unsolicited promotions.\n"
        "3. Keep discussions relevant to the exhibition/topic.\n"
        "4. Profanity and toxic behavior will result in a ban."
    )
    await update.message.reply_text(group_rules, parse_mode='Markdown')

async def check_message_toxicity(text: str) -> bool:
    """Uses Google Gemini to classify if a message is toxic, spam, or highly inappropriate."""
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

async def moderate_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor group messages and delete toxic content."""
    if not update.message or not update.message.text:
        return

    # Skip moderation for admins
    if update.message.chat.type in ['group', 'supergroup']:
        chat_admins = await context.bot.get_chat_administrators(update.message.chat_id)
        is_admin = any(admin.user.id == update.message.from_user.id for admin in chat_admins)
        if is_admin:
            return

    text = update.message.text
    user = update.message.from_user
    
    # Simple keyword filter
    banned_words = ['scam', 'crypto dump', 'fake link']
    if any(word in text.lower() for word in banned_words):
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        await context.bot.send_message(
            chat_id=update.message.chat_id, 
            text=f"⚠️ Message from {user.first_name} was removed due to banned keywords."
        )
        return

    # Advanced AI filtering
    if await check_message_toxicity(text):
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
        await context.bot.send_message(
            chat_id=update.message.chat_id, 
            text=f"🛑 {user.first_name}, your message was flagged by the AI moderator for violating community guidelines."
        )

async def welcome_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome new users when they join the group."""
    for new_member in update.message.new_chat_members:
        # Ignore bots joining
        if new_member.is_bot:
            continue
            
        welcome_text = (
            f"Welcome to the group, {new_member.first_name}! 🎉\n"
            f"Please type /rules to read the community guidelines."
        )
        await context.bot.send_message(chat_id=update.message.chat_id, text=welcome_text)

def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is not set in the .env file!")
        return

    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("rules", rules))

    # New Members
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_members))

    # Moderation (Listen to all text messages)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), moderate_messages))

    # Run the bot
    logger.info("Bot is polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
