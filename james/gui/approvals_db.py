import sqlite3
import datetime

class ApprovalsDB:
    def __init__(self, db_path="approvals.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT,
                    timestamp TEXT,
                    approved INTEGER
                )
            ''')
            conn.commit()

    def log_approval(self, action: str, approved: bool):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            timestamp = datetime.datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO approvals (action, timestamp, approved) VALUES (?, ?, ?)",
                (action, timestamp, int(approved))
            )
            conn.commit()
