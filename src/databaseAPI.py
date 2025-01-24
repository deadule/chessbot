import sqlite3
import datetime
import logging
import os
import sys

logger = logging.getLogger(__name__)

sqlite3.register_adapter(datetime.datetime, lambda date: date.isoformat())
sqlite3.register_converter("datetime", lambda date: datetime.datetime.fromisoformat(date.decode()))

class RepChessDB:
    """
    Managing all DB-related stuff.

    NOTE: not thread-safe. But fast.
    """

    def initialize(self):
        db_path = os.getenv("REPCHESS_DB_PATH")

        if not db_path:
            logger.error("Can't find path to database!")
            print("Set the REPCHESS_DB_PATH variable.")
            sys.exit(1)

        # Connect just once during all bot activity.
        # No need to connect() and close() at every transaction,
        # because this file won't run from multiple threads.
        self.conn = sqlite3.connect(db_path)

        with self.conn:
            # TODO: add other tables
            self.conn.executescript(
                """
                BEGIN;

                CREATE TABLE IF NOT EXISTS user (
                    user_id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    name TEXT,
                    surname TEXT,
                    first_contact TEXT,
                    last_contact TEXT,
                    lichess_rating INTEGER,
                    chesscom_rating INTEGER,
                    rep_rating INTEGER
                );

                END;
                """
            )
        logger.info("Database is ready")

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()

    def register_user(
        self,
        telegram_id: int,
        name: str | None = None,
        surname: str | None = None,
        first_contact: datetime.datetime | None = None,
        last_contact: datetime.datetime | None = None,
        lichess_rating: int | None = None,
        chesscom_rating: int | None = None,
        rep_rating: int = 1700,
    ):
        with self.conn:
            self.conn.execute(
                """INSERT INTO user (
                    user_id,
                    telegram_id,
                    name,
                    surname,
                    first_contact,
                    last_contact,
                    lichess_rating,
                    chesscom_rating,
                    rep_rating
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (None,
                 telegram_id,
                 name,
                 surname,
                 first_contact,
                 last_contact,
                 lichess_rating,
                 chesscom_rating,
                 rep_rating)
            )

    def get_user_on_telegram_id(self, telegram_id: int) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE user.telegram_id == ?""", (telegram_id,)
            )
            result = cursor.fetchone()
        return result

rep_chess_db = RepChessDB()
