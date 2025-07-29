import logging
from logging.handlers import RotatingFileHandler
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
)
from telegram.constants import ParseMode
import re

# Add project root to path for module access    
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.arxiv_search import search_arxiv, get_popular_categories, validate_category
from config.config import Config
from database.database import (
    initialize_database, add_subscription, remove_subscription, 
    get_user_subscriptions, get_all_subscriptions,
    has_been_notified, add_notified_article, clean_old_notifications
)

# --- Constants ---
LOG_FILE = "logs/arxiv_bot.log"

# --- Logging Setup ---
def setup_logging():
    """Configures logging to file and console, filtering out verbose libraries."""
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Define a filter to exclude INFO-level logs from specific noisy loggers
    class InfoFilter(logging.Filter):
        def filter(self, record):
            # Exclude INFO logs from httpx, telegram's application, apscheduler, and arxiv
            if record.levelno == logging.INFO and record.name.startswith(('httpx', 'telegram.ext.Application', 'apscheduler', 'arxiv')):
                return False
            return True

    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # File handler with rotation
            RotatingFileHandler(
                LOG_FILE, 
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=2
            ),
            # Console handler
            logging.StreamHandler()
        ]
    )

    # Get the root logger
    root_logger = logging.getLogger()
    
    # Add the filter to all handlers
    for handler in root_logger.handlers:
        handler.addFilter(InfoFilter())

    logger = logging.getLogger(__name__)
    return logger

# Initialize logging
logger = setup_logging()

def escape_markdown_v2(text: str) -> str:
    """Escapes characters for Telegram's MarkdownV2 parse mode."""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

WELCOME_MESSAGE = """
🔬 *Welcome to the arXiv Notifier Bot\!*

I help you stay updated with the latest research papers on arXiv\.
Click the *MENU* button below to get started\.
"""

def get_main_menu_keyboard():
    """Returns the main menu inline keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📚 Browse Categories", callback_data='browse_categories'),
            InlineKeyboardButton("📋 My Subscriptions", callback_data='my_subscriptions')
        ],
        [
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_persistent_keyboard():
    """Returns the persistent keyboard with a MENU button."""
    keyboard = [[KeyboardButton("MENU")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the welcome message and persistent menu."""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_persistent_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_main_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a new message with the main menu."""
    await update.message.reply_text(
        "*Main Menu*\n\nHow can I help you\?",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def show_main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the main menu by editing the current message."""
    query = update.callback_query
    await query.message.edit_text(
        "*Main Menu*\n\nHow can I help you\?",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📚 *How to use this bot:*

*Keyword Subscriptions:*
Subscribe to any topic using keywords: `/subscribe machine learning`

*Category Subscriptions:*
Subscribe to official arXiv categories: `/subscribe cs\.AI`

*Popular Categories:*
• `cs.AI` \- Artificial Intelligence
• `cs.LG` \- Machine Learning
• `cond-mat` \- Condensed Matter
• `econ.EM` \- Econometrics
• `stat.ML` \- Statistics \- Machine Learning

Use `/categories` to see all popular categories\.
Use `/test <topic>` to preview what papers you'd get\.

*Tips:*
• You can subscribe to multiple topics
• Mix keywords and categories 
• Check `/mysubscriptions` to manage your subscriptions
    """
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if the command was triggered by a button press
    if update.callback_query:
        await update.callback_query.message.edit_text(help_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)

async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cats = get_popular_categories()
    query = update.callback_query
    user_id = update.effective_user.id
    
    user_topics = get_user_subscriptions(user_id)

    keyboard = []
    for cat_code, description in cats.items():
        is_subscribed = cat_code in user_topics
        
        button_text = f"{'✅ ' if is_subscribed else ''}{description} ({cat_code})"
        action = "unsub_cat" if is_subscribed else "sub_cat"
        
        button = InlineKeyboardButton(
            button_text, 
            callback_data=f"{action}:{cat_code}"
        )
        keyboard.append([button])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.edit_text(
        "📋 *Click a category to subscribe or unsubscribe:*", 
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text(
            "Please provide a topic to subscribe to\.\n\n"
            "Examples:\n"
            "• `/subscribe machine learning`\n"
            "• `/subscribe cs\.AI`\n"
            "• `/subscribe natural language processing`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    user_topics = get_user_subscriptions(user_id)
    
    if topic not in user_topics:
        add_subscription(user_id, topic)
        
        topic_type = "category" if validate_category(topic) else "keyword"
        await update.message.reply_text(
            f"✅ Successfully subscribed to {topic_type}: *{escape_markdown_v2(topic)}*\n\n"
            f"You'll receive notifications when new papers are published\!\n"
            f"Use `/test {escape_markdown_v2(topic)}` to see what papers you'd get\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
    else:
        await update.message.reply_text(f"You are already subscribed to *{escape_markdown_v2(topic)}*\.", parse_mode=ParseMode.MARKDOWN_V2)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses."""
    query = update.callback_query
    await query.answer()
    
    command, *args = query.data.split(':', 1)
    
    if command == 'main_menu':
        await show_main_menu_callback(update, context)
    elif command == 'browse_categories':
        await categories(update, context)
    elif command == 'my_subscriptions':
        await mysubscriptions(update, context)
    elif command == 'help':
        await help_command(update, context)
    elif command == 'sub_cat':
        topic = args[0]
        await subscribe_handler(update, context, topic, from_categories=True)
    elif command == 'unsub_cat':
        topic = args[0]
        await unsubscribe_handler(update, context, topic, from_categories=True)
    elif command == 'sub':
        topic = args[0]
        await subscribe_handler(update, context, topic)
    elif command == 'unsub':
        topic = args[0]
        await unsubscribe_handler(update, context, topic)

async def subscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, from_categories: bool = False):
    """Handles category subscription from a button press."""
    user_id = update.effective_user.id
    
    user_topics = get_user_subscriptions(user_id)
    
    if topic not in user_topics:
        add_subscription(user_id, topic)
        
    if from_categories:
        await categories(update, context)
    else:
        await mysubscriptions(update, context)

