# BluePrep Telegram Bot

A robust, Telegram-based testing bot for BluePrep.

## Features
- **Admin Panel**: Manage tests, answer keys, and leaderboards entirely within Telegram (`/admin`).
- **Student Flow**: Simple registration and answer submission (`TestID*Answers`).
- **Auto-Grading**: Instant feedback on submissions.
- **Leaderboards**: Auto-generated HTML leaderboards sent to admins when tests end.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**
   Copy `.env.example` to `.env` and fill in your details:
   ```bash
   cp .env.example .env
   ```
   - `BOT_TOKEN`: From @BotFather
   - `ADMIN_USER_IDS`: Comma-separated list of Telegram User IDs who can access `/admin`.

3. **Run the Bot**
   ```bash
   python main.py
   ```
   The database (`bluebot.db`) will be initialized automatically.

## Usage Guide

### Admin
1. Type `/admin` to open the panel.
2. Click **➕ Create Test**.
3. Follow the wizard (Title -> Q Count -> Duration).
4. After creation, click **✍️ Set Answer Key** and send the key (e.g., `ABCD...` or `1A 2B...`).
5. Click **▶️ Start Now** to activate the test.
6. When the duration expires, the bot will automatically end the test and send you the leaderboard file.

### Student
1. Type `/start` to register.
2. Submit answers using the format: `TestID*Answers`
   - Example: `12*ABCDE`
3. Receive instant grading results.

## Project Structure
- `bot_handlers/`: Telegram update handlers.
- `db/`: Database schema and query functions.
- `services/`: Logic for grading and file export.
- `scheduler/`: Background jobs for test expiry.
