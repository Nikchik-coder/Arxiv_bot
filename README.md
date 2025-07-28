# arXiv Notification Bot

A powerful Telegram bot that sends you notifications when new research papers are published on arXiv based on your interests. Stay updated with the latest research in your field with a user-friendly, button-driven interface.

## Features

- **Flexible Subscriptions**: Subscribe to both keywords and official arXiv categories.
- **Real-time Notifications**: Get notified when new papers match your interests.
- **Interactive Buttons**: Easily manage subscriptions and browse categories with a full button-based interface.
- **Category Support**: Subscribe to a wide range of official arXiv categories like `cs.AI`, `cs.LG`, `cond-mat`, etc.
- **Smart Search**: Keyword search across titles and abstracts.
- **Configurable**: Customize check intervals, message formatting, and more.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (get one from [@BotFather](https://t.me/BotFather))

### Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd arxiv_bot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the `config/` directory:
   ```env
   TELEGRAM_API_TOKEN=your_telegram_bot_token_here
   ```

4. **Run the bot from the project root**:
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

With the virtual environment activated, install the required packages. The `requirements.txt` file is configured to install `python-telegram-bot` with `job-queue` support, which is essential for the scheduled notification job to run.
```bash
pip install -r requirements.txt
```

### 4. Run the Bot

You can now run the bot:
```bash
python src/arxiv_bot.py
```

### Troubleshooting

- **`AttributeError: 'NoneType' object has no attribute 'run_repeating'`**: This error means that `python-telegram-bot` was installed without `job-queue` support. Ensure you have activated your virtual environment and have installed the packages from the updated `requirements.txt` file.

- **Deactivating the Environment**: When you are done, you can deactivate the virtual environment with a simple command:
  ```bash
  deactivate
  ```

## Bot Interface

The bot is designed to be fully interactive, with buttons guiding you through all its features.

| Button | Action |
|---|---|
| **Browse Categories** | Shows a list of popular arXiv categories to subscribe to with a single click. |
| **My Subscriptions** | View and manage your current subscriptions. Each subscription has an "Unsubscribe" button. |
| **Help** | Displays a help message with instructions on how to use the bot. |
| **Back to Main Menu** | Available in all sub-menus to easily navigate back. |

You can also use traditional commands like `/subscribe <keyword>` to subscribe to custom topics.

## File Structure

The project is organized into the following directories:

```
arxiv_bot/
├── src/
│   ├── arxiv_bot.py        # Main bot application logic
│   └── arxiv_search.py     # arXiv search and parsing functionality
├── config/
│   ├── config.py           # Configuration management
│   └── .env                # Environment variables (create this)
├── database/
│   ├── user_subscriptions.json # Stores user subscription data
│   └── notified_articles.json  # Tracks sent notifications
├── .gitignore
├── requirements.txt
└── README.md
```

## How It Works

The bot's functionality is split into two main parts: handling user interactions and periodically checking for new papers.

### 1. Parsing Papers from arXiv

- **What happens**: The bot uses the official `arxiv` Python library to connect to the arXiv API. When a user subscribes to a topic or a scheduled check runs, the `search_arxiv` function in `src/arxiv_search.py` is called.
- **How it works**:
  - **Category Search**: If you subscribe to a category (e.g., `cs.AI`), the bot constructs a query like `cat:cs.AI`.
  - **Keyword Search**: For keywords (e.g., "machine learning"), it builds a query like `ti:"machine learning" OR abs:"machine learning"` to search in the title and abstract.
  - **Filtering**: The search results are sorted by submission date, and only papers published within a configured time window (e.g., the last 24 hours) are considered new.
  - **Data Extraction**: For each new paper, the bot extracts the title, authors, summary (abstract), publication date, and a direct link to the PDF.

### 2. Notification Schedule

- **When it happens**: The bot checks for new articles at a regular interval, which is set to **every 60 minutes** by default. You can change this by setting the `CHECK_INTERVAL_MINUTES` variable in the `config/.env` file.
- **How it works**:
  - **Job Scheduler**: The `check_new_articles` function in `src/arxiv_bot.py` is scheduled to run automatically.
  - **Unique Topics**: It gathers all unique topics from all users' subscriptions to avoid redundant searches.
  - **Notification Delivery**: For each topic, it performs a search and, if new papers are found, it sends a notification to every user subscribed to that topic.
  - **Duplicate Prevention**: To avoid sending the same notification multiple times, the bot keeps a record of every paper it sends in `database/notified_articles.json`.

## Configuration

Customize the bot's behavior by creating a `.env` file in the `config/` directory. See `config/.example.env` for all available options.

### Required
- `TELEGRAM_API_TOKEN`

### Optional
- `CHECK_INTERVAL_MINUTES`
- `DAYS_BACK_FOR_NEW_ARTICLES`
- `MAX_RESULTS_PER_SEARCH`
- `MAX_ABSTRACT_LENGTH`
- ...and more.

## Contributing

Contributions are welcome! If you have ideas for new features or improvements, feel free to open an issue or submit a pull request.

## License

This project is open source. Feel free to use, modify, and distribute it. 