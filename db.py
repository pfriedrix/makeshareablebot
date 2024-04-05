import sqlite3
import json

def init_db():
    conn = sqlite3.connect('db.sqlite')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            telegram_id BIGINT PRIMARY KEY,
            spotify_token JSON
        )
    ''')
    conn.commit()
    conn.close()
    
def insert_or_update_spotify_token(telegram_id, spotify_token_dict):
    conn = sqlite3.connect('db.sqlite')
    cur = conn.cursor()
    
    spotify_token_json = json.dumps(spotify_token_dict)
    
    cur.execute('''
    INSERT INTO users (telegram_id, spotify_token)
    VALUES (?, ?)
    ON CONFLICT(telegram_id) DO UPDATE SET spotify_token = excluded.spotify_token
    ''', (telegram_id, spotify_token_json))
    
    conn.commit()
    conn.close()

def get_spotify_token_from_db(telegram_id):
    conn = sqlite3.connect('db.sqlite')
    cur = conn.cursor()
    
    cur.execute('SELECT spotify_token FROM users WHERE telegram_id = ?', (telegram_id,))
    result = cur.fetchone()
    
    conn.close()
    
    if result:
        return json.loads(result[0])
    else:
        return None
    
def remove_spotify_token(telegram_id):
    conn = sqlite3.connect('db.sqlite')
    cur = conn.cursor()
    
    cur.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
    
    conn.commit()
    conn.close()