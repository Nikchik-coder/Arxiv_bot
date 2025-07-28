import logging
import json
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Add project root to path for module access    
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.arxiv_search import search_arxiv, get_popular_categories, validate_category
from config.config import Config

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_data(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)

WELCOME_MESSAGE = """
🔬 **Welcome to the arXiv Notifier Bot!**

I help you stay updated with the latest research papers on arXiv.
"""

def get_main_menu_keyboard():
    """Returns the main menu keyboard."""
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends the welcome message and main menu."""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the main menu by editing the current message."""
    query = update.callback_query
    await query.message.edit_text(
        WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard(),
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
📚 **How to use this bot:**

**Keyword Subscriptions:**
Subscribe to any topic using keywords: `/subscribe machine learning`

**Category Subscriptions:**
Subscribe to official arXiv categories: `/subscribe cs.AI`

**Popular Categories:**
• `cs.AI` - Artificial Intelligence
• `cs.LG` - Machine Learning
• `cond-mat` - Condensed Matter
• `econ.EM` - Econometrics
• `stat.ML` - Statistics - Machine Learning

Use `/categories` to see all popular categories.
Use `/test <topic>` to preview what papers you'd get.

**Tips:**
• You can subscribe to multiple topics
• Mix keywords and categories 
• Check `/mysubscriptions` to manage your subscriptions
    """
    
    keyboard = [[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if the command was triggered by a button press
    if update.callback_query:
        await update.callback_query.message.edit_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

async def categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cats = get_popular_categories()
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    user_topics = subscriptions.get(user_id, [])

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
        "📋 **Click a category to subscribe or unsubscribe:**", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text(
            "Please provide a topic to subscribe to.\n\n"
            "Examples:\n"
            "• `/subscribe machine learning`\n"
            "• `/subscribe cs.AI`\n"
            "• `/subscribe natural language processing`"
        )
        return

    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    if user_id not in subscriptions:
        subscriptions[user_id] = []
    
    if topic not in subscriptions[user_id]:
        subscriptions[user_id].append(topic)
        save_data(subscriptions, Config.USER_SUBSCRIPTIONS_FILE)
        
        # Determine if it's a category or keyword
        topic_type = "category" if validate_category(topic) else "keyword"
        await update.message.reply_text(
            f"✅ Successfully subscribed to {topic_type}: **{topic}**\n\n"
            f"You'll receive notifications when new papers are published!\n"
            f"Use `/test {topic}` to see what papers you'd get.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"You are already subscribed to **{topic}**.", parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses."""
    query = update.callback_query
    await query.answer()
    
    command, *args = query.data.split(':', 1)
    
    if command == 'main_menu':
        await show_main_menu(update, context)
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
    user_id = str(update.effective_user.id)
    
    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    if user_id not in subscriptions:
        subscriptions[user_id] = []
    
    if topic not in subscriptions[user_id]:
        subscriptions[user_id].append(topic)
        save_data(subscriptions, Config.USER_SUBSCRIPTIONS_FILE)
        
        # After subscribing, show the updated subscriptions list
        if from_categories:
            await categories(update, context)
        else:
            await mysubscriptions(update, context)
    else:
        # If already subscribed, just show the subscriptions list
        if from_categories:
            await categories(update, context)
        else:
            await mysubscriptions(update, context)

async def unsubscribe_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str, from_categories: bool = False):
    """Handles category unsubscription from a button press."""
    query = update.callback_query
    user_id = str(update.effective_user.id)
    
    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    if user_id in subscriptions and topic in subscriptions[user_id]:
        subscriptions[user_id].remove(topic)
        if not subscriptions[user_id]:
            del subscriptions[user_id]
        save_data(subscriptions, Config.USER_SUBSCRIPTIONS_FILE)
        
        await query.answer(text=f"✅ Unsubscribed from {topic}")
        
        # After unsubscribing, refresh the list
        if from_categories:
            await categories(update, context)
        else:
            await mysubscriptions(update, context)
    else:
        await query.answer(text=f"You are no longer subscribed to {topic}")

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text("Please provide a topic to unsubscribe from.")
        return

    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    if user_id in subscriptions and topic in subscriptions[user_id]:
        subscriptions[user_id].remove(topic)
        if not subscriptions[user_id]:
            del subscriptions[user_id]
        save_data(subscriptions, Config.USER_SUBSCRIPTIONS_FILE)
        await update.message.reply_text(f"❌ Unsubscribed from **{topic}**.", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"You are not subscribed to **{topic}**.", parse_mode='Markdown')

