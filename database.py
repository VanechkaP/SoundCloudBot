import sqlite3

DB_NAME = "bot_music.db"


def init_db():
    """Создает таблицы в базе данных, если их еще нет"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')

    # Таблица плейлистов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS playlists (
            playlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    ''')

    # Таблица треков в плейлистах
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracks (
            track_id INTEGER PRIMARY KEY AUTOINCREMENT,
            playlist_id INTEGER,
            title TEXT NOT NULL,
            artist TEXT,
            url TEXT NOT NULL,
            FOREIGN KEY (playlist_id) REFERENCES playlists(playlist_id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()


# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ПЛЕЙЛИСТАМИ ---

def add_user(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()


def create_playlist(user_id: int, name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()


def get_user_playlists(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT playlist_id, name FROM playlists WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows  # Возвращает список кортежей [(id, name), ...]


def add_track_to_playlist(playlist_id: int, title: str, artist: str, url: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tracks (playlist_id, title, artist, url) VALUES (?, ?, ?, ?)",
        (playlist_id, title, artist, url)
    )
    conn.commit()
    conn.close()


def get_playlist_tracks(playlist_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title, artist, url FROM tracks WHERE playlist_id = ?", (playlist_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows