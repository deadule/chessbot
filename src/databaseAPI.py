import sqlite3
import datetime
from zoneinfo import ZoneInfo
import logging
import os
import sys
from collections import deque

def _setup_logger():
    logfile_dir = os.getenv("REPCHESS_LOG_DIR")
    if not logfile_dir:
        data_dir = os.getenv("DATA_DIR", "/app/data")
        logfile_dir = os.path.join(data_dir, "logs")

    try:
        os.makedirs(logfile_dir, exist_ok=True)
    except Exception as e:
        print(f"[CRITICAL] Failed to create log directory '{logfile_dir}': {e}", file=sys.stderr)
        sys.exit(1)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        try:
            handler = logging.FileHandler(os.path.join(logfile_dir, "database.log"))
        except Exception as e:
            print(f"[CRITICAL] Cannot open log file in '{logfile_dir}': {e}", file=sys.stderr)
            sys.exit(1)

        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s : %(levelname)s: %(message)s")
        )
        logger.addHandler(handler)

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(
            logging.Formatter("[DB] %(levelname)s: %(message)s")
        )
        logger.addHandler(console)

    logger.propagate = False
    return logger

logger = _setup_logger()

# logger = logging.getLogger(__name__)
# logfile_dir = os.getenv("REPCHESS_LOG_DIR")
# logger_handler = logging.FileHandler(os.path.join(logfile_dir, "database.log"))
# logger_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s : %(levelname)s: %(message)s"))
# logger.addHandler(logger_handler)
# logger.setLevel(logging.DEBUG)
# logger.propagate = False


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
                
                CREATE TABLE IF NOT EXISTS subscription (
                    telegram_id INTEGER PRIMARY KEY,
                    active_subscription BOOL,
                    subscription_valid_until datetime,
                    subscription_payment_method_id TEXT,
                    subscription_auto_renew BOOL,
                    subscription_next_charge datetime,
                    user_phone TEXT
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

                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY,
                    file_id_480p TEXT,
                    file_id_1080p TEXT,
                    title TEXT,
                    description TEXT,
                    category TEXT,
                    lesson_number INTEGER,
                    original_file_id TEXT,
                    original_path TEXT,
                    processing_status TEXT DEFAULT 'pending'
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
            self.conn.execute(
                """INSERT OR IGNORE INTO subscription (
                    telegram_id,
                    active_subscription,
                    subscription_valid_until,
                    subscription_payment_method_id,
                    subscription_auto_renew,
                    subscription_next_charge,
                    user_phone
                ) VALUES (?, 0, NULL, NULL, 0, NULL, NULL)""",
                (telegram_id,)
            )
        logger.debug(f"register user {telegram_id}, {public_id}, {is_admin}, {name}, {surname}, {nickname}, {city_id}, {first_contact}, {last_contact}, {lichess_rating}, {chesscom_rating}, {rep_rating} {age}")
        
    # SUBSCRIPTION =========================================================
    
    def check_user_active_subscription(self, telegram_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT active_subscription, subscription_valid_until FROM subscription WHERE telegram_id = ?""",
                (telegram_id,)
            )
            result = cursor.fetchone()
        
        if not result:
            return False

        subscription_flag = bool(result["active_subscription"])

        if not subscription_flag:
            return False

        valid_until_value = result["subscription_valid_until"]

        if not valid_until_value:
            return subscription_flag

        if isinstance(valid_until_value, str):
            try:
                valid_until = datetime.datetime.fromisoformat(valid_until_value)
            except ValueError:
                logger.warning(
                    "Unable to parse subscription_valid_until '%s' for telegram_id %s",
                    valid_until_value,
                    telegram_id,
                )
                return subscription_flag
        else:
            valid_until = valid_until_value

        if valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=MOSCOW_TZ)
        else:
            valid_until = valid_until.astimezone(MOSCOW_TZ)

        now = datetime.datetime.now(MOSCOW_TZ)

        if valid_until < now:
            with self.conn:
                self.conn.execute(
                    """UPDATE subscription SET active_subscription = 0 WHERE telegram_id = ?""",
                    (telegram_id,)
                )
            return False

        return True
    
    def ensure_subscription_row(self, telegram_id: int) -> None:
        """Make sure a subscription row exists for this user."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO subscription (telegram_id)
                VALUES (?)
                """,
                (telegram_id,),
            )

    def set_user_subscription(
        self,
        telegram_id: int,
        is_active: bool,
        valid_until: datetime.datetime | None = None,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """UPDATE subscription
                SET active_subscription = ?,
                    subscription_valid_until = ?
                WHERE telegram_id = ?""",
                (is_active, valid_until, telegram_id),
            )

    def update_subscription_payment_method(
        self,
        telegram_id: int,
        payment_method_id: str | None,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """UPDATE subscription
                SET subscription_payment_method_id = ?
                WHERE telegram_id = ?""",
                (payment_method_id, telegram_id),
            )

    def update_subscription_auto_renew(
        self,
        telegram_id: int,
        auto_renew: bool,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """UPDATE subscription
                SET subscription_auto_renew = ?
                WHERE telegram_id = ?""",
                (auto_renew, telegram_id),
            )

    def update_subscription_next_charge(
        self,
        telegram_id: int,
        next_charge: datetime.datetime | None,
    ) -> None:
        with self.conn:
            self.conn.execute(
                """UPDATE subscription
                SET subscription_next_charge = ?
                WHERE telegram_id = ?""",
                (next_charge, telegram_id),
            )

    def get_subscription_details(self, telegram_id: int) -> dict | None:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT active_subscription, subscription_valid_until, subscription_payment_method_id,
                           subscription_auto_renew, subscription_next_charge, user_phone
                    FROM subscription WHERE telegram_id = ?""",
                (telegram_id,)
            )
            row = cursor.fetchone()

        return dict(row) if row else None

    def get_due_subscriptions(self) -> list[dict]:
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self.conn:
            cursor = self.conn.execute(
                """
                SELECT 
                    telegram_id,
                    user_phone AS phone,
                    subscription_payment_method_id
                FROM subscription
                WHERE 
                    active_subscription = 1
                    AND subscription_auto_renew = 1
                    AND subscription_payment_method_id IS NOT NULL
                    AND user_phone IS NOT NULL
                    AND subscription_next_charge IS NOT NULL
                    AND subscription_next_charge <= ?
                """,
                (now_utc,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_phone(self, telegram_id: int) -> str | None:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT user_phone FROM subscription WHERE telegram_id = ?""",
                (telegram_id,)
            )
            row = cursor.fetchone()

        return row[0] if row else None

    def set_user_phone(self, telegram_id: int, phone: str) -> bool:
        # debug
        for row in self.conn.execute("PRAGMA database_list"):
            logging.info("DB attached: %s -> %s", row[1], row[2])
            
        with self.conn:
            cur = self.conn.execute(
                """
                INSERT INTO subscription (telegram_id, user_phone)
                VALUES (?, ?)
                ON CONFLICT(telegram_id) DO UPDATE
                SET user_phone = excluded.user_phone
                """,
            (telegram_id, phone),
            )
        return True
            
    # USER =========================================================

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
           
    def check_for_user_in_db_return_nickname(self, telegram_id: int):
        with self.conn:
            cursor = self.conn.execute(
                """SELECT nickname FROM user WHERE telegram_id = ?""",
                (telegram_id,)
            )
            result = cursor.fetchone()
        
        return result[0] if result else None
    
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
        logger.debug(f"update user age {telegram_id=}, {age=}")

    def update_user_city_id(self, telegram_id: int, city_id: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user SET city_id = ?, last_contact = ? WHERE telegram_id = ?""",
                (city_id, datetime.datetime.now(), telegram_id)
            )
        logger.debug(f"update user city id {telegram_id=}, {city_id=}")

    def get_user_on_telegram_id(self, telegram_id: int) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE telegram_id == ?""", (telegram_id,)
            )
            result = cursor.fetchone()
        return dict(result)

    def get_user_on_user_id(self, user_id: int) -> dict:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user WHERE user_id == ?""", (user_id,)
            )
            result = cursor.fetchone()
        return dict(result)

    def is_admin(self, telegram_id: int) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                "SELECT is_admin FROM user WHERE telegram_id = ?", (telegram_id,)
            )
            row = cursor.fetchone()

        if row is None:
            return False

        return bool(row[0])


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

    # VIDEOS =========================================================

    def add_video(self, file_id_480p: str = None, file_id_1080p: str = None, title: str = None, description: str = None, category: str = None, lesson_number: int = None, original_file_id: str = None, original_path: str = None, processing_status: str = "pending"):
        with self.conn:
            self.conn.execute(
                """INSERT INTO videos (file_id_480p, file_id_1080p, title, description, category, lesson_number, original_file_id, original_path, processing_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (file_id_480p, file_id_1080p, title, description, category, lesson_number, original_file_id, original_path, processing_status)
            )
        logger.debug(f"add video {file_id_480p=}, {file_id_1080p=}, {title=}, {category=}, {lesson_number=}, {processing_status=}")
    
    def update_video_quality(self, video_id: int, file_id_480p: str = None, file_id_1080p: str = None, processing_status: str = None):
        """Update video quality file_ids and processing status"""
        updates = []
        values = []
        
        if file_id_480p is not None:
            updates.append("file_id_480p = ?")
            values.append(file_id_480p)
        
        if file_id_1080p is not None:
            updates.append("file_id_1080p = ?")
            values.append(file_id_1080p)
        
        if processing_status is not None:
            updates.append("processing_status = ?")
            values.append(processing_status)
        
        if not updates:
            return False
        
        values.append(video_id)
    
        with self.conn:
            self.conn.execute(
                f"""UPDATE videos SET {', '.join(updates)} WHERE id = ?""",
                values
            )
        logger.debug(f"update video quality {video_id=}, {file_id_480p=}, {file_id_1080p=}, {processing_status=}")
        return True
    
    def get_videos_by_category(self, category: str) -> list[dict]:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos WHERE category = ?""",
                (category,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_videos(self) -> list[dict]:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos ORDER BY category, lesson_number ASC"""
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_videos_by_category_ordered(self, category: str) -> list[dict]:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos WHERE category = ? ORDER BY lesson_number ASC""",
                (category,)
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_next_lesson_number(self, category: str) -> int:
        """Get the next lesson number for a given category"""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT MAX(lesson_number) FROM videos WHERE category = ?""",
                (category,)
            )
        result = cursor.fetchone()
        max_lesson = result[0] if result[0] is not None else 0
        return max_lesson + 1
    
    def get_video_by_id(self, video_id: int) -> dict | None:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos WHERE id = ?""",
                (video_id,)
            )
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def delete_video(self, video_id: int) -> bool:
        """Delete video from database"""
        with self.conn:
            cursor = self.conn.execute(
                """DELETE FROM videos WHERE id = ?""",
                (video_id,)
            )
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent video {video_id=}")
            return False
        logger.debug(f"delete video {video_id=}")
        
        # Delete video files from storage
        from video_processor import VideoProcessor
        VideoProcessor.delete_video_files_static(video_id)
        
        return True
    
    def update_video_metadata(self, video_id: int, title: str, description: str) -> bool:
        with self.conn:
            cursor = self.conn.execute(
                """UPDATE videos SET title = ?, description = ? WHERE id = ?""",
                (title, description, video_id)
            )
        if cursor.rowcount == 0:
            logger.warning(f"Attempted to update non-existent video {video_id=}")
            return False
        logger.debug(f"update video metadata {video_id=}, {title=}")
        return True

    # CATEGORIES =========================================================

    def get_all_categories(self) -> list[str]:
        """Get all unique categories from videos table"""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT DISTINCT category FROM videos ORDER BY category ASC"""
            )
        return [row[0] for row in cursor.fetchall() if row[0]]
    
    def add_category(self, category_name: str) -> bool:
        """Add a new category (just creates a placeholder video entry)"""
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO videos (file_id_480p, file_id_1080p, title, description, category, lesson_number, original_file_id, processing_status) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    ("placeholder", "placeholder", f"Категория {category_name}", "", category_name, 0, "placeholder", "completed")
                )
            logger.debug(f"add category {category_name=}")
            return True
        except Exception as e:
            logger.error(f"Error adding category {category_name}: {e}")
            return False
    
    def delete_category(self, category_name: str) -> bool:
        """Delete a category and all its videos"""
        try:
            with self.conn:
                cursor = self.conn.execute(
                    """DELETE FROM videos WHERE category = ?""",
                    (category_name,)
                )
            logger.debug(f"delete category {category_name=}, deleted {cursor.rowcount} videos")
            return True
        except Exception as e:
            logger.error(f"Error deleting category {category_name}: {e}")
            return False
    
    def category_exists(self, category_name: str) -> bool:
        """Check if category exists"""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT COUNT(*) FROM videos WHERE category = ?""",
                (category_name,)
            )
        return cursor.fetchone()[0] > 0
    
    def get_videos_by_quality(self, quality: str) -> list[dict]:
        """Get videos that have the specified quality available"""
        if quality == "480p":
            field = "file_id_480p"
        elif quality == "1080p":
            field = "file_id_1080p"
        else:
            return []
        
        with self.conn:
            cursor = self.conn.execute(
                f"""SELECT * FROM videos WHERE {field} IS NOT NULL AND {field} != 'placeholder' AND processing_status = 'completed'""",
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_videos_pending_processing(self) -> list[dict]:
        """Get videos that are pending processing"""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos WHERE processing_status = 'pending'""",
            )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_video_file_id(self, video_id: int, quality: str) -> str | None:
        """Get file_id for specific video and quality"""
        if quality == "480p":
            field = "file_id_480p"
        elif quality == "1080p":
            field = "file_id_1080p"
        else:
            return None
        
        with self.conn:
            cursor = self.conn.execute(
                f"""SELECT {field} FROM videos WHERE id = ? AND processing_status = 'completed'""",
                (video_id,)
            )
        result = cursor.fetchone()
        return result[0] if result and result[0] != "placeholder" else None

    def get_video_by_category_and_lesson(self, category: str, lesson_number: int) -> dict | None:
        """Get video by category and lesson number"""
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM videos WHERE category = ? AND lesson_number = ?""",
                (category, lesson_number)
            )
        result = cursor.fetchone()
        return dict(result) if result else None
    
    def delete_videos_by_category_and_lesson(self, category: str, lesson_number: int, statuses: list[str] = None) -> int:
        """Delete videos by category and lesson number, optionally filtered by status"""
        if statuses is None:
            statuses = ['pending', 'failed']
        
        # First get the video IDs that will be deleted
        placeholders = ','.join(['?'] * len(statuses))
        with self.conn:
            cursor = self.conn.execute(
                f"""SELECT id FROM videos WHERE category = ? AND lesson_number = ? AND processing_status IN ({placeholders})""",
                (category, lesson_number, *statuses)
            )
            video_ids = [row[0] for row in cursor.fetchall()]
        
        if video_ids:
            placeholders = ','.join(['?'] * len(statuses))
            with self.conn:
                cursor = self.conn.execute(
                    f"""DELETE FROM videos WHERE category = ? AND lesson_number = ? AND processing_status IN ({placeholders})""",
                    (category, lesson_number, *statuses)
                )
            deleted_count = cursor.rowcount
            
            from video_processor import VideoProcessor
            for video_id in video_ids:
                VideoProcessor.delete_video_files_static(video_id)
            
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} video(s) with category={category}, lesson_number={lesson_number}, statuses={statuses}")
            return deleted_count
        return 0

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
        tg_channel: str,
        from_date: datetime.datetime,
        to_date: datetime.datetime | None = None,
        results_uploaded: bool | None = None
    ) -> list[tuple]:
        request = "SELECT * FROM tournament WHERE date_time >= ? and tg_channel == ?"
        values = [from_date, tg_channel]
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
        return list(map(dict, cursor.fetchall()))

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

    def add_city(self, tg_channel: str, name: str):
        with self.conn:
            self.conn.execute(
                """INSERT INTO city (
                    city_id,
                    name,
                    tg_channel,
                    timetable_message_id,
                    timetable_photo
                ) VALUES(?, ?, ?, ?, ?)""",
                (None, name, tg_channel, None, None) 
            )

    def get_photo_id(self, tg_channel: str) -> str:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT timetable_photo FROM city WHERE tg_channel = ?""",
                (tg_channel,)
            )
        return cursor.fetchone()[0]

    def get_city_on_id(self, city_id: int) -> str | None:
        """
        Return city name on city id. If city_id isn't in table, return None.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT name FROM city WHERE city_id = ?""",
                (city_id,)
            )
        city = cursor.fetchone()[0]
        if not city:
            return None
        return city

    def get_id_on_city_name(self, city: str) -> int | None:
        """
        Return city id on name. If city with name isn't in table, return None.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT city_id FROM city WHERE name = ?""",
                (city,)
            )
        city_id = cursor.fetchone()[0]
        if not city_id:
            return None
        return int(city_id)

    def get_cities_names(self) -> list[str]:
        with self.conn:
            cursor = self.conn.execute("""SELECT name FROM city""")
        return list(city_raw[0] for city_raw in cursor.fetchall())

    def get_tg_channel_on_tg_id(self, telegram_id: int) -> str:
        """
        Return tg channel of city where user telegram id is. If city id isn't in table, return None.
        """
        user = self.get_user_on_telegram_id(telegram_id)
        with self.conn:
            cursor = self.conn.execute(
                """SELECT tg_channel FROM city WHERE city_id = ?""",
                (user['city_id'],)
            )
        tg_channel = cursor.fetchone()
        if not tg_channel:
            return None
        return tg_channel[0]

    def delete_city(self, city: str):
        """
        Users with deleted city now set to Moscow (city_id = 1)
        """
        city_id = self.get_id_on_city_name(city)
        with self.conn:
            self.conn.execute(
                """UPDATE user SET city_id = 1 WHERE city_id = ?""",
                (city_id,)
            )

            self.conn.execute(
                """DELETE FROM city WHERE city_id = ?""",
                (city_id,)
            )

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

    def get_registered_users(self, tournament_id: int) -> list[tuple]:
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user_on_tournament WHERE tournament_id = ?""",
                (tournament_id,)
            )
        return cursor.fetchall()

    def get_user_on_tournament_on_nickname(self, tournament_id: int, nickname: str) -> dict:
        """
        Return None if there aren't user on tournament with nickname.
        Otherwise return user_on_tournament element.
        """
        with self.conn:
            cursor = self.conn.execute(
                """SELECT * FROM user_on_tournament WHERE tournament_id = ? AND nickname = ?""",
                (tournament_id, nickname)
            )
        user_on_tournament = cursor.fetchone()
        if not user_on_tournament:
            return None
        return dict(user_on_tournament)

    def update_user_on_tournament(self, tournament_id: int, nickname: str, rating_after: int, place: int, score: int):
        with self.conn:
            self.conn.execute(
                """UPDATE user_on_tournament SET rating_after = ?, place = ?, score = ?
                WHERE tournament_id == ? AND nickname == ?""",
                (rating_after, place, score, tournament_id, nickname)
            )

    def get_tournaments_with_registration(
        self,
        from_date: datetime.datetime,
        results_uploaded: bool
    ):
        with self.conn:
            cursor = self.conn.execute(
                """SELECT DISTINCT tournament.* FROM user_on_tournament JOIN tournament ON user_on_tournament.tournament_id = tournament.tournament_id
                WHERE tournament.date_time >= ? AND tournament.results_uploaded = ?""",
                (from_date, results_uploaded)
            )

        return list(map(dict, cursor.fetchall()))

    def delete_user_on_tournament(self, tournament_id: int, nickname: str):
        with self.conn:
            self.conn.execute(
                """DELETE FROM user_on_tournament WHERE tournament_id = ? AND nickname = ?""",
                (tournament_id, nickname)
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
MOSCOW_TZ = ZoneInfo("Europe/Moscow")
