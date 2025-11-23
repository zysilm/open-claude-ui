"""Add title_auto_generated column to chat_sessions table."""

import sqlite3
import os

def migrate():
    """Add title_auto_generated column to chat_sessions table."""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'open_codex.db')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add the new column with default value 'N'
        cursor.execute("""
            ALTER TABLE chat_sessions
            ADD COLUMN title_auto_generated VARCHAR(1) DEFAULT 'N' NOT NULL
        """)

        conn.commit()
        print("✓ Successfully added title_auto_generated column to chat_sessions table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Column title_auto_generated already exists")
        else:
            raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
