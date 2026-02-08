import sqlite3
from config import DB_PATH
from datetime import datetime

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- User Queries ---
def upsert_user(tg_user_id, username, full_name, region=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO users (tg_user_id, username, full_name, region)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(tg_user_id) DO UPDATE SET
        username=excluded.username,
        full_name=excluded.full_name,
        region=COALESCE(excluded.region, users.region)
    ''', (tg_user_id, username, full_name, region))
    conn.commit()
    user_id = c.lastrowid
    if not user_id: # On update, lastrowid might not be returned depending on sqlite version/driver, so fetch
        c.execute('SELECT id FROM users WHERE tg_user_id = ?', (tg_user_id,))
        user_id = c.fetchone()['id']
    conn.close()
    return user_id

def get_user_by_tg_id(tg_user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE tg_user_id = ?', (tg_user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT tg_user_id FROM users')
    rows = c.fetchall()
    conn.close()
    return rows

# --- Test Queries ---
def create_test(title, num_questions, duration_hours):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO tests (title, num_questions, duration_hours, status)
        VALUES (?, ?, ?, 'draft')
    ''', (title, num_questions, duration_hours))
    test_id = c.lastrowid
    conn.commit()
    conn.close()
    return test_id

def get_test(test_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tests WHERE id = ?', (test_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_test_answer_key(test_id, answer_key):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE tests SET answer_key = ? WHERE id = ?', (answer_key, test_id))
    conn.commit()
    conn.close()

def start_test_db(test_id, start_at, end_at):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE tests 
        SET status = 'active', start_at = ?, end_at = ?
        WHERE id = ?
    ''', (start_at, end_at, test_id))
    conn.commit()
    conn.close()

def end_test_db(test_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tests SET status = 'ended' WHERE id = ?", (test_id,))
    conn.commit()
    conn.close()

def get_active_tests_needing_end(current_time):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM tests 
        WHERE status = 'active' AND end_at <= ?
    ''', (current_time,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_tests(limit=20):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM tests ORDER BY created_at DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Submission Queries ---
def create_submission(test_id, user_id, raw, normalized, correct, wrong, percent, started_at, time_taken):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO submissions (test_id, user_id, raw_answers, normalized_answers, correct_count, wrong_count, percent, started_at, time_taken_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (test_id, user_id, raw, normalized, correct, wrong, percent, started_at, time_taken))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_submission(test_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM submissions WHERE test_id = ? AND user_id = ?', (test_id, user_id))
    row = c.fetchone()
    conn.close()
    return row

def get_test_submissions(test_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT s.*, u.full_name, u.username 
        FROM submissions s
        JOIN users u ON s.user_id = u.id
        WHERE s.test_id = ?
        ORDER BY s.percent DESC, s.correct_count DESC, s.time_taken_seconds ASC
    ''', (test_id,))
    rows = c.fetchall()
    conn.close()
    return rows
