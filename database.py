import os
import sqlite3
from flask import g, current_app

def get_db():
    """Opens a unique database connection per request context."""
    if 'db' not in g:
        # Puts the DB in the designated Flask instance folder
        db_path = os.path.join(current_app.instance_path, 'codequest.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        # Enforce foreign key constraints inside SQLite explicitly
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(exception=None):
    """Closes the connection seamlessly at the end of a request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Builds clean, structured tables with appropriate constraints."""
    db = get_db()
    
    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        problem_name TEXT NOT NULL,
        platform TEXT NOT NULL,
        difficulty TEXT NOT NULL CHECK(difficulty IN ('Easy', 'Medium', 'Hard')),
        topic TEXT NOT NULL,
        solved_date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS contests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        contest_name TEXT NOT NULL,
        platform TEXT NOT NULL,
        rank INTEGER,
        rating_change INTEGER,
        contest_date TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)
    db.commit()