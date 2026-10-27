import sqlite3
import re
from datetime import datetime
from .config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Anime table
    c.execute("""
    CREATE TABLE IF NOT EXISTS anime (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        title_ru TEXT NOT NULL,
        title_en TEXT DEFAULT '',
        format TEXT DEFAULT 'ТВ-сериал',
        episodes_done INTEGER DEFAULT 0,
        episodes_total INTEGER DEFAULT 0,
        status TEXT DEFAULT 'В процессе',
        cast TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        description TEXT DEFAULT '',
        poster_url TEXT DEFAULT '',
        banner_url TEXT DEFAULT '',
        aliases TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Episodes table
    c.execute("""
    CREATE TABLE IF NOT EXISTS episodes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anime_id INTEGER NOT NULL,
        episode_num TEXT NOT NULL,
        episode_order REAL DEFAULT 0,
        title TEXT DEFAULT '',
        cast_credits TEXT DEFAULT '',
        sub_credits TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        tg_message_id INTEGER,
        tg_post_url TEXT DEFAULT '',
        file_name TEXT DEFAULT '',
        file_size INTEGER DEFAULT 0,
        duration INTEGER DEFAULT 0,
        mime_type TEXT DEFAULT 'video/mp4',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (anime_id) REFERENCES anime (id) ON DELETE CASCADE,
        UNIQUE(anime_id, episode_num)
    );
    """)

    # Sync logs
    c.execute("""
    CREATE TABLE IF NOT EXISTS sync_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER,
        status TEXT,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

def get_all_anime(status_filter=None, search=None):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM anime WHERE 1=1"
    params = []
    
    if status_filter and status_filter != 'Все':
        query += " AND status = ?"
        params.append(status_filter)
        
    if search:
        query += " AND (title_ru LIKE ? OR title_en LIKE ? OR aliases LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s])
        
    query += " ORDER BY status = 'В процессе' DESC, updated_at DESC"
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_anime_by_id(anime_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM anime WHERE id = ?", (anime_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    anime = dict(row)
    c.execute("SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_order ASC, id ASC", (anime_id,))
    anime['episodes'] = [dict(r) for r in c.fetchall()]
    conn.close()
    return anime

def get_episode_by_id(ep_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM episodes WHERE id = ?", (ep_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def get_episode_by_tg_msg(message_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM episodes WHERE tg_message_id = ?", (message_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def update_episode_tg_id(ep_id, tg_message_id, tg_post_url=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE episodes 
    SET tg_message_id = ?, tg_post_url = COALESCE(?, tg_post_url)
    WHERE id = ?
    """, (tg_message_id, tg_post_url, ep_id))
    conn.commit()
    conn.close()

def find_matching_anime(text):
    """
    Tries to match a title from text (e.g. from Telegram caption)
    against existing anime titles and aliases.
    """
    if not text:
        return None
    text_lower = text.lower()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title_ru, title_en, aliases FROM anime")
    candidates = c.fetchall()
    conn.close()
    
    # Priority check: aliases first, then title parts
    for row in candidates:
        anime_id, ru, en, aliases = row['id'], row['title_ru'], row['title_en'], row['aliases'] or ''
        all_keys = [ru.lower()]
        if en:
            all_keys.append(en.lower())
        for a in aliases.split(','):
            a_clean = a.strip().lower()
            if a_clean:
                all_keys.append(a_clean)
                
        for k in all_keys:
            if len(k) >= 3 and k in text_lower:
                return anime_id
    return None

def extract_episode_num(text):
    """
    Extracts episode number from text.
    Examples:
    '1 сезон 5 серия' -> 5
    '23 серия (389)' -> 23
    'Серия 7/52' -> 7
    '1 серия' -> 1
    'Спешл' -> 'Спешл'
    """
    if not text:
        return "1", 1.0
        
    text_clean = text.lower()
    
    # Check for keywords like "фильм" or "спешл"
    if "фильм" in text_clean:
        return "Фильм", 1.0
    if "спешл" in text_clean or "ona" in text_clean:
        return "Спешл", 1.0
        
    # Match pattern: '23 серия' or 'серия 7' or 'серии 1' or 'эп 5' or 'эпизод 5'
    m1 = re.search(r'(\d+)\s*(?:серия|эп|эпизод)', text_clean)
    if m1:
        n = int(m1.group(1))
        return f"{n} серия", float(n)
        
    m2 = re.search(r'сери[яи]\s*(\d+)', text_clean)
    if m2:
        n = int(m2.group(1))
        return f"{n} серия", float(n)
        
    m3 = re.search(r'(\d+)\s*/\s*\d+', text_clean)
    if m3:
        n = int(m3.group(1))
        return f"{n} серия", float(n)
        
    m4 = re.search(r'\b(\d+)\b', text_clean)
    if m4:
        n = int(m4.group(1))
        return f"{n} серия", float(n)
        
    return text.strip(), 1.0

def add_episode_from_tg(anime_id, ep_num_str, ep_order, caption, tg_message_id, tg_post_url, file_name="", file_size=0):
    conn = get_connection()
    c = conn.cursor()
    
    # Check if this episode already exists for this anime
    c.execute("SELECT id FROM episodes WHERE anime_id = ? AND episode_num = ?", (anime_id, ep_num_str))
    existing = c.fetchone()
    
    if existing:
        ep_id = existing['id']
        c.execute("""
        UPDATE episodes 
        SET tg_message_id = ?, tg_post_url = ?, file_name = ?, file_size = ?
        WHERE id = ?
        """, (tg_message_id, tg_post_url, file_name, file_size, ep_id))
    else:
        c.execute("""
        INSERT INTO episodes (anime_id, episode_num, episode_order, title, notes, tg_message_id, tg_post_url, file_name, file_size)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (anime_id, ep_num_str, ep_order, ep_num_str, caption[:200], tg_message_id, tg_post_url, file_name, file_size))
        ep_id = c.lastrowid
        
    # Recalculate anime episodes_done
    c.execute("SELECT COUNT(*) as cnt FROM episodes WHERE anime_id = ?", (anime_id,))
    cnt = c.fetchone()['cnt']
    c.execute("UPDATE anime SET episodes_done = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (cnt, anime_id))
    
    conn.commit()
    conn.close()
    return ep_id
