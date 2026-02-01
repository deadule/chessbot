import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
import datetime
from zoneinfo import ZoneInfo
import logging
import os
import sys
from collections import deque
from contextlib import contextmanager

logger = logging.getLogger(__name__)
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

# who the hell uses sqlite3? and god why
class RepChessDB:
    # Assume that all players amount is less than 1 million.
    MAX_PUBLIC_ID = 1000000
    # We need this variable to optimize searching public id for new player.
    FREE_PUBLIC_IDS = deque(maxlen=100000)

    def initialize(self):
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            logger.error("Can't find DATABASE_URL!")
            print("Set the DATABASE_URL variable (e.g., postgresql://user:pass@host:5432/dbname).")
            sys.exit(1)

        try:
            # initialize connection pool instead of single connection
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=db_url,
                cursor_factory=RealDictCursor
            )
            logger.info("Database pool initialized (min=1, max=10 connections)")
            
            # create tables and init IDs
            self._create_tables()
            self._init_free_ids()
            logger.info("Database is ready")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            sys.exit(1)

    @contextmanager
    def get_connection(self):
        """Get connection from pool with automatic cleanup"""
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

    def _create_tables(self):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS city (
                        city_id SERIAL PRIMARY KEY,
                        name TEXT,
                        tg_channel TEXT UNIQUE,
                        timetable_message_id TEXT,
                        timetable_photo TEXT
                    );
                """)
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS "user" (
                        user_id SERIAL PRIMARY KEY,
                        telegram_id BIGINT UNIQUE NOT NULL,
                        public_id INTEGER UNIQUE NOT NULL,
                        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                        name TEXT,
                        surname TEXT,
                        nickname TEXT,
                        city_id INTEGER REFERENCES city(city_id) ON DELETE SET NULL,
                        first_contact TIMESTAMPTZ,
                        last_contact TIMESTAMPTZ,
                        lichess_rating INTEGER,
                        chesscom_rating INTEGER,
                        rep_rating INTEGER NOT NULL DEFAULT 1600,
                        games_played INTEGER NOT NULL DEFAULT 0,
                        age INTEGER
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS subscription (
                        telegram_id BIGINT PRIMARY KEY REFERENCES "user"(telegram_id) ON DELETE CASCADE,
                        active_subscription BOOLEAN NOT NULL DEFAULT FALSE,
                        subscription_valid_until TIMESTAMPTZ,
                        subscription_payment_method_id TEXT,
                        subscription_auto_renew BOOLEAN NOT NULL DEFAULT FALSE,
                        subscription_next_charge TIMESTAMPTZ,
                        user_phone TEXT
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS tournament (
                        tournament_id SERIAL PRIMARY KEY,
                        tg_channel TEXT,
                        message_id BIGINT,
                        city_id INTEGER REFERENCES city(city_id),
                        summary TEXT,
                        date_time TIMESTAMPTZ,
                        address TEXT,
                        registration BOOLEAN NOT NULL DEFAULT FALSE,
                        results_uploaded BOOLEAN NOT NULL DEFAULT FALSE,
                        UNIQUE(tg_channel, message_id)
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS user_on_tournament (
                        user_on_tournament_id SERIAL PRIMARY KEY,
                        tournament_id INTEGER NOT NULL REFERENCES tournament(tournament_id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES "user"(public_id) ON DELETE CASCADE,
                        nickname TEXT,
                        rating_before INTEGER,
                        rating_after INTEGER,
                        place INTEGER,
                        score REAL,
                        k_factor INTEGER,
                        UNIQUE(tournament_id, user_id)
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS game (
                        game_id SERIAL PRIMARY KEY,
                        tournament_id INTEGER NOT NULL REFERENCES tournament(tournament_id) ON DELETE CASCADE,
                        white_user_id INTEGER NOT NULL REFERENCES "user"(user_id),
                        black_user_id INTEGER NOT NULL REFERENCES "user"(user_id),
                        round INTEGER,
                        desk_number INTEGER,
                        result REAL NOT NULL,
                        white_rating_change INTEGER,
                        black_rating_change INTEGER
                    );
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        id SERIAL PRIMARY KEY,
                        file_id_480p TEXT,
                        file_id_1080p TEXT,
                        title TEXT,
                        description TEXT,
                        category TEXT,
                        lesson_number INTEGER,
                        original_file_id TEXT,
                        original_path TEXT,
                        processing_status TEXT NOT NULL DEFAULT 'pending'
                    );
                ''')
                # create indexes for performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_videos_processing_status 
                    ON videos(processing_status)
                """)
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_videos_category_lesson 
                    ON videos(category, lesson_number)
                """)
            conn.commit()

    def _init_free_ids(self):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT public_id FROM "user"')
                occupied = {row["public_id"] for row in cur.fetchall()}
        
        for i in range(101, self.MAX_PUBLIC_ID):
            if len(self.FREE_PUBLIC_IDS) >= 90000:
                break
            if i not in occupied:
                self.FREE_PUBLIC_IDS.appendleft(i)

    def __del__(self):
        if hasattr(self, "pool") and self.pool:
            self.pool.closeall()
            logger.info("Database pool closed")

    # ================= USER =================
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
        age: int | None = None,
    ):
        if public_id is None:
            if not self.FREE_PUBLIC_IDS:
                raise RuntimeError("No free public IDs available")
            public_id = self.FREE_PUBLIC_IDS.pop()

        now = datetime.datetime.now(MOSCOW_TZ)
        first_contact = first_contact or now
        last_contact = last_contact or now

        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO "user" (
                            telegram_id, public_id, is_admin, name, surname, nickname,
                            city_id, first_contact, last_contact, lichess_rating,
                            chesscom_rating, rep_rating, games_played, age
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (telegram_id) DO NOTHING
                    """, (
                        telegram_id, public_id, is_admin, name, surname, nickname,
                        city_id, first_contact, last_contact, lichess_rating,
                        chesscom_rating, rep_rating, games_played, age
                    ))
                    cur.execute("""
                        INSERT INTO subscription (telegram_id)
                        VALUES (%s)
                        ON CONFLICT (telegram_id) DO NOTHING
                    """, (telegram_id,))
                conn.commit()
                logger.debug(f"register user {telegram_id}, {public_id}, {is_admin}, {name}, {surname}, {nickname}, {city_id}, {first_contact}, {last_contact}, {lichess_rating}, {chesscom_rating}, {rep_rating} {age}")
            except Exception as e:
                conn.rollback()
                logger.exception(f"register_user failed: {e}")
                raise

    # ================= SUBSCRIPTION =================
    def check_user_active_subscription(self, telegram_id: int) -> bool:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT active_subscription, subscription_valid_until
                    FROM subscription WHERE telegram_id = %s
                """, (telegram_id,))
                row = cur.fetchone()
                if not row:
                    return False
                active = row["active_subscription"]
                valid_until = row["subscription_valid_until"]
                if not active:
                    return False
                if valid_until is None:
                    return True
                now = datetime.datetime.now(MOSCOW_TZ)
                if valid_until.tzinfo is None:
                    valid_until = valid_until.replace(tzinfo=MOSCOW_TZ)
                else:
                    valid_until = valid_until.astimezone(MOSCOW_TZ)
                if valid_until < now:
                    with conn.cursor() as c2:
                        c2.execute("""
                            UPDATE subscription SET active_subscription = FALSE
                            WHERE telegram_id = %s
                        """, (telegram_id,))
                    conn.commit()
                    return False
                return True

    def ensure_subscription_row(self, telegram_id: int) -> None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO subscription (telegram_id)
                        VALUES (%s)
                        ON CONFLICT (telegram_id) DO NOTHING
                    """, (telegram_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"ensure_subscription_row failed: {e}")
                raise

    def set_user_subscription(
        self,
        telegram_id: int,
        is_active: bool,
        valid_until: datetime.datetime | None = None,
    ) -> None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE subscription
                        SET active_subscription = %s, subscription_valid_until = %s
                        WHERE telegram_id = %s
                    """, (is_active, valid_until, telegram_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"set_user_subscription failed: {e}")
                raise

    def update_subscription_payment_method(self, telegram_id: int, payment_method_id: str | None) -> None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE subscription
                        SET subscription_payment_method_id = %s
                        WHERE telegram_id = %s
                    """, (payment_method_id, telegram_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_subscription_payment_method failed: {e}")
                raise

    def update_subscription_auto_renew(self, telegram_id: int, auto_renew: bool) -> None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE subscription
                        SET subscription_auto_renew = %s
                        WHERE telegram_id = %s
                    """, (auto_renew, telegram_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_subscription_auto_renew failed: {e}")
                raise

    def update_subscription_next_charge(self, telegram_id: int, next_charge: datetime.datetime | None) -> None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE subscription
                        SET subscription_next_charge = %s
                        WHERE telegram_id = %s
                    """, (next_charge, telegram_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_subscription_next_charge failed: {e}")
                raise

    def get_subscription_details(self, telegram_id: int) -> dict | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT active_subscription, subscription_valid_until, subscription_payment_method_id,
                    subscription_auto_renew, subscription_next_charge, user_phone
                    FROM subscription WHERE telegram_id = %s
                """, (telegram_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def get_due_subscriptions(self) -> list[dict]:
        now = datetime.datetime.now(datetime.timezone.utc)
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT
                        telegram_id,
                        user_phone AS phone,
                        subscription_payment_method_id
                    FROM subscription
                    WHERE
                        active_subscription = TRUE
                        AND subscription_auto_renew = TRUE
                        AND subscription_payment_method_id IS NOT NULL
                        AND user_phone IS NOT NULL
                        AND subscription_next_charge IS NOT NULL
                        AND subscription_next_charge <= %s
                """, (now,))
                return [dict(row) for row in cur.fetchall()]

    def get_user_phone(self, telegram_id: int) -> str | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT user_phone FROM subscription WHERE telegram_id = %s", (telegram_id,))
                row = cur.fetchone()
                return row["user_phone"] if row else None

    def set_user_phone(self, telegram_id: int, phone: str) -> bool:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO subscription (telegram_id, user_phone)
                        VALUES (%s, %s)
                        ON CONFLICT (telegram_id)
                        DO UPDATE SET user_phone = EXCLUDED.user_phone
                    """, (telegram_id, phone))
                conn.commit()
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"set_user_phone failed: {e}")
                return False

    # ================= USER GETTERS / UPDATERS =================
    def update_user_public_id(self, old_public_id: int, public_id: int) -> bool | None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM \"user\" WHERE public_id = %s", (public_id,))
                    if cur.fetchone():
                        return False
                    cur.execute("SELECT 1 FROM \"user\" WHERE public_id = %s", (old_public_id,))
                    if not cur.fetchone():
                        return None
                    cur.execute("""
                        UPDATE "user" SET public_id = %s WHERE public_id = %s
                    """, (public_id, old_public_id))
                conn.commit()
                self.FREE_PUBLIC_IDS.append(old_public_id)
                try:
                    self.FREE_PUBLIC_IDS.remove(public_id)
                except ValueError:
                    pass
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_public_id failed: {e}")
                return None

    def check_for_user_in_db_return_nickname(self, telegram_id: int) -> str | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nickname FROM \"user\" WHERE telegram_id = %s", (telegram_id,))
                row = cur.fetchone()
                return row["nickname"] if row else None

    def _update_user_field(self, telegram_id: int, field: str, value):
        now = datetime.datetime.now(MOSCOW_TZ)
        query = sql.SQL('UPDATE "user" SET {} = %s, last_contact = %s WHERE telegram_id = %s').format(sql.Identifier(field))
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(query, (value, now, telegram_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"_update_user_field failed for {field}: {e}")
                raise

    def update_user_name(self, telegram_id: int, name: str):
        self._update_user_field(telegram_id, "name", name)
        logger.debug(f"update user name {telegram_id=}, {name=}")

    def update_user_surname(self, telegram_id: int, surname: str):
        self._update_user_field(telegram_id, "surname", surname)
        logger.debug(f"update user surname {telegram_id=}, {surname=}")

    def update_user_nickname(self, telegram_id: int, nickname: str):
        self._update_user_field(telegram_id, "nickname", nickname)
        logger.debug(f"update user nickname {telegram_id=}, {nickname=}")

    def update_user_lichess_rating(self, telegram_id: int, lichess_rating: int):
        self._update_user_field(telegram_id, "lichess_rating", lichess_rating)
        logger.debug(f"update lichess rating {telegram_id=}, {lichess_rating=}")

    def update_user_chesscom_rating(self, telegram_id: int, chesscom_rating: int):
        self._update_user_field(telegram_id, "chesscom_rating", chesscom_rating)
        logger.debug(f"update chesscom_rating {telegram_id=}, {chesscom_rating=}")

    def update_user_rep_rating_with_rep_id(self, public_id: int, rep_rating: int):
        now = datetime.datetime.now(MOSCOW_TZ)
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE "user" SET rep_rating = %s, last_contact = %s WHERE public_id = %s
                    """, (rep_rating, now, public_id))
                    if cur.rowcount == 0:
                        raise ValueError(f"User with public_id {public_id} not found")
                conn.commit()
                logger.debug(f"update rep rating {public_id=}, {rep_rating=}")
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_rep_rating_with_rep_id failed: {e}")
                raise

    def update_user_rep_rating_with_user_id(self, user_id: int, rep_rating: int):
        now = datetime.datetime.now(MOSCOW_TZ)
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE "user" SET rep_rating = %s, last_contact = %s WHERE user_id = %s
                    """, (rep_rating, now, user_id))
                conn.commit()
                logger.debug(f"update rep rating {user_id=}, {rep_rating=}")
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_rep_rating_with_user_id failed: {e}")
                raise

    def update_user_last_contact(self, telegram_id: int):
        now = datetime.datetime.now(MOSCOW_TZ)
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute('UPDATE "user" SET last_contact = %s WHERE telegram_id = %s', (now, telegram_id))
                conn.commit()
                logger.debug(f"update user last contact {telegram_id=}")
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_last_contact failed: {e}")
                raise

    def update_user_games_played(self, user_id: int, games_played: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE "user" SET games_played = games_played + %s WHERE user_id = %s
                    """, (games_played, user_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_games_played failed: {e}")
                raise

    def update_user_age(self, telegram_id: int, age: int):
        self._update_user_field(telegram_id, "age", age)
        logger.debug(f"update user age {telegram_id=}, {age=}")

    def update_user_city_id(self, telegram_id: int, city_id: int):
        self._update_user_field(telegram_id, "city_id", city_id)
        logger.debug(f"update user city id {telegram_id=}, {city_id=}")

    def get_user_on_telegram_id(self, telegram_id: int) -> dict:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "user" WHERE telegram_id = %s', (telegram_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"User with telegram_id {telegram_id} not found")
                return dict(row)

    def get_user_on_user_id(self, user_id: int) -> dict:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM "user" WHERE user_id = %s', (user_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"User with user_id {user_id} not found")
                return dict(row)

    def is_admin(self, telegram_id: int) -> bool:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT is_admin FROM "user" WHERE telegram_id = %s', (telegram_id,))
                row = cur.fetchone()
                return bool(row["is_admin"]) if row else False

    def set_user_as_admin(self, public_id: int) -> str | None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM "user" WHERE public_id = %s', (public_id,))
                    user = cur.fetchone()
                    if not user:
                        return None
                    if user["is_admin"]:
                        return ""
                    cur.execute('UPDATE "user" SET is_admin = TRUE WHERE public_id = %s', (public_id,))
                conn.commit()
                logger.debug(f"update user {public_id=} is_admin to True")
                name = user["name"] or ""
                surname = user["surname"] or ""
                nickname = user["nickname"] or ""
                return f"{name} {surname} {nickname}".strip()
            except Exception as e:
                conn.rollback()
                logger.exception(f"set_user_as_admin failed: {e}")
                return None

    def remove_user_from_admins(self, public_id: int) -> str | None:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT * FROM "user" WHERE public_id = %s', (public_id,))
                    user = cur.fetchone()
                    if not user:
                        return None
                    if not user["is_admin"]:
                        return ""
                    cur.execute('UPDATE "user" SET is_admin = FALSE WHERE public_id = %s', (public_id,))
                conn.commit()
                logger.debug(f"update user {public_id=} is_admin to False")
                name = user["name"] or ""
                surname = user["surname"] or ""
                nickname = user["nickname"] or ""
                return f"{name} {surname} {nickname}".strip()
            except Exception as e:
                conn.rollback()
                logger.exception(f"remove_user_from_admins failed: {e}")
                return None

    # ================= VIDEOS =================
    def add_video(
        self,
        file_id_480p: str = None,
        file_id_1080p: str = None,
        title: str = None,
        description: str = None,
        category: str = None,
        lesson_number: int = None,
        original_file_id: str = None,
        original_path: str = None,
        processing_status: str = "pending",
    ):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO videos (
                            file_id_480p, file_id_1080p, title, description, category,
                            lesson_number, original_file_id, original_path, processing_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        file_id_480p, file_id_1080p, title, description, category,
                        lesson_number, original_file_id, original_path, processing_status
                    ))
                conn.commit()
                logger.debug(f"add video {file_id_480p=}, {file_id_1080p=}, {title=}, {category=}, {lesson_number=}, {processing_status=}")
            except Exception as e:
                conn.rollback()
                logger.exception(f"add_video failed: {e}")
                raise

    def update_video_quality(self, video_id: int, file_id_480p: str = None, file_id_1080p: str = None, processing_status: str = None):
        updates = []
        values = []
        if file_id_480p is not None:
            updates.append("file_id_480p = %s")
            values.append(file_id_480p)
        if file_id_1080p is not None:
            updates.append("file_id_1080p = %s")
            values.append(file_id_1080p)
        if processing_status is not None:
            updates.append("processing_status = %s")
            values.append(processing_status)
        if not updates:
            return False
        values.append(video_id)
        
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE videos SET {', '.join(updates)} WHERE id = %s", values)
                conn.commit()
                logger.debug(f"update video quality {video_id=}, {file_id_480p=}, {file_id_1080p=}, {processing_status=}")
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_video_quality failed: {e}")
                return False

    def get_videos_by_category(self, category: str) -> list[dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE category = %s", (category,))
                return [dict(row) for row in cur.fetchall()]

    def get_all_videos(self) -> list[dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos ORDER BY category, lesson_number ASC")
                return [dict(row) for row in cur.fetchall()]

    def get_videos_by_category_ordered(self, category: str) -> list[dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE category = %s ORDER BY lesson_number ASC", (category,))
                return [dict(row) for row in cur.fetchall()]

    def get_next_lesson_number(self, category: str) -> int:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(lesson_number) FROM videos WHERE category = %s", (category,))
                row = cur.fetchone()
                max_lesson = row["max"] if row["max"] is not None else 0
                return max_lesson + 1

    def get_video_by_id(self, video_id: int) -> dict | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE id = %s", (video_id,))
                row = cur.fetchone()
                return dict(row) if row else None

    def delete_video(self, video_id: int) -> bool:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM videos WHERE id = %s", (video_id,))
                    if cur.rowcount == 0:
                        logger.warning(f"Attempted to delete non-existent video {video_id=}")
                        return False
                conn.commit()
                logger.debug(f"delete video {video_id=}")
                from video_processor import VideoProcessor
                VideoProcessor.delete_video_files_static(video_id)
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"delete_video failed: {e}")
                return False

    def update_video_metadata(self, video_id: int, title: str, description: str) -> bool:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE videos SET title = %s, description = %s WHERE id = %s", (title, description, video_id))
                    if cur.rowcount == 0:
                        logger.warning(f"Attempted to update non-existent video {video_id=}")
                        return False
                conn.commit()
                logger.debug(f"update video metadata {video_id=}, {title=}")
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_video_metadata failed: {e}")
                return False

    def get_all_categories(self) -> list[str]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT category FROM videos WHERE category IS NOT NULL ORDER BY category ASC")
                return [row["category"] for row in cur.fetchall()]

    def add_category(self, category_name: str) -> bool:
        try:
            self.add_video(
                file_id_480p="placeholder",
                file_id_1080p="placeholder",
                title=f"Категория {category_name}",
                description="",
                category=category_name,
                lesson_number=0,
                original_file_id="placeholder",
                processing_status="completed"
            )
            logger.debug(f"add category {category_name=}")
            return True
        except Exception as e:
            logger.error(f"Error adding category {category_name}: {e}")
            return False

    def delete_category(self, category_name: str) -> bool:
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM videos WHERE category = %s", (category_name,))
                    deleted = cur.rowcount
                conn.commit()
                logger.debug(f"delete category {category_name=}, deleted {deleted} videos")
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"delete_category failed: {e}")
                return False

    def category_exists(self, category_name: str) -> bool:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM videos WHERE category = %s LIMIT 1", (category_name,))
                return cur.fetchone() is not None

    def get_videos_by_quality(self, quality: str) -> list[dict]:
        field = "file_id_480p" if quality == "480p" else "file_id_1080p" if quality == "1080p" else None
        if not field:
            return []
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM videos WHERE {field} IS NOT NULL AND {field} != %s AND processing_status = %s', ("placeholder", "completed"))
                return [dict(row) for row in cur.fetchall()]

    def get_videos_pending_processing(self) -> list[dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE processing_status = 'pending'")
                return [dict(row) for row in cur.fetchall()]

    def get_video_file_id(self, video_id: int, quality: str) -> str | None:
        field = "file_id_480p" if quality == "480p" else "file_id_1080p" if quality == "1080p" else None
        if not field:
            return None
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT {field} FROM videos WHERE id = %s AND processing_status = 'completed'", (video_id,))
                row = cur.fetchone()
                if row and row[field] != "placeholder":
                    return row[field]
        return None

    def get_video_by_category_and_lesson(self, category: str, lesson_number: int) -> dict | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM videos WHERE category = %s AND lesson_number = %s", (category, lesson_number))
                row = cur.fetchone()
                return dict(row) if row else None

    def delete_videos_by_category_and_lesson(self, category: str, lesson_number: int, statuses: list[str] = None) -> int:
        if statuses is None:
            statuses = ['pending', 'failed']
        placeholders = ','.join(['%s'] * len(statuses))
        
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT id FROM videos WHERE category = %s AND lesson_number = %s AND processing_status IN ({placeholders})", (category, lesson_number, *statuses))
                    video_ids = [row["id"] for row in cur.fetchall()]
                    if video_ids:
                        cur.execute(f"DELETE FROM videos WHERE category = %s AND lesson_number = %s AND processing_status IN ({placeholders})", (category, lesson_number, *statuses))
                        deleted_count = cur.rowcount
                conn.commit()
                from video_processor import VideoProcessor
                for vid in video_ids:
                    VideoProcessor.delete_video_files_static(vid)
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} video(s) with category={category}, lesson_number={lesson_number}, statuses={statuses}")
                return deleted_count if video_ids else 0
            except Exception as e:
                conn.rollback()
                logger.exception(f"delete_videos_by_category_and_lesson failed: {e}")
                return 0

    # ================= TOURNAMENT =================
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
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM tournament WHERE date_time = %s AND address = %s", (date_time, address))
                    if cur.fetchone():
                        logger.debug(f"Trying to add existed tournament: {message_id=} {summary=} {date_time=}")
                        return False
                    cur.execute("""
                        INSERT INTO tournament (
                            tg_channel, message_id, city_id, summary, date_time,
                            address, registration, results_uploaded
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (tg_channel, message_id, city_id, summary, date_time, address, registration, results_uploaded))
                conn.commit()
                logger.debug(f"Insert into tournaments {message_id=} {date_time=} {address=}")
                return True
            except Exception as e:
                conn.rollback()
                logger.exception(f"add_tournament failed: {e}")
                return False

    def update_tournament(
        self,
        tg_channel: str,
        message_id: int,
        summary: str,
        date_time: datetime.datetime,
        city_id: int | None = None,
        address: str | None = None,
    ):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM tournament WHERE message_id = %s AND tg_channel = %s", (message_id, tg_channel))
                    if not cur.fetchone():
                        logger.debug(f"Trying to update non existent tournament: {message_id=} {summary=} {date_time=}")
                        self.add_tournament(tg_channel, message_id, summary, date_time, city_id, address)
                        return
                    cur.execute("""
                        UPDATE tournament SET summary = %s, date_time = %s, city_id = %s, address = %s
                        WHERE message_id = %s AND tg_channel = %s
                    """, (summary, date_time, city_id, address, message_id, tg_channel))
                conn.commit()
                logger.debug(f"Update tournament {tg_channel} {message_id=} {date_time=} {address=} ")
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_tournament failed: {e}")
                raise

    def get_tournaments(
        self,
        tg_channel: str,
        from_date: datetime.datetime,
        to_date: datetime.datetime | None = None,
        results_uploaded: bool | None = None
    ) -> list[dict]:
        query = "SELECT * FROM tournament WHERE date_time >= %s AND tg_channel = %s"
        values = [from_date, tg_channel]
        if to_date:
            query += " AND date_time <= %s"
            values.append(to_date)
        if results_uploaded is not None:
            query += " AND results_uploaded = %s"
            values.append(results_uploaded)
        query += " ORDER BY date_time"
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                return [dict(row) for row in cur.fetchall()]

    def remove_tournament(self, tg_channel: str, message_id: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM tournament WHERE tg_channel = %s AND message_id = %s", (tg_channel, message_id))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"remove_tournament failed: {e}")
                raise

    def open_registration(self, tournament_id: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE tournament SET registration = TRUE WHERE tournament_id = %s", (tournament_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"open_registration failed: {e}")
                raise

    def close_registration(self, tournament_id: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE tournament SET registration = FALSE WHERE tournament_id = %s", (tournament_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"close_registration failed: {e}")
                raise

    def results_uploaded(self, tournament_id: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE tournament SET results_uploaded = TRUE WHERE tournament_id = %s", (tournament_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"results_uploaded failed: {e}")
                raise

    def get_tournament_on_id(self, tournament_id: int) -> dict:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tournament WHERE tournament_id = %s", (tournament_id,))
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"Tournament with id {tournament_id} not found")
                return dict(row)

    # ================= CITY =================
    def add_city(self, tg_channel: str, name: str):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO city (name, tg_channel, timetable_message_id, timetable_photo)
                        VALUES (%s, %s, NULL, NULL)
                    """, (name, tg_channel))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"add_city failed: {e}")
                raise

    def get_photo_id(self, tg_channel: str) -> str | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT timetable_photo FROM city WHERE tg_channel = %s", (tg_channel,))
                row = cur.fetchone()
                return row["timetable_photo"] if row else None

    def get_city_on_id(self, city_id: int) -> str | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM city WHERE city_id = %s", (city_id,))
                row = cur.fetchone()
                return row["name"] if row else None

    def get_id_on_city_name(self, city: str) -> int | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT city_id FROM city WHERE name = %s", (city,))
                row = cur.fetchone()
                return row["city_id"] if row else None

    def get_cities_names(self) -> list[str]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM city")
                return [row["name"] for row in cur.fetchall()]

    def get_tg_channel_on_tg_id(self, telegram_id: int) -> str | None:
        user = self.get_user_on_telegram_id(telegram_id)
        if not user.get("city_id"):
            return None
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tg_channel FROM city WHERE city_id = %s", (user["city_id"],))
                row = cur.fetchone()
                return row["tg_channel"] if row else None

    def delete_city(self, city: str):
        city_id = self.get_id_on_city_name(city)
        if city_id is None:
            return
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE \"user\" SET city_id = 1 WHERE city_id = %s", (city_id,))
                    cur.execute("DELETE FROM city WHERE city_id = %s", (city_id,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"delete_city failed: {e}")
                raise

    def update_weakly_info(self, channel: str, message_id: str, photo_id: str):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE city SET timetable_message_id = %s, timetable_photo = %s WHERE tg_channel = %s
                    """, (message_id, photo_id, channel))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_weakly_info failed: {e}")
                raise

    # ================= USER_ON_TOURNAMENT =================
    def add_user_on_tournament(self, user_id: int, tournament_id: int, nickname: str, rating: int, k_factor: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM user_on_tournament WHERE user_id = %s AND tournament_id = %s", (user_id, tournament_id))
                    if cur.fetchone():
                        cur.execute("UPDATE user_on_tournament SET nickname = %s WHERE user_id = %s AND tournament_id = %s", (nickname, user_id, tournament_id))
                    else:
                        cur.execute("""
                            INSERT INTO user_on_tournament (
                                tournament_id, user_id, nickname, rating_before, rating_after,
                                place, score, k_factor
                            ) VALUES (%s, %s, %s, %s, NULL, NULL, NULL, %s)
                        """, (tournament_id, user_id, nickname, rating, k_factor))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"add_user_on_tournament failed: {e}")
                raise

    def get_registered_users(self, tournament_id: int) -> list[dict]:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_on_tournament WHERE tournament_id = %s", (tournament_id,))
                return [dict(row) for row in cur.fetchall()]

    def get_user_on_tournament_on_nickname(self, tournament_id: int, nickname: str) -> dict | None:
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM user_on_tournament WHERE tournament_id = %s AND nickname = %s", (tournament_id, nickname))
                row = cur.fetchone()
                return dict(row) if row else None

    def update_user_on_tournament(self, tournament_id: int, nickname: str, rating_after: int, place: int, score: int):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE user_on_tournament
                        SET rating_after = %s, place = %s, score = %s
                        WHERE tournament_id = %s AND nickname = %s
                    """, (rating_after, place, score, tournament_id, nickname))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"update_user_on_tournament failed: {e}")
                raise

    def get_tournaments_with_registration(self, from_date: datetime.datetime, results_uploaded: bool):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT t.*
                    FROM user_on_tournament uot
                    JOIN tournament t ON uot.tournament_id = t.tournament_id
                    WHERE t.date_time >= %s AND t.results_uploaded = %s
                """, (from_date, results_uploaded))
                return [dict(row) for row in cur.fetchall()]

    def delete_user_on_tournament(self, tournament_id: int, nickname: str):
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM user_on_tournament WHERE tournament_id = %s AND nickname = %s", (tournament_id, nickname))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"delete_user_on_tournament failed: {e}")
                raise

    # ================= GAME =================
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
        with self.get_connection() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO game (
                            tournament_id, white_user_id, black_user_id, round,
                            desk_number, result, white_rating_change, black_rating_change
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        tournament_id, white_user_id, black_user_id, round,
                        desk_number, result, white_rating_change, black_rating_change
                    ))
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.exception(f"add_game failed: {e}")
                raise

# our holy db instance
rep_chess_db = RepChessDB()