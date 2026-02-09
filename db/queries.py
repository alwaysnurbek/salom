import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_PATH, DATABASE_URL
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_ph():
    """Returns the placeholder string based on DB type."""
    return '%s' if DATABASE_URL else '?'

# --- User Queries ---
def upsert_user(tg_user_id, username, full_name, region=None):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    
    sql = f'''
        INSERT INTO users (tg_user_id, username, full_name, region)
        VALUES ({ph}, {ph}, {ph}, {ph})
        ON CONFLICT(tg_user_id) DO UPDATE SET
        username=excluded.username,
        full_name=excluded.full_name,
        region=COALESCE(excluded.region, users.region)
    '''
    
    try:
        if DATABASE_URL:
            sql += " RETURNING id"
            c.execute(sql, (tg_user_id, username, full_name, region))
            user_id = c.fetchone()['id']
        else:
            c.execute(sql, (tg_user_id, username, full_name, region))
            user_id = c.lastrowid
            if not user_id:
                c.execute(f'SELECT id FROM users WHERE tg_user_id = {ph}', (tg_user_id,))
                res = c.fetchone()
                user_id = res['id'] if res else None
        conn.commit()
    finally:
        conn.close()
    return user_id

def get_user_by_tg_id(tg_user_id):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'SELECT * FROM users WHERE tg_user_id = {ph}', (tg_user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_all_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users") # sqlite3.Row / RealDictCursor access by key 'tg_user_id' if needed, but here we perform broadcast
    rows = cursor.fetchall()
    conn.close()
    # Return rows as dicts to be safe or list of dicts
    # In original code it returned IDs? no, send_broadcast iterated rows.
    # Original: return [row['id'] for row in rows] -> Actually send_broadcast used:
    # row['tg_user_id']
    # Wait, original get_all_users returned list of IDs?
    # Let's check send_broadcast usage.
    # send_broadcast(update...) calls db.get_all_users()
    # It iterates 'users'.
    # Previous implementation: return [row['id'] for row in rows]
    # Wait, send_broadcast used: users = db.get_all_users(); for row in users: user_id = row['tg_user_id']
    # If get_all_users returned list of IDs, then row['tg_user_id'] would fail.
    # Checking previous code... 
    # Previous code: return [row['id'] for row in rows]
    # But send_broadcast: users = db.get_all_users() ... for row in users: user_id = row['tg_user_id']
    # This implies the previous code was BROKEN or I misread it.
    # Let's look at previous file content in Step 280.
    # 44:    return [row['id'] for row in rows]
    # 333:   users = db.get_all_users()
    # 340:   for row in users:
    # 341:       user_id = row['tg_user_id']
    # This confirms the previous code was indeed buggy (integers don't have subscripts).
    # Since I am rewriting it, I will fix it to return the full rows or at least tg_user_id.
    
    # Correction: I will return list of dicts/Rows with tg_user_id.
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tg_user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_user_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    # psycopg2 RealDictCursor fetchone returns dict {'count': N} ?? No, COUNT(*) name is unpredictable unless aliased?
    # Actually RealDictCursor preserves column names. COUNT(*) might be 'count'.
    # sqlite3 fetchone()[0] works.
    # To be safe, use alias.
    if DATABASE_URL:
        # Postgres RealDictCursor
        cursor.execute("SELECT COUNT(*) as c FROM users")
        res = cursor.fetchone()
        count = res['c']
    else:
        # SQLite
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
    conn.close()
    return count

# --- Test Queries ---
def create_test(title, num_questions, duration_hours):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    
    sql = f'''
        INSERT INTO tests (title, num_questions, duration_hours, status)
        VALUES ({ph}, {ph}, {ph}, 'draft')
    '''
    
    if DATABASE_URL:
        sql += " RETURNING id"
        c.execute(sql, (title, num_questions, duration_hours))
        test_id = c.fetchone()['id']
    else:
        c.execute(sql, (title, num_questions, duration_hours))
        test_id = c.lastrowid
        
    conn.commit()
    conn.close()
    return test_id

def get_test(test_id):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'SELECT * FROM tests WHERE id = {ph}', (test_id,))
    row = c.fetchone()
    conn.close()
    return row

def update_test_answer_key(test_id, answer_key):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'UPDATE tests SET answer_key = {ph} WHERE id = {ph}', (answer_key, test_id))
    conn.commit()
    conn.close()

def start_test_db(test_id, start_at, end_at):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'''
        UPDATE tests 
        SET status = 'active', start_at = {ph}, end_at = {ph}
        WHERE id = {ph}
    ''', (start_at, end_at, test_id))
    conn.commit()
    conn.close()

def end_test_db(test_id):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f"UPDATE tests SET status = 'ended' WHERE id = {ph}", (test_id,))
    conn.commit()
    conn.close()

def get_active_tests_needing_end(current_time):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'''
        SELECT * FROM tests 
        WHERE status = 'active' AND end_at <= {ph}
    ''', (current_time,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_all_tests(limit=20):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'SELECT * FROM tests ORDER BY created_at DESC LIMIT {ph}', (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

# --- Submission Queries ---
def create_submission(test_id, user_id, raw, normalized, correct, wrong, percent, started_at, time_taken):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    
    try:
        c.execute(f'''
            INSERT INTO submissions (test_id, user_id, raw_answers, normalized_answers, correct_count, wrong_count, percent, started_at, time_taken_seconds)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        ''', (test_id, user_id, raw, normalized, correct, wrong, percent, started_at, time_taken))
        conn.commit()
        return True
    except (sqlite3.IntegrityError, psycopg2.IntegrityError):
        return False
    except Exception as e:
        logger.error(f"Error creating submission: {e}")
        return False
    finally:
        conn.close()

def get_submission(test_id, user_id):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'SELECT * FROM submissions WHERE test_id = {ph} AND user_id = {ph}', (test_id, user_id))
    row = c.fetchone()
    conn.close()
    return row

def get_test_submissions(test_id):
    conn = get_connection()
    c = conn.cursor()
    ph = get_ph()
    c.execute(f'''
        SELECT s.*, u.full_name, u.username 
        FROM submissions s
        JOIN users u ON s.user_id = u.id
        WHERE s.test_id = {ph}
        ORDER BY s.percent DESC, s.correct_count DESC, s.time_taken_seconds ASC
    ''', (test_id,))
    rows = c.fetchall()
    conn.close()
    return rows