async def mysubscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # This function can be called by a command or a button press,
    # so we need to handle both `update.message` and `update.callback_query`
    query = update.callback_query
    message = query.message if query else update.message
    user_id = str(update.effective_user.id)
    
    subscriptions = load_data(Config.USER_SUBSCRIPTIONS_FILE)
    user_topics = subscriptions.get(user_id, [])
    
    if user_topics:
        response = "📋 **Your Current Subscriptions:**\n"
        keyboard = []
        for topic in user_topics:
            topic_type = "📁 Category" if validate_category(topic) else "🔍 Keyword"
            button_text = f"❌ Unsubscribe from {topic_type}: {topic}"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"unsub:{topic}")
            ])
        
        keyboard.append([InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.edit_text(response, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await message.edit_text(
            "You have no active subscriptions.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data='main_menu')]]),
            parse_mode='Markdown'
        )

async def test_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    topic = ' '.join(context.args).strip()
    
    if not topic:
        await update.message.reply_text("Please provide a topic to test.\nExample: `/test machine learning`")
        return
    
    await update.message.reply_text(f"🔍 Searching for recent papers on **{topic}**...", parse_mode='Markdown')
    
    try:
        articles = search_arxiv(
            topic, 
            max_results=Config.MAX_TEST_RESULTS, 
            days_back=Config.DAYS_BACK_FOR_TEST_SEARCH
        )
        
        if not articles:
            await update.message.reply_text(
                f"No recent papers found for **{topic}** in the last {Config.DAYS_BACK_FOR_TEST_SEARCH} days.\n"
                f"Try a different topic or check if it's a valid arXiv category.",
                parse_mode='Markdown'
            )
            return
        
        response = f"📄 **Recent papers for '{topic}':**\n\n"
        for i, article in enumerate(articles, 1):
            response += format_article_message(article, i)
            response += "\n" + "─" * 50 + "\n\n"
        
        await update.message.reply_text(
            response, 
            parse_mode='Markdown', 
            disable_web_page_preview=not Config.ENABLE_WEB_PAGE_PREVIEW
        )
        
    except Exception as e:
        logger.error(f"Error in test search: {e}")
        await update.message.reply_text("Sorry, there was an error searching for papers. Please try again later.")

def format_article_message(article, number=None):
    """Format article information into a readable message."""
    title = article['title']
    
    # Format authors
    authors = ", ".join(article['authors'][:Config.MAX_AUTHORS_DISPLAY])
    if len(article['authors']) > Config.MAX_AUTHORS_DISPLAY:
        authors += f" et al. ({len(article['authors'])} authors)"
    
    # Truncate abstract intelligently
    abstract = article['summary']
    if len(abstract) > Config.MAX_ABSTRACT_LENGTH:
        # Find a good break point near the limit
        break_point = abstract.rfind('. ', 0, Config.MAX_ABSTRACT_LENGTH)
        if break_point > Config.MAX_ABSTRACT_LENGTH - 100:  # If we found a good break point
            abstract = abstract[:break_point + 1]
        else:
            abstract = abstract[:Config.MAX_ABSTRACT_LENGTH] + "..."
    
    message = ""
    if number:
        message += f"**{number}.** "
    
    message += f"**{title}**\n\n"
    message += f"👥 **Authors:** {authors}\n"
    message += f"📅 **Published:** {article['published']}\n"
    message += f"🏷️ **Category:** {article['primary_category']}\n\n"
    message += f"📄 **Abstract:** {abstract}\n\n"
    message += f"🔗 [**Read Paper**]({article['pdf_url']})"
    
    return message

async def check_new_articles(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check for new articles and notify subscribed users."""
    logger.info("Checking for new articles...")
    
    subscriptions = load_data(context.job.data['user_subscriptions_file'])
    notified_articles = load_data(context.job.data['notified_articles_file'])
    
    if not subscriptions:
        logger.info("No active subscriptions found")
        return
    
    all_topics = set(topic for user_topics in subscriptions.values() for topic in user_topics)
    logger.info(f"Checking {len(all_topics)} unique topics")

    for topic in all_topics:
        try:
            articles = search_arxiv(
                topic, 
                max_results=Config.MAX_RESULTS_PER_SEARCH, 
                days_back=Config.DAYS_BACK_FOR_NEW_ARTICLES
            )
            
            for article in articles:
                article_id = article['id']
                
                message = f"🔔 **New arXiv Paper Alert!**\n\n"
                message += f"📍 **Topic:** {topic}\n\n"
                message += format_article_message(article)

                # Send to all users subscribed to this topic who haven't seen this article
                for user_id, user_topics in subscriptions.items():
                    if topic in user_topics:
                        # Check if user has already been notified for this article
                        if article_id not in notified_articles.get(user_id, []):
                            try:
                                await context.bot.send_message(
                                    chat_id=user_id, 
                                    text=message, 
                                    parse_mode='Markdown',
                                    disable_web_page_preview=not Config.ENABLE_WEB_PAGE_PREVIEW
                                )
                                logger.info(f"Notification for article {article_id} sent to user {user_id}")
                                
                                # Mark as notified for this user
                                if user_id not in notified_articles:
                                    notified_articles[user_id] = []
                                notified_articles[user_id].append(article_id)
                                
                            except Exception as e:
                                logger.error(f"Failed to send message to {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error checking topic '{topic}': {e}")

    # Clean up old notifications for each user
    for user_id in notified_articles:
        if len(notified_articles[user_id]) > Config.MAX_NOTIFICATION_HISTORY:
            notified_articles[user_id] = notified_articles[user_id][-Config.MAX_NOTIFICATION_HISTORY:]
    
    save_data(notified_articles, context.job.data['notified_articles_file'])
    logger.info("Finished checking for new articles")

def initialize_paths():
    """Initializes and sets the absolute paths for data files."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    Config.USER_SUBSCRIPTIONS_FILE = os.path.join(base_dir, 'database', 'user_subscriptions.json')
    Config.NOTIFIED_ARTICLES_FILE = os.path.join(base_dir, 'database', 'notified_articles.json')

def main() -> None:
    """Start the bot."""
    initialize_paths()
    
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

    # Add button handler
    application.add_handler(CallbackQueryHandler(button_handler))

    # Schedule the job to check for new articles
    job_queue = application.job_queue
    job_context = {
        'user_subscriptions_file': Config.USER_SUBSCRIPTIONS_FILE,
        'notified_articles_file': Config.NOTIFIED_ARTICLES_FILE
    }
    job_queue.run_repeating(
        check_new_articles, 
        interval=Config.get_check_interval_seconds(), 
        first=10,
        data=job_context
    )

    logger.info(f"Bot starting... Will check for new articles every {Config.CHECK_INTERVAL_MINUTES} minutes")
    # Run the bot until the user presses Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()