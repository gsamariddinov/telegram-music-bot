"""
Database layer for Tunova bot — SQLite based.
Tables: users, history, favorites, stats
"""
import sqlite3
import os
import threading

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "tunova.db")

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db() -> None:
    """Create all tables on first run."""
    os.makedirs(DB_DIR, exist_ok=True)
    with _lock:
        con = _conn()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id   INTEGER PRIMARY KEY,
                username  TEXT,
                lang      TEXT NOT NULL DEFAULT 'ru',
                joined_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS history (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                video_id      TEXT    NOT NULL,
                title         TEXT,
                uploader      TEXT,
                duration      INTEGER,
                downloaded_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS favorites (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                video_id TEXT    NOT NULL,
                title    TEXT,
                uploader TEXT,
                duration INTEGER,
                added_at TEXT    NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, video_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS stats (
                video_id       TEXT    PRIMARY KEY,
                title          TEXT,
                uploader       TEXT,
                duration       INTEGER,
                download_count INTEGER NOT NULL DEFAULT 1,
                last_at        TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)
        con.commit()
        con.close()


def ensure_user(user_id: int, username: str = "") -> None:
    with _lock:
        con = _conn()
        con.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username or ""),
        )
        if username:
            con.execute(
                "UPDATE users SET username = ? WHERE user_id = ?",
                (username, user_id),
            )
        con.commit()
        con.close()


def get_lang(user_id: int) -> str:
    with _lock:
        con = _conn()
        row = con.execute(
            "SELECT lang FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        con.close()
    return row[0] if row else "ru"


def set_lang(user_id: int, lang: str) -> None:
    with _lock:
        con = _conn()
        con.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
        con.commit()
        con.close()


def add_history(user_id: int, track: dict) -> None:
    with _lock:
        con = _conn()
        con.execute(
            "DELETE FROM history WHERE user_id = ? AND video_id = ?",
            (user_id, track["id"])
        )
        con.execute(
            "INSERT INTO history (user_id, video_id, title, uploader, duration) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, track["id"], track["title"],
             track.get("uploader", ""), track.get("duration")),
        )
        # Keep only last 10 per user
        con.execute(
            """DELETE FROM history
               WHERE user_id = ? AND id NOT IN (
                   SELECT id FROM history WHERE user_id = ?
                   ORDER BY downloaded_at DESC LIMIT 10
               )""",
            (user_id, user_id),
        )
        con.commit()
        con.close()


def get_history(user_id: int) -> list:
    with _lock:
        con = _conn()
        rows = con.execute(
            """SELECT h.video_id, h.title, h.uploader, h.duration, COALESCE(s.download_count, 1)
               FROM history h
               LEFT JOIN stats s ON h.video_id = s.video_id
               WHERE h.user_id = ?
               ORDER BY h.downloaded_at DESC LIMIT 10""",
            (user_id,),
        ).fetchall()
        con.close()
    return [{"id": r[0], "title": r[1], "uploader": r[2], "duration": r[3], "count": r[4]} for r in rows]


def toggle_favorite(user_id: int, track: dict) -> str:
    """Returns 'added', 'removed', or 'limit'."""
    with _lock:
        con = _conn()
        exists = con.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND video_id = ?",
            (user_id, track["id"]),
        ).fetchone()
        if exists:
            con.execute(
                "DELETE FROM favorites WHERE user_id = ? AND video_id = ?",
                (user_id, track["id"]),
            )
            con.commit()
            con.close()
            return "removed"
        count = con.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        if count >= 20:
            con.close()
            return "limit"
        con.execute(
            "INSERT INTO favorites (user_id, video_id, title, uploader, duration) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, track["id"], track["title"],
             track.get("uploader", ""), track.get("duration")),
        )
        con.commit()
        con.close()
        return "added"


def is_fav(user_id: int, video_id: str) -> bool:
    with _lock:
        con = _conn()
        result = con.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND video_id = ?",
            (user_id, video_id),
        ).fetchone()
        con.close()
    return result is not None


def get_favorites(user_id: int) -> list:
    with _lock:
        con = _conn()
        rows = con.execute(
            """SELECT f.video_id, f.title, f.uploader, f.duration, COALESCE(s.download_count, 1)
               FROM favorites f
               LEFT JOIN stats s ON f.video_id = s.video_id
               WHERE f.user_id = ?
               ORDER BY f.added_at DESC""",
            (user_id,),
        ).fetchall()
        con.close()
    return [{"id": r[0], "title": r[1], "uploader": r[2], "duration": r[3], "count": r[4]} for r in rows]


def update_stats(track: dict) -> None:
    with _lock:
        con = _conn()
        con.execute(
            """INSERT INTO stats (video_id, title, uploader, duration, download_count)
               VALUES (?, ?, ?, ?, 1)
               ON CONFLICT(video_id) DO UPDATE SET
                   download_count = download_count + 1,
                   last_at = datetime('now')""",
            (track["id"], track["title"],
             track.get("uploader", ""), track.get("duration")),
        )
        con.commit()
        con.close()


def get_top(limit: int = 10) -> list:
    with _lock:
        con = _conn()
        rows = con.execute(
            """SELECT video_id, title, uploader, duration, download_count
               FROM stats ORDER BY download_count DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        con.close()
    return [
        {"id": r[0], "title": r[1], "uploader": r[2], "duration": r[3], "count": r[4]}
        for r in rows
    ]
