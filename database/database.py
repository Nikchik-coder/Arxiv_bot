import sqlite3
import os
from threading import Lock

# --- Database Setup ---
DB_FILE = os.path.join(os.path.dirname(__file__), 'arxiv_bot.db')
db_lock = Lock()

def get_db_connection():
    """Creates a thread-safe database connection."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def initialize_database():
    """Initializes the database and creates tables if they don't exist."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create user_subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                PRIMARY KEY (user_id, topic)
            )
        ''')
        
        # Create notified_articles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notified_articles (
                user_id INTEGER NOT NULL,
                article_id TEXT NOT NULL,
                PRIMARY KEY (user_id, article_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully.")

# --- Subscription Management ---

def add_subscription(user_id: int, topic: str):
    """Adds a new topic subscription for a user."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO user_subscriptions (user_id, topic) VALUES (?, ?)", (user_id, topic))
        conn.commit()
        conn.close()

def remove_subscription(user_id: int, topic: str):
    """Removes a topic subscription for a user."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_subscriptions WHERE user_id = ? AND topic = ?", (user_id, topic))
        conn.commit()
        conn.close()

def get_user_subscriptions(user_id: int) -> list:
    """Retrieves all topic subscriptions for a user."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT topic FROM user_subscriptions WHERE user_id = ?", (user_id,))
        topics = [row[0] for row in cursor.fetchall()]
        conn.close()
        return topics

def get_all_subscriptions() -> dict:
    """Retrieves all subscriptions for all users."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, topic FROM user_subscriptions")
        subscriptions = {}
        for user_id, topic in cursor.fetchall():
            if str(user_id) not in subscriptions:
                subscriptions[str(user_id)] = []
            subscriptions[str(user_id)].append(topic)
        conn.close()
        return subscriptions

# --- Notification Management ---

def has_been_notified(user_id: int, article_id: str) -> bool:
    """Checks if a user has already been notified about an article."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM notified_articles WHERE user_id = ? AND article_id = ?", (user_id, article_id))
        result = cursor.fetchone()
        conn.close()
        return result is not None

def add_notified_article(user_id: int, article_id: str):
    """Adds a record that a user has been notified about an article."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO notified_articles (user_id, article_id) VALUES (?, ?)", (user_id, article_id))
        conn.commit()
        conn.close()

def clean_old_notifications(user_id: int, max_history: int):
    """Keeps only the most recent `max_history` notifications for a user."""
    with db_lock:
        conn = get_db_connection()
        cursor = conn.cursor()
        # This is a simplified cleanup. A timestamp-based cleanup would be more robust.
        # For now, we get all, and if they exceed max_history, we delete the oldest ones.
        cursor.execute("SELECT article_id FROM notified_articles WHERE user_id = ? ORDER BY rowid DESC", (user_id,))
        all_articles = [row[0] for row in cursor.fetchall()]
        
        if len(all_articles) > max_history:
            articles_to_delete = all_articles[max_history:]
            cursor.executemany("DELETE FROM notified_articles WHERE user_id = ? AND article_id = ?", [(user_id, article) for article in articles_to_delete])
            conn.commit()
        
        conn.close() 