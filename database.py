import sqlite3
import datetime
from config import DB_NAME

def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # Foydalanuvchilar
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id          INTEGER PRIMARY KEY,
        full_name   TEXT,
        username    TEXT,
        lang        TEXT DEFAULT 'uz',
        is_admin    INTEGER DEFAULT 0,
        is_banned   INTEGER DEFAULT 0,
        vip_until   TEXT,
        views       INTEGER DEFAULT 0,
        joined_at   TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Adminlar
    c.execute("""CREATE TABLE IF NOT EXISTS admins (
        user_id     INTEGER PRIMARY KEY,
        added_by    INTEGER,
        added_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Majburiy obuna kanallari
    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id  TEXT NOT NULL,
        channel_name TEXT,
        channel_url TEXT,
        sub_type    TEXT DEFAULT 'public',
        min_members INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        added_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Qo'shimcha kanallar (post tashlash uchun)
    c.execute("""CREATE TABLE IF NOT EXISTS extra_channels (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id   TEXT NOT NULL,
        channel_name TEXT,
        is_active    INTEGER DEFAULT 1,
        added_at     TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Postlar tarixi
    c.execute("""CREATE TABLE IF NOT EXISTS posts (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id     INTEGER,
        message_text TEXT,
        extra_links  TEXT,
        sent_to      TEXT,
        sent_at      TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Kinolar
    c.execute("""CREATE TABLE IF NOT EXISTS movies (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        title_ru    TEXT,
        category    TEXT NOT NULL,
        year        INTEGER,
        country     TEXT,
        genre       TEXT,
        rating      REAL DEFAULT 0,
        description TEXT,
        desc_ru     TEXT,
        poster_id   TEXT,
        is_vip      INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        views       INTEGER DEFAULT 0,
        added_by    INTEGER,
        added_at    TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Fasllar (Serial/Anime uchun)
    c.execute("""CREATE TABLE IF NOT EXISTS seasons (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id    INTEGER NOT NULL,
        season_num  INTEGER NOT NULL,
        title       TEXT,
        FOREIGN KEY (movie_id) REFERENCES movies(id)
    )""")

    # Qismlar (episodes)
    c.execute("""CREATE TABLE IF NOT EXISTS episodes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id    INTEGER NOT NULL,
        season_id   INTEGER,
        episode_num INTEGER,
        ep_type     TEXT DEFAULT 'episode',
        file_id     TEXT NOT NULL,
        title       TEXT,
        duration    TEXT,
        FOREIGN KEY (movie_id) REFERENCES movies(id),
        FOREIGN KEY (season_id) REFERENCES seasons(id)
    )""")

    # Ko'rishlar tarixi
    c.execute("""CREATE TABLE IF NOT EXISTS views (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        movie_id    INTEGER,
        viewed_at   TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # Sevimlilar
    c.execute("""CREATE TABLE IF NOT EXISTS favorites (
        user_id     INTEGER,
        movie_id    INTEGER,
        added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    )""")

    # Keyinroq ko'raman
    c.execute("""CREATE TABLE IF NOT EXISTS watch_later (
        user_id     INTEGER,
        movie_id    INTEGER,
        added_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    )""")

    # Baholar
    c.execute("""CREATE TABLE IF NOT EXISTS ratings (
        user_id     INTEGER,
        movie_id    INTEGER,
        rating      INTEGER,
        rated_at    TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, movie_id)
    )""")

    # Bot sozlamalari
    c.execute("""CREATE TABLE IF NOT EXISTS settings (
        key         TEXT PRIMARY KEY,
        value       TEXT
    )""")

    # Default sozlamalar
    defaults = [
        ("forward_enabled", "1"),
        ("bot_active", "1"),
    ]
    for key, val in defaults:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, val))

    conn.commit()
    conn.close()
    print("✅ Database tayyor!")

# =====================
# FOYDALANUVCHI
# =====================

def get_user(user_id):
    conn = get_conn()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return user

def add_user(user_id, full_name, username):
    conn = get_conn()
    conn.execute("""INSERT OR IGNORE INTO users (id, full_name, username)
                    VALUES (?, ?, ?)""", (user_id, full_name, username))
    conn.execute("""UPDATE users SET full_name=?, username=?
                    WHERE id=?""", (full_name, username, user_id))
    conn.commit()
    conn.close()

def get_user_lang(user_id):
    conn = get_conn()
    row = conn.execute("SELECT lang FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["lang"] if row else "uz"

def set_user_lang(user_id, lang):
    conn = get_conn()
    conn.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_conn()
    users = conn.execute("SELECT id FROM users WHERE is_banned=0").fetchall()
    conn.close()
    return [u["id"] for u in users]

def count_users():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    conn.close()
    return n

# =====================
# ADMIN
# =====================

def is_admin(user_id):
    conn = get_conn()
    row = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["is_admin"])

def add_admin(user_id, added_by):
    conn = get_conn()
    conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (user_id,))
    conn.execute("INSERT OR IGNORE INTO admins (user_id, added_by) VALUES (?,?)", (user_id, added_by))
    conn.commit()
    conn.close()

def remove_admin(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET is_admin=0 WHERE id=?", (user_id,))
    conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_admins():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM admins").fetchall()
    conn.close()
    return rows

# =====================
# MAJBURIY OBUNA
# =====================

def add_subscription(channel_id, channel_name, channel_url, sub_type, min_members=0):
    conn = get_conn()
    conn.execute("""INSERT INTO subscriptions
                    (channel_id, channel_name, channel_url, sub_type, min_members)
                    VALUES (?,?,?,?,?)""",
                 (channel_id, channel_name, channel_url, sub_type, min_members))
    conn.commit()
    conn.close()

def remove_subscription(sub_id):
    conn = get_conn()
    conn.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
    conn.commit()
    conn.close()

def get_subscriptions():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM subscriptions WHERE is_active=1").fetchall()
    conn.close()
    return rows

# =====================
# KINO
# =====================

def add_movie(data):
    conn = get_conn()
    cur = conn.execute("""INSERT INTO movies
        (title, title_ru, category, year, country, genre, description, desc_ru, poster_id, is_vip, added_by)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (data["title"], data.get("title_ru"), data["category"],
         data.get("year"), data.get("country"), data.get("genre"),
         data.get("description"), data.get("desc_ru"),
         data.get("poster_id"), data.get("is_vip", 0), data.get("added_by")))
    movie_id = cur.lastrowid
    conn.commit()
    conn.close()
    return movie_id

def get_movie(movie_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM movies WHERE id=? AND is_active=1", (movie_id,)).fetchone()
    conn.close()
    return row

def delete_movie(movie_id):
    conn = get_conn()
    conn.execute("UPDATE movies SET is_active=0 WHERE id=?", (movie_id,))
    conn.commit()
    conn.close()

def get_movies_by_category(category, limit=10, offset=0):
    conn = get_conn()
    rows = conn.execute("""SELECT * FROM movies WHERE category=? AND is_active=1
                           ORDER BY id DESC LIMIT ? OFFSET ?""",
                        (category, limit, offset)).fetchall()
    conn.close()
    return rows

def search_movies(query):
    conn = get_conn()
    rows = conn.execute("""SELECT * FROM movies WHERE is_active=1 AND
                           (title LIKE ? OR title_ru LIKE ? OR id=?)
                           LIMIT 20""",
                        (f"%{query}%", f"%{query}%", query if query.isdigit() else -1)).fetchall()
    conn.close()
    return rows

def get_random_movie(category=None):
    conn = get_conn()
    if category:
        row = conn.execute("""SELECT * FROM movies WHERE category=? AND is_active=1
                              ORDER BY RANDOM() LIMIT 1""", (category,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM movies WHERE is_active=1 ORDER BY RANDOM() LIMIT 1").fetchone()
    conn.close()
    return row

def add_view(user_id, movie_id):
    conn = get_conn()
    conn.execute("INSERT INTO views (user_id, movie_id) VALUES (?,?)", (user_id, movie_id))
    conn.execute("UPDATE movies SET views=views+1 WHERE id=?", (movie_id,))
    conn.execute("UPDATE users SET views=views+1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

# =====================
# FASLLAR VA QISMLAR
# =====================

def add_season(movie_id, season_num, title=None):
    conn = get_conn()
    cur = conn.execute("INSERT INTO seasons (movie_id, season_num, title) VALUES (?,?,?)",
                       (movie_id, season_num, title))
    season_id = cur.lastrowid
    conn.commit()
    conn.close()
    return season_id

def get_seasons(movie_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM seasons WHERE movie_id=? ORDER BY season_num", (movie_id,)).fetchall()
    conn.close()
    return rows

def add_episode(movie_id, file_id, season_id=None, episode_num=None, ep_type="episode", title=None):
    conn = get_conn()
    conn.execute("""INSERT INTO episodes (movie_id, season_id, episode_num, ep_type, file_id, title)
                    VALUES (?,?,?,?,?,?)""",
                 (movie_id, season_id, episode_num, ep_type, file_id, title))
    conn.commit()
    conn.close()

def get_episodes(movie_id, season_id=None):
    conn = get_conn()
    if season_id:
        rows = conn.execute("""SELECT * FROM episodes WHERE movie_id=? AND season_id=?
                               ORDER BY episode_num""", (movie_id, season_id)).fetchall()
    else:
        rows = conn.execute("""SELECT * FROM episodes WHERE movie_id=?
                               ORDER BY episode_num""", (movie_id,)).fetchall()
    conn.close()
    return rows

def delete_episodes(movie_id):
    conn = get_conn()
    conn.execute("DELETE FROM episodes WHERE movie_id=?", (movie_id,))
    conn.execute("DELETE FROM seasons WHERE movie_id=?", (movie_id,))
    conn.commit()
    conn.close()

# =====================
# SEVIMLILAR & KEYINROQ
# =====================

def toggle_favorite(user_id, movie_id):
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM favorites WHERE user_id=? AND movie_id=?",
                          (user_id, movie_id)).fetchone()
    if exists:
        conn.execute("DELETE FROM favorites WHERE user_id=? AND movie_id=?", (user_id, movie_id))
        added = False
    else:
        conn.execute("INSERT INTO favorites (user_id, movie_id) VALUES (?,?)", (user_id, movie_id))
        added = True
    conn.commit()
    conn.close()
    return added

def get_favorites(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT m.* FROM movies m
                           JOIN favorites f ON m.id=f.movie_id
                           WHERE f.user_id=? AND m.is_active=1
                           ORDER BY f.added_at DESC""", (user_id,)).fetchall()
    conn.close()
    return rows

def toggle_watch_later(user_id, movie_id):
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM watch_later WHERE user_id=? AND movie_id=?",
                          (user_id, movie_id)).fetchone()
    if exists:
        conn.execute("DELETE FROM watch_later WHERE user_id=? AND movie_id=?", (user_id, movie_id))
        added = False
    else:
        conn.execute("INSERT INTO watch_later (user_id, movie_id) VALUES (?,?)", (user_id, movie_id))
        added = True
    conn.commit()
    conn.close()
    return added

def get_watch_later(user_id):
    conn = get_conn()
    rows = conn.execute("""SELECT m.* FROM movies m
                           JOIN watch_later w ON m.id=w.movie_id
                           WHERE w.user_id=? AND m.is_active=1
                           ORDER BY w.added_at DESC""", (user_id,)).fetchall()
    conn.close()
    return rows

# =====================
# BAHO
# =====================

def set_rating(user_id, movie_id, rating):
    conn = get_conn()
    conn.execute("""INSERT OR REPLACE INTO ratings (user_id, movie_id, rating)
                    VALUES (?,?,?)""", (user_id, movie_id, rating))
    avg = conn.execute("SELECT AVG(rating) as a FROM ratings WHERE movie_id=?",
                       (movie_id,)).fetchone()["a"]
    conn.execute("UPDATE movies SET rating=? WHERE id=?", (round(avg, 1), movie_id))
    conn.commit()
    conn.close()

# =====================
# VIP
# =====================

def is_vip(user_id):
    conn = get_conn()
    row = conn.execute("SELECT vip_until FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if not row or not row["vip_until"]:
        return False
    return datetime.datetime.strptime(row["vip_until"], "%Y-%m-%d") >= datetime.datetime.now()

def set_vip(user_id, days):
    now = datetime.datetime.now()
    until = (now + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_conn()
    conn.execute("UPDATE users SET vip_until=? WHERE id=?", (until, user_id))
    conn.commit()
    conn.close()
    return until

# =====================
# STATISTIKA
# =====================

def get_stats():
    conn = get_conn()
    today = datetime.date.today().isoformat()
    stats = {
        "users":       conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"],
        "movies":      conn.execute("SELECT COUNT(*) as c FROM movies WHERE category='movie' AND is_active=1").fetchone()["c"],
        "serials":     conn.execute("SELECT COUNT(*) as c FROM movies WHERE category='serial' AND is_active=1").fetchone()["c"],
        "anime":       conn.execute("SELECT COUNT(*) as c FROM movies WHERE category='anime' AND is_active=1").fetchone()["c"],
        "dramas":      conn.execute("SELECT COUNT(*) as c FROM movies WHERE category='drama' AND is_active=1").fetchone()["c"],
        "cartoons":    conn.execute("SELECT COUNT(*) as c FROM movies WHERE category='cartoon' AND is_active=1").fetchone()["c"],
        "today_views": conn.execute("SELECT COUNT(*) as c FROM views WHERE viewed_at LIKE ?", (f"{today}%",)).fetchone()["c"],
        "total_views": conn.execute("SELECT COUNT(*) as c FROM views").fetchone()["c"],
    }
    conn.close()
    return stats

# =====================
# SOZLAMALAR
# =====================

def get_setting(key):
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None

def set_setting(key, value):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()

# =====================
# QO'SHIMCHA KANALLAR
# =====================

def add_extra_channel(channel_id, channel_name):
    conn = get_conn()
    conn.execute("INSERT INTO extra_channels (channel_id, channel_name) VALUES (?,?)",
                 (channel_id, channel_name))
    conn.commit()
    conn.close()

def remove_extra_channel(ch_id):
    conn = get_conn()
    conn.execute("DELETE FROM extra_channels WHERE id=?", (ch_id,))
    conn.commit()
    conn.close()

def get_extra_channels():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM extra_channels WHERE is_active=1").fetchall()
    conn.close()
    return rows

def save_post(admin_id, message_text, extra_links, sent_to):
    conn = get_conn()
    conn.execute("""INSERT INTO posts (admin_id, message_text, extra_links, sent_to)
                    VALUES (?,?,?,?)""",
                 (admin_id, message_text, extra_links, sent_to))
    conn.commit()
    conn.close()

