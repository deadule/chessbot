import sqlite3
import datetime
import logging
import os
import sys
from collections import deque

logger = logging.getLogger(__name__)
logfile_dir = os.getenv("REPCHESS_LOG_DIR")
logger_handler = logging.FileHandler(os.path.join(logfile_dir, "database.log"))
logger_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s : %(levelname)s: %(message)s"))
logger.addHandler(logger_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False


def converter_to_isoformat(date_time_b: bytes):
    try:
        date_time = datetime.datetime.fromisoformat(date_time_b.decode("utf-8"))
    except ValueError:
        return date_time_b
    return date_time


sqlite3.register_converter("datetime", converter_to_isoformat)
sqlite3.register_adapter(datetime.datetime, lambda date: date.isoformat())

sqlite3.register_converter("BOOL", lambda v: bool(int(v)))
sqlite3.register_adapter(bool, int)


# TODO: maybe rewrite it with sqlalchemy or somehow else...
class RepChessDB:
    """
    Managing all DB-related stuff.

    NOTE: not thread-safe. But fast.
    """

    # Assume that all players amount is less then 1 million.
    MAX_PUBLIC_ID = 1000000

    # We need this variable to optimize searching public id for new player.
    FREE_PUBLIC_IDS = deque(maxlen=100000)

    def initialize(self):
        db_path = os.getenv("REPCHESS_DB_PATH")

        if not db_path:
            logger.error("Can't find path to database!")
            print("Set the REPCHESS_DB_PATH variable.")
            sys.exit(1)

        # Connect just once during all bot activity.
        # No need to connect() and close() at every transaction,
        # because this file won't run from multiple threads.
        self.conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row

        with self.conn:
            # TODO: add other tables
            self.conn.executescript(
                """
                BEGIN;

                CREATE TABLE IF NOT EXISTS city (
                    city_id INTEGER PRIMARY KEY,
                    name TEXT,
                    tg_channel TEXT UNIQUE,
                    timetable_message_id TEXT,
                    timetable_photo TEXT
                );

                CREATE TABLE IF NOT EXISTS user (
                    user_id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    public_id INTEGER UNIQUE NOT NULL,
                    is_admin BOOL,
                    name TEXT,
                    surname TEXT,
                    nickname TEXT,
                    city_id INTEGER,
                    first_contact datetime,
                    last_contact datetime,
                    lichess_rating INTEGER,
                    chesscom_rating INTEGER,
                    rep_rating INTEGER,
                    games_played INTEGER,
                    age INTEGER,
                    FOREIGN KEY (city_id) REFERENCES city (city_id)
                );

                CREATE TABLE IF NOT EXISTS tournament (
                    tournament_id INTEGER PRIMARY KEY,
                    tg_channel TEXT,
                    message_id INTEGER,
                    city_id INTEGER,
                    summary TEXT,
                    date_time datetime,
                    address TEXT,
                    registration BOOL,
                    results_uploaded BOOL,
                    FOREIGN KEY (city_id) REFERENCES city (city_id)
                );

                CREATE TABLE IF NOT EXISTS user_on_tournament (
                    user_on_tournament_id INTEGER PRIMARY KEY,
                    tournament_id INTEGER,
                    user_id INTEGER,
                    nickname TEXT,
                    rating_before INTEGER,
                    rating_after INTEGER,
                    place INTEGER,
                    score REAL,
                    k_factor INTEGER,
                    FOREIGN KEY (tournament_id) REFERENCES tournament (tournament_id),
                    FOREIGN KEY (user_id) REFERENCES user (public_id)
                );

                CREATE TABLE IF NOT EXISTS game (
                    game_id INTEGER PRIMARY KEY,
                    tournament_id INTEGER NOT NULL,
                    white_user_id INTEGER NOT NULL,
                    black_user_id INTEGER NOT NULL,
                    round INTEGER,
                    desk_number INTEGER,
                    result REAL,
                    white_rating_change INTEGER,
                    black_rating_change INTEGER,
                    FOREIGN KEY (tournament_id) REFERENCES tournament (tournament_id),
                    FOREIGN KEY (white_user_id) REFERENCES user (user_id),
                    FOREIGN KEY (black_user_id) REFERENCES user (user_id)
                );

                END;
                """
            )

        with self.conn:
            cursor = self.conn.execute("""SELECT public_id FROM user""")
        all_ids = cursor.fetchall()

        if all_ids:
            occupied_ids = {public_id[0] for public_id in all_ids}
        else:
            occupied_ids = {}

        # First 100 ids is for special use.
        for i in range(101, 1000000):
            if i % 1000 == 0 and len(self.FREE_PUBLIC_IDS) > 90000:
                break
            if i not in occupied_ids:
                self.FREE_PUBLIC_IDS.appendleft(i)

        logger.info("Database is ready")

    def __del__(self):
        if hasattr(self, "conn"):
            self.conn.close()

    # USER =========================================================

    def register_user(
        self,
        telegram_id: int,
        public_id: int | None = None,
        is_admin: bool = False,
        name: str | None = None,
        surname: str | None = None,
        nickname: str | None = None,
        city_id: int | None = None,
        first_contact: datetime.datetime | None = None,
        last_contact: datetime.datetime | None = None,
        lichess_rating: int | None = None,
        chesscom_rating: int | None = None,
        rep_rating: int = 1600,
        games_played: int = 0,
        age: int | None = None
    ):
        """
        Register user if user with given telegram_id doesn't exist.
        """
        if not public_id:
            public_id = self.FREE_PUBLIC_IDS.pop()

        with self.conn:
            self.conn.execute(
                """INSERT OR IGNORE INTO user (
                    user_id,
                    telegram_id,
                    public_id,
                    is_admin,
                    name,
                    surname,
                    nickname,
                    city_id,
                    first_contact,
                    last_contact,
                    lichess_rating,
                    chesscom_rating,
                    rep_rating,
                    games_played,
                    age
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (None,
                 telegram_id,
                 public_id,
                 is_admin,
                 name,
                 surname,
                 nickname,
                 city_id,
                 first_contact if first_contact else datetime.datetime.now(),
                 last_contact,
                 lichess_rating,
                 chesscom_rating,
                 rep_rating,
                 games_played,
                 age)
            )
        logger.debug(f"register user {telegram_id}, {public_id}, {is_admin}, {name}, {surname}, {nickname}, {city_id}, {first_contact}, {last_contact}, {lichess_rating}, {chesscom_rating}, {rep_rating} {age}")

    def update_user_public_id(self, old_public_id: int, public_id: int) -> bool:
        """
        Return False if public_id is already occupied.
        Return None if user with old_public_id is not present.
        Otherwise return True.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT public_id FROM user WHERE public_id = ?""",
                (public_id,)
            )
        if cursor.fetchone():
            return False

        with self.conn:
            cursor = self.conn.execute(
                """SELECT public_id FROM user WHERE public_id = ?""",
                (old_public_id,)
            )
        if not cursor.fetchone():
            return

        with self.conn:
            self.conn.execute(
                """UPDATE user SET public_id = ? WHERE public_id = ?""",
                (public_id, old_public_id)
            )
        logger.debug(f"update user public id from {old_public_id} to {public_id}")
        self.FREE_PUBLIC_IDS.append(old_public_id)
        try:
            self.FREE_PUBLIC_IDS.remove(public_id)
        except ValueError:
            pass
        return True

    def update_user_name(self, telegram_id: int, name: str):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET name = ?, last_contact = ? WHERE telegram_id = ?""",
                (name, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update user name {telegram_id=}, {name=}")

    def update_user_surname(self, telegram_id: int, surname: str):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET surname = ?, last_contact = ? WHERE telegram_id = ?""",
                (surname, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update user surname {telegram_id=}, {surname=}")

    def update_user_nickname(self, telegram_id: int, nickname: str):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET nickname = ?, last_contact = ? WHERE telegram_id = ?""",
                (nickname, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update user nickname {telegram_id=}, {nickname=}")

    def update_user_lichess_rating(self, telegram_id: int, lichess_rating: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET lichess_rating = ?, last_contact = ? WHERE telegram_id = ?""",
                (lichess_rating, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update lichess rating {telegram_id=}, {lichess_rating=}")

    def update_user_chesscom_rating(self, telegram_id: int, chesscom_rating: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET chesscom_rating = ?, last_contact = ? WHERE telegram_id = ?""",
                (chesscom_rating, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update chesscom_rating {telegram_id=}, {chesscom_rating=}")

    def update_user_rep_rating_with_rep_id(self, public_id: int, rep_rating: int):
        with self.conn:
            cursor = self.conn.execute(
                """UPDATE user SET rep_rating = ?, last_contact = ? WHERE public_id = ?""",
                (rep_rating, datetime.datetime.now(), public_id)
            )
        if cursor.rowcount == 0:
            raise ValueError(f"User with public_id {public_id} not found in the database")
        logger.debug(f"update rep rating {public_id=}, {rep_rating=}")
    
    def update_user_rep_rating_with_user_id(self, user_id: int, rep_rating: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET rep_rating = ?, last_contact = ? WHERE user_id = ?""",
                (rep_rating, datetime.datetime.now(), user_id)
            )
        logger.debug(f"update rep rating {user_id=}, {rep_rating=}")

    def update_user_last_contact(self, telegram_id: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET last_contact = ? WHERE telegram_id = ?""",
                (datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update user last contact {telegram_id=}")

    def update_user_games_played(self, user_id: int, games_played: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET games_played = games_played + ? WHERE user_id == ?""",
                (games_played, user_id)
            )

    def update_user_age(self, telegram_id: int, age: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET age = ?, last_contact = ? WHERE telegram_id = ?""",
                (age, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update lichess rating {telegram_id=}, {age=}")

    def get_user_on_telegram_id(self, telegram_id: int) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE user.telegram_id == ?""", (telegram_id,)
            )
            result = cursor.fetchone()
        return dict(result)

    def is_admin(self, telegram_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT is_admin FROM user WHERE user.telegram_id == ?""", (telegram_id,)
            )
        result = cursor.fetchone()
        return bool(result[0])

    def set_user_as_admin(self, public_id: int) -> str | None:
        """
        Return None if there is no user with 'public_id'.
        Return "" - empty string if the user with 'public_id' already is admin.
        Otherwise return users name + surname + nickname.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE public_id = ?""",
                (public_id,)
            )
        user = cursor.fetchone()
        if not user:
            return None
        user = dict(user)
        if user["is_admin"] == True:
            return ""

        self.conn.execute(
            """UPDATE user SET is_admin = ? WHERE public_id = ?""",
            (True, public_id)
        )
        logger.debug(f"update user {public_id=} is_admin to True")
        return user["name"] + " " + (user["surname"] if user["surname"] else "") + " " + (user["nickname"] if user["nickname"] else "")

    def remove_user_from_admins(self, public_id: int):
        """
        Return None if there is no user with 'public_id'.
        Return "" - empty string if the user with 'public_id' already is admin.
        Otherwise return users name + surname.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE public_id = ?""",
                (public_id,)
            )
        user = cursor.fetchone()
        if not user:
            return None
        user = dict(user)
        if user["is_admin"] == False:
            return ""

        self.conn.execute(
            """UPDATE user SET is_admin = ? WHERE public_id = ?""",
            (False, public_id)
        )

        logger.debug(f"update user {public_id=} is_admin to False")
        return user["name"] + " " + (user["surname"] if user["surname"] else "") + " " + (user["nickname"] if user["nickname"] else "")

    # TOURNAMENT =========================================================

    def add_tournament(
        self,
        tg_channel: str,
        message_id: int,
        summary: str,
        date_time: datetime.datetime,
        city_id: int | None = None,
        address: str | None = None,
        registration: bool = False,
        results_uploaded: bool = False
    ) -> bool:
        """
        Add new tournament if it has another (date_time, address) and
        tg_channel is in channel table.
        Return True on success, False if tournament with same date_time and address exists.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM tournament WHERE date_time = ? AND address = ?""",
                (date_time, address)
            )
        user = cursor.fetchone()
        if user:
            logger.debug(f"Trying to add existed tournament: {message_id=} {summary=} {date_time=}")
            return False

        with self.conn:
            cursor = self.conn.execute(
                """INSERT INTO tournament (
                    tournament_id,
                    tg_channel,
                    message_id,
                    city_id,
                    summary,
                    date_time,
                    address,
                    registration,
                    results_uploaded
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (None, tg_channel, message_id, city_id, summary, date_time, address, registration, results_uploaded)
            )
        logger.debug(f"Insert into tournaments {message_id=} {date_time=} {address=}")
        return True

    def update_tournament(
        self,
        tg_channel: str,
        message_id: int,
        summary: str,
        date_time: datetime.datetime,
        city_id: int | None = None,
        address: str | None = None,
    ):
        """
        Update tournament info if tournament with same tg_channel and message_id exists.
        Otherwise just add it as new tournament.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM tournament WHERE message_id = ? AND tg_channel = ?""",
                (message_id, tg_channel)
            )
        user = cursor.fetchone()
        if not user:
            logger.debug(f"Trying to update non existent tournament: {message_id=} {summary=} {date_time=}")
            self.add_tournament(tg_channel, message_id, summary, date_time, city_id, address)
            return

        self.conn.execute(
            """UPDATE tournament SET summary = ?, date_time = ?, city_id = ?, address = ? WHERE message_id = ? AND tg_channel = ?""",
            (summary, date_time, city_id, address, message_id, tg_channel)
        )
        logger.debug(f"Update tournament {tg_channel} {message_id=} {date_time=} {address=} ")

    def get_tournaments(
        self,
        from_date: datetime.datetime,
        to_date: datetime.datetime | None = None,
        results_uploaded: bool | None = None
    ) -> list[tuple]:
        request = "SELECT * FROM tournament WHERE date_time >= ?"
        values = [from_date]
        if to_date:
            request += " AND date_time <= ?"
            values.append(to_date)
        if results_uploaded is not None:
            request += " AND results_uploaded == ?"
            values.append(results_uploaded)
        request += " ORDER BY date_time"
        values = tuple(values)

        with self.conn:
            cursor = self.conn.execute(request, values)
        return cursor.fetchall()

    def remove_tournament(self, tg_channel: str, message_id: int):
        with self.conn:
            self.conn.execute(
                """DELETE FROM tournament WHERE tg_channel = ? AND message_id = ?""",
                (tg_channel, message_id)
            )

    def open_registration(self, tournament_id: int):
        with self.conn:
            self.conn.execute(
                """UPDATE tournament SET registration = ? WHERE tournament_id = ?""",
                (True, tournament_id)
            )

    def close_registration(self, tournament_id: int):
        with self.conn:
            self.conn.execute(
                """UPDATE tournament SET registration = ? WHERE tournament_id = ?""",
                (False, tournament_id)
            )

    def results_uploaded(self, tournament_id: int):
        with self.conn:
            self.conn.execute(
                """UPDATE tournament SET results_uploaded = ? WHERE tournament_id = ?""",
                (True, tournament_id)
            )

    def get_tournament_on_id(self, tournament_id: int) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM tournament WHERE tournament_id = ?""",
                (tournament_id,)
            )
        return dict(cursor.fetchone())

    # CITY =========================================================

    # TODO: переделать нормально, tg_channel в аргументы
    def get_photo_id(self):
        with self.conn:
            cursor = self.conn.execute(
                """SELECT timetable_photo FROM city WHERE tg_channel = 'repchess'"""
            )
        return cursor.fetchone()[0]

    def update_weakly_info(self, channel, message_id, photo_id):
        with self.conn:
            self.conn.execute(
                """UPDATE city SET timetable_message_id = ?, timetable_photo = ? WHERE tg_channel = ?""",
                (message_id, photo_id, channel)
            )

    # USER_ON_TOURNAMENT ===========================================

    def add_user_on_tournament(self, user_id: int, tournament_id: int, nickname: str, rating: int, k_factor: int):
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user_on_tournament WHERE user_id = ? AND tournament_id = ?""",
                (user_id, tournament_id)
            )
        res = cursor.fetchone()
        if res:
            with self.conn:
                self.conn.execute(
                    """UPDATE user_on_tournament SET nickname = ? WHERE user_id = ? AND tournament_id = ?""",
                    (nickname, user_id, tournament_id)
                )
            return

        with self.conn:
            self.conn.execute(
                """INSERT INTO user_on_tournament (
                    user_on_tournament_id,
                    tournament_id,
                    user_id,
                    nickname,
                    rating_before,
                    rating_after,
                    place,
                    score,
                    k_factor
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (None, tournament_id, user_id, nickname, rating, None, None, None, k_factor)
            )

    def get_registered_users(self, tournament_id: int) -> list:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user_on_tournament WHERE tournament_id = ?""",
                (tournament_id,)
            )
        return cursor.fetchall()

    def get_user_on_tournament_on_nickname(self, tournament_id: int, nickname: str) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT user_id FROM user_on_tournament WHERE tournament_id = ? AND nickname = ?""",
                (tournament_id, nickname)
            )
        return dict(cursor.fetchone())

    def update_user_on_tournament(self, tournament_id: int, nickname: str, rating_after: int, place: int, score: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user_on_tournament SET rating_after = ?, place = ?, score = ?
                WHERE tournament_id == ? AND nickname == ?""",
                (rating_after, place, score, tournament_id, nickname)
            )

    # GAME ======================================================

    def add_game(
        self,
        tournament_id: int,
        white_user_id: int,
        black_user_id: int,
        round: int,
        result: float,
        desk_number: int | None = None,
        white_rating_change: int | None = None,
        black_rating_change: int | None = None,
    ):
        with self.conn:
            self.conn.execute(
                """INSERT INTO game (
                    game_id,
                    tournament_id,
                    white_user_id,
                    black_user_id,
                    round,
                    desk_number,
                    result,
                    white_rating_change,
                    black_rating_change
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (None, tournament_id, white_user_id, black_user_id, round, desk_number, result, white_rating_change, black_rating_change)
            )


rep_chess_db = RepChessDB()
