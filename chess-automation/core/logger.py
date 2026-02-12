# import sqlite3
# from datetime import datetime


# class ChessLogger:
#     def __init__(self, db_name="chess_bot.db"):
#         self.db_name = db_name
#         self.init_db()

#     def init_db(self):
#         """Creates the database and table if they don't exist."""
#         conn = sqlite3.connect(self.db_name)
#         cursor = conn.cursor()
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS game_logs (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 timestamp DATETIME,
#                 game_number INTEGER,
#                 turn_number INTEGER,
#                 side TEXT,
#                 fen TEXT,
#                 move_made TEXT,
#                 event_type TEXT,
#                 message TEXT
#             )
#         """)
#         conn.commit()
#         conn.close()

#     def log(
#         self,
#         game_num=0,
#         turn_num=0,
#         side="unknown",
#         fen="unknown",
#         move="unknown",
#         event="INFO",
#         message="unknown",
#     ):
#         """Inserts a new log entry into the database."""
#         try:
#             conn = sqlite3.connect(self.db_name)
#             cursor = conn.cursor()
#             cursor.execute(
#                 """
#                 INSERT INTO game_logs
#                 (timestamp, game_number, turn_number, side, fen, move_made, event_type, message)
#                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#             """,
#                 (datetime.now(), game_num, turn_num, side, fen, move, event, message),
#             )
#             conn.commit()
#             conn.close()
#         except Exception as e:
#             print(f"[DB ERROR] Could not write to SQLite: {e}")


import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class ChessLogger:
    def __init__(self):
        self.host = os.getenv("RDS_HOST")
        self.port = int(os.getenv("RDS_PORT", "5432"))
        self.dbname = os.getenv("RDS_DBNAME")
        self.user = os.getenv("RDS_USER")
        self.password = os.getenv("RDS_PASSWORD")

        if not all([self.host, self.user, self.password, self.dbname]):
            raise ValueError("Missing RDS env vars. Check .env file.")

        self.init_db()

    def get_conn(self):
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname,
        )

    def init_db(self):
        conn = None
        try:
            conn = self.get_conn()
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS game_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP NOT NULL,
                    game_number INTEGER,
                    turn_number INTEGER,
                    side TEXT,
                    fen TEXT,
                    move_made TEXT,
                    event_type TEXT,
                    message TEXT
                );
            """)

            conn.commit()
            cur.close()

        except Exception as e:
            print(f"[DB ERROR] Could not init Postgres table: {e}")

        finally:
            if conn:
                conn.close()

    def log(
        self,
        game_num=None,
        turn_num=None,
        side=None,
        fen=None,
        move=None,
        event="INFO",
        message=None,
    ):
        conn = None
        try:
            conn = self.get_conn()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO game_logs
                (timestamp, game_number, turn_number, side, fen, move_made, event_type, message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (datetime.now(), game_num, turn_num, side, fen, move, event, message),
            )

            conn.commit()
            cur.close()

        except Exception as e:
            print(f"[DB ERROR] Could not write to Postgres: {e}")

        finally:
            if conn:
                conn.close()
