import sqlite3
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id INTEGER UNIQUE NOT NULL,
        username TEXT,
        full_name TEXT,
        region TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tests table
    c.execute('''
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        num_questions INTEGER NOT NULL,
        duration_hours INTEGER NOT NULL,
        answer_key TEXT,
        start_at TIMESTAMP,
        end_at TIMESTAMP,
        status TEXT DEFAULT 'draft', -- draft, active, ended
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Submissions table
    c.execute('''
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        raw_answers TEXT,
        normalized_answers TEXT,
        correct_count INTEGER,
        wrong_count INTEGER,
        percent REAL,
        started_at TIMESTAMP,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        time_taken_seconds INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(test_id) REFERENCES tests(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(test_id, user_id)
    )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

if __name__ == "__main__":
    init_db()
