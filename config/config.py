import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration settings for the arXiv bot."""
    
    # Telegram Bot Settings
    TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
    
    # Data Storage Settings
    USER_SUBSCRIPTIONS_FILE = os.getenv("USER_SUBSCRIPTIONS_FILE", "user_subscriptions.json")
    NOTIFIED_ARTICLES_FILE = os.getenv("NOTIFIED_ARTICLES_FILE", "notified_articles.json")
    
    # ArXiv Search Settings
    MAX_RESULTS_PER_SEARCH = int(os.getenv("MAX_RESULTS_PER_SEARCH", "100"))
    DAYS_BACK_FOR_NEW_ARTICLES = int(os.getenv("DAYS_BACK_FOR_NEW_ARTICLES", "1"))
    SEARCH_BUFFER_MINUTES = int(os.getenv("SEARCH_BUFFER_MINUTES", "5")) # Look back N extra minutes
    MINIMUM_SEARCH_WINDOW_MINUTES = int(os.getenv("MINIMUM_SEARCH_WINDOW_MINUTES", "10")) # Ensures the bot always looks back at least this many minutes
    DAYS_BACK_FOR_TEST_SEARCH = int(os.getenv("DAYS_BACK_FOR_TEST_SEARCH", "7"))
    MAX_TEST_RESULTS = int(os.getenv("MAX_TEST_RESULTS", "3"))
    
    # Notification Settings
    CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "60"))  # How often to check for new articles
    MAX_ABSTRACT_LENGTH = int(os.getenv("MAX_ABSTRACT_LENGTH", "700"))  # Max characters in abstract
    MAX_AUTHORS_DISPLAY = int(os.getenv("MAX_AUTHORS_DISPLAY", "3"))  # Max authors to show
    
    # Performance Settings
    MAX_NOTIFICATION_HISTORY = int(os.getenv("MAX_NOTIFICATION_HISTORY", "1000"))  # Keep last N notifications
    
    # Bot Behavior Settings
    ENABLE_WEB_PAGE_PREVIEW = os.getenv("ENABLE_WEB_PAGE_PREVIEW", "false").lower() == "true"
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is present."""
        if not cls.TELEGRAM_API_TOKEN:
            raise ValueError("TELEGRAM_API_TOKEN is required but not found in environment variables")
        
        return True
    
    @classmethod
    def get_check_interval_seconds(cls):
        """Get the check interval in seconds for the job scheduler."""
        return cls.CHECK_INTERVAL_MINUTES * 60 