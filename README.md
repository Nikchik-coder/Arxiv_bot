# arXiv Notification Bot

A powerful and user-friendly Telegram bot that uses a persistent, button-driven interface to send you real-time notifications for new arXiv research papers based on your interests.

## Features

- **User-Friendly Interface**: A fully interactive, button-based menu that makes managing subscriptions a breeze.
- **Flexible Subscriptions**: Subscribe to both keywords (e.g., "quantum computing") and official arXiv categories (e.g., `cs.AI`).
- **Real-time, Smart Notifications**: Get notified within minutes of a new paper being published. The bot uses a precise time window to prevent notification floods, especially on the first run.
- **Robust & Scalable**: Uses an SQLite database to reliably store user subscriptions and notified articles, ensuring data integrity and performance.
- **Configurable**: Customize check intervals, message formatting, and more using environment variables.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get one from [@BotFather](https://t.me/BotFather))

### Installation

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd arxiv_bot
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up environment variables**:
    Create a `.env` file in the `config/` directory. You can copy the `config/.env.example` file as a template.
    ```env
    # Required
    TELEGRAM_API_TOKEN=your_telegram_bot_token_here

    # Optional: How often, in minutes, to check for new articles (default: 60)
    CHECK_INTERVAL_MINUTES=60 
    ```

4.  **Run the bot from the project root**:
    ```bash
    python src/arxiv_bot.py
    ```

## Deploying on a Server

When deploying the bot on a Linux server (e.g., Ubuntu), follow these steps to ensure a smooth setup.

### 1. Install Virtual Environment Tools (If Needed)

On some systems, you may need to install the package for creating virtual environments first.
```bash
sudo apt update
sudo apt install python3.12-venv
```

### 2. Create and Activate Virtual Environment

Navigate to your project directory and create a virtual environment.
```bash
cd /path/to/your/project
python3 -m venv venv
source venv/bin/activate
```
Your command prompt should change to indicate that you are now operating within the virtual environment.

### 3. Install Dependencies

With the virtual environment activated, install the required packages.
```bash
pip install -r requirements.txt
```

### 4. Run the Bot

You can now run the bot:
```bash
python src/arxiv_bot.py
```

## Bot Interface

The bot is designed to be fully interactive. Use the persistent **MENU** button to access all features.

| Button              | Action                                                                              |
| ------------------- | ----------------------------------------------------------------------------------- |
| **Browse Categories** | Shows a list of popular arXiv categories to subscribe to with a single click.       |
| **My Subscriptions**  | View and manage your current subscriptions. Each subscription has an "Unsubscribe" button. |
| **Help**              | Displays a detailed help message with instructions on how to use the bot.           |

You can also use traditional commands like `/subscribe <keyword>` to subscribe to custom topics.

## File Structure

The project is organized into the following directories:

```
arxiv_bot/
├── src/
│   ├── arxiv_bot.py        # Main bot application logic
│   └── arxiv_search.py     # arXiv search and parsing functionality
├── database/
│   └── arxiv_bot.db        # SQLite database for all user data
├── config/
│   ├── config.py           # Configuration management
│   └── .env.example        # Example environment variables
├── logs/
│   └── arxiv_bot.log       # Application log file
├── .gitignore
├── requirements.txt
└── README.md
```

## How It Works

The bot's functionality is split into two main parts: handling user interactions and periodically checking for new papers.

### 1. The "Trickle" Notification Method (No More Floods!)

To avoid overwhelming users with a flood of articles, especially when the bot first starts, it uses a smart and precise time window for finding new papers.

- **The Problem:** A simple bot might ask arXiv for all papers from the "last 24 hours." On the first run, this would result in hundreds of notifications, which is a poor user experience.
- **The Solution:** This bot uses a much smaller, rolling time window. If it's configured to check every **1 minute**, it will only search for papers published in the last **6 minutes** (1-minute interval + 5-minute safety buffer). This ensures:
    1.  **No Initial Flood**: On the first run, you only get papers from the last few minutes, not the whole day.
    2.  **Timely Notifications**: You are notified of new papers within minutes of their publication.
    3.  **Efficiency**: The bot makes very small, fast requests to the arXiv API.

### 2. Reliable Data Storage with SQLite

All user data, including subscriptions and which articles have already been sent, is stored in a robust **SQLite database** (`database/arxiv_bot.db`).

- **Why not JSON?** Simple text files like JSON are prone to data loss and corruption, especially with many users.
- **Why SQLite?** It's a lightweight, reliable, and professional database that is built into Python. It ensures that your subscriptions are stored safely and efficiently.

### 3. Parsing Papers from arXiv

- **What happens**: When a user subscribes to a topic or a scheduled check runs, the `search_arxiv` function in `src/arxiv_search.py` is called.
- **How it works**:
    - **Category Search**: If you subscribe to a category (e.g., `cs.AI`), the bot constructs a query like `cat:cs.AI`.
    - **Keyword Search**: For keywords (e.g., "machine learning"), it builds a query like `ti:"machine learning" OR abs:"machine learning"` to search in the title and abstract.
    - **Data Extraction**: For each new paper, the bot extracts the title, authors, summary (abstract), publication date, and a direct link to the PDF.

## Configuration

Customize the bot's behavior by creating a `.env` file in the `config/` directory. You can use `config/.env.example` as a starting point.

### Required
- `TELEGRAM_API_TOKEN`

### Optional
- `CHECK_INTERVAL_MINUTES`
- `SEARCH_BUFFER_MINUTES`
- `MAX_RESULTS_PER_SEARCH`
- `MAX_ABSTRACT_LENGTH`
- ...and more. See the `.env.example` file for all available options.

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, feel free to open an issue or submit a pull request.

## License

This project is open source. Feel free to use, modify, and distribute it. 