async def unsubscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, from_categories: bool = False):
    """Handles category unsubscription from a button press."""
    query = update.callback_query
    user_id = update.effective_user.id
    
    remove_subscription(user_id, topic)
    await query.answer(text=f"✅ Unsubscribed from {topic}")
    
    if from_categories:
        await categories(update, context)
    else:
        await mysubscriptions(update, context)

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text("Please provide a topic to unsubscribe from\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    remove_subscription(user_id, topic)
    await update.message.reply_text(f"🗑️ Unsubscribed from *{escape_markdown_v2(topic)}*\.", parse_mode=ParseMode.MARKDOWN_V2)

async def mysubscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    message = query.message if query else update.message
    user_id = update.effective_user.id
    
    user_topics = get_user_subscriptions(user_id)
    
    if user_topics:
        response = "📋 *Your Current Subscriptions:*\n"
        keyboard = []
        for topic in user_topics:
            button_text = f"🗑️ Unsubscribe: {topic}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"unsub:{topic}")
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.edit_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await message.edit_text(
            "You have no active subscriptions\.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')]]),
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def test_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text("Please provide a topic to test\.\nExample: `/test machine learning`", parse_mode=ParseMode.MARKDOWN_V2)
        return
    
    await update.message.reply_text(f"🔍 Searching for recent papers on *{escape_markdown_v2(topic)}*\.\.\.", parse_mode=ParseMode.MARKDOWN_V2)
    
    try:
        articles = search_arxiv(
            topic, 
            max_results=Config.MAX_TEST_RESULTS, 
            days_back=Config.DAYS_BACK_FOR_TEST_SEARCH
        )
        
        if not articles:
            await update.message.reply_text(
                f"No recent papers found for *{escape_markdown_v2(topic)}* in the last {Config.DAYS_BACK_FOR_TEST_SEARCH} days\.\n"
                f"Try a different topic or check if it's a valid arXiv category\.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
            return
        
        response = f"📄 *Recent papers for '{escape_markdown_v2(topic)}':*\n\n"
        for i, article in enumerate(articles, 1):
            response += format_article_message(article, i)
            response += "\n" + "─" * 50 + "\n\n"
        
        await update.message.reply_text(
            response, 
            parse_mode=ParseMode.MARKDOWN_V2, 
            disable_web_page_preview=not Config.ENABLE_WEB_PAGE_PREVIEW
        )
        
    except Exception as e:
        logger.error(f"Error in test search: {e}")
        await update.message.reply_text("Sorry, there was an error searching for papers\. Please try again later\.", parse_mode=ParseMode.MARKDOWN_V2)

def format_article_message(article, number=None):
    """Format article information into a readable message."""
    title = escape_markdown_v2(article['title'])
    
    authors = ", ".join(article['authors'][:Config.MAX_AUTHORS_DISPLAY])
    if len(article['authors']) > Config.MAX_AUTHORS_DISPLAY:
        authors += f" et al. ({len(article['authors'])} authors)"
    authors = escape_markdown_v2(authors)
    
    abstract = article['summary']
    if len(abstract) > Config.MAX_ABSTRACT_LENGTH:
        break_point = abstract.rfind('. ', 0, Config.MAX_ABSTRACT_LENGTH)
        if break_point > Config.MAX_ABSTRACT_LENGTH - 100:
            abstract = abstract[:break_point + 1]
        else:
            abstract = abstract[:Config.MAX_ABSTRACT_LENGTH] + "..."
    abstract = escape_markdown_v2(abstract)
    
    message = ""
    if number:
        message += f"*{number}.* "
    
    message += f"*{title}*\n\n"
    message += f"👥 *Authors:* {authors}\n"
    message += f"📅 *Published:* {escape_markdown_v2(article['published'])}\n"
    message += f"🏷️ *Category:* {escape_markdown_v2(article['primary_category'])}\n\n"
    message += f"📄 *Abstract:* {abstract}\n\n"
    message += f"🔗 [Read Paper]({article['pdf_url']})"
    
    return message

async def check_new_articles(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for new articles and notify subscribed users."""
    logger.info("Checking for new articles...")
    
    subscriptions = get_all_subscriptions()
    
    if not subscriptions:
        logger.info("No active subscriptions found")
        return
    
    all_topics = set(topic for user_topics in subscriptions.values() for topic in user_topics)
    logger.info(f"Checking {len(all_topics)} unique topics")

    newly_notified_articles = set()
    popular_categories = get_popular_categories()

    for topic in all_topics:
        try:
            articles = search_arxiv(
                topic, 
                max_results=Config.MAX_RESULTS_PER_SEARCH, 
                days_back=Config.DAYS_BACK_FOR_NEW_ARTICLES
            )
            
            for article in articles:
                article_id = article['id']
                
                display_topic = escape_markdown_v2(popular_categories.get(topic, topic))
                message = f"🔔 *New arXiv Paper Alert\!*\n\n"
                message += f"📍 *Topic:* {display_topic}\n\n"
                message += format_article_message(article)

                for user_id_str, user_topics in subscriptions.items():
                    user_id = int(user_id_str)
                    if topic in user_topics:
                        if not has_been_notified(user_id, article_id):
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id, 
                                    text=message, 
                                    parse_mode=ParseMode.MARKDOWN_V2,
                                    disable_web_page_preview=not Config.ENABLE_WEB_PAGE_PREVIEW
                                )
                                logger.info(f"Notification for article {article_id} sent to user {user_id} for topic '{topic}'")
                                
                                newly_notified_articles.add(article_id)
                                add_notified_article(user_id, article_id)
                                
                            except Exception as e:
                                logger.error(f"Failed to send message to {user_id}: {e}")
                        else:
                            logger.info(f"Skipping article {article_id} for user {user_id} (already notified)")
                    
        except Exception as e:
            logger.error(f"Error checking topic '{topic}': {e}")

    if newly_notified_articles:
        logger.info(f"Found and notified users about {len(newly_notified_articles)} new articles.")

    all_user_ids = subscriptions.keys()
    for user_id_str in all_user_ids:
        user_id = int(user_id_str)
        clean_old_notifications(user_id, Config.MAX_NOTIFICATION_HISTORY)
    
    logger.info("Finished checking for new articles")

def main() -> None:
    """Start the bot."""
    initialize_database()
    
    # Override the check interval to 1 minute
    Config.CHECK_INTERVAL_MINUTES = 1
    
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return
        
    application = Application.builder().token(Config.TELEGRAM_API_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("mysubscriptions", mysubscriptions))
    application.add_handler(CommandHandler("categories", categories))
    application.add_handler(CommandHandler("test", test_search))

    # Add button handler and menu handler
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.Regex('^MENU$'), show_main_menu_message))

    # Schedule the job to check for new articles
    job_queue = application.job_queue
    job_queue.run_repeating(
        check_new_articles, 
        interval=Config.get_check_interval_seconds(), 
        first=10
    )

    logger.info(f"Bot starting... Will check for new articles every {Config.CHECK_INTERVAL_MINUTES} minutes")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()