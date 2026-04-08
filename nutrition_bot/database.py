from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from config import get_settings
from services.profile import build_profile_meta, calculate_goal_calories, is_profile_complete, sanitize_profile_input

_DB: aiosqlite.Connection | None = None

_USER_SELECT = """
    SELECT
        telegram_id,
        username,
        sex,
        age,
        height_cm,
        weight_kg,
        activity_level,
        goal_type,
        goal_calories,
        updated_at,
        created_at
    FROM users
"""


def _now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def _ensure_schema_async(conn: aiosqlite.Connection) -> None:
    await conn.execute("PRAGMA foreign_keys = ON;")
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            weight REAL,
            height REAL,
            goal_calories INTEGER,
            sex TEXT,
            age INTEGER,
            height_cm REAL,
            weight_kg REAL,
            activity_level TEXT,
            goal_type TEXT,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cursor = await conn.execute("PRAGMA table_info(users);")
    columns = {row["name"] for row in await cursor.fetchall()}
    for statement in _missing_user_column_statements(columns):
        await conn.execute(statement)

    await conn.execute(
        """
        UPDATE users
        SET
            weight_kg = COALESCE(weight_kg, weight),
            height_cm = COALESCE(height_cm, height),
            updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
        ;
        """
    )

    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            calories REAL NOT NULL DEFAULT 0,
            protein REAL NOT NULL DEFAULT 0,
            fat REAL NOT NULL DEFAULT 0,
            carbs REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            calories_burned REAL NOT NULL DEFAULT 0,
            duration_minutes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            structure_json TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            notif_type TEXT NOT NULL,
            sent_date TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        );
        """
    )
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profile_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL,
            sex TEXT,
            age INTEGER,
            height_cm REAL,
            weight_kg REAL,
            activity_level TEXT,
            goal_type TEXT,
            goal_calories INTEGER,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
        );
        """
    )
    await conn.commit()


def _missing_user_column_statements(columns: set[str]) -> list[str]:
    statements: list[str] = []
    required = {
        "sex": "ALTER TABLE users ADD COLUMN sex TEXT;",
        "age": "ALTER TABLE users ADD COLUMN age INTEGER;",
        "height_cm": "ALTER TABLE users ADD COLUMN height_cm REAL;",
        "weight_kg": "ALTER TABLE users ADD COLUMN weight_kg REAL;",
        "activity_level": "ALTER TABLE users ADD COLUMN activity_level TEXT;",
        "goal_type": "ALTER TABLE users ADD COLUMN goal_type TEXT;",
        "updated_at": "ALTER TABLE users ADD COLUMN updated_at TEXT;",
        "weight": "ALTER TABLE users ADD COLUMN weight REAL;",
        "height": "ALTER TABLE users ADD COLUMN height REAL;",
    }
    for column, statement in required.items():
        if column not in columns:
            statements.append(statement)
    return statements


async def _db() -> aiosqlite.Connection:
    global _DB
    if _DB is None or _DB._conn is None:
        path = get_settings().database_path
        _DB = await aiosqlite.connect(path)
        _DB.row_factory = aiosqlite.Row
        await _ensure_schema_async(_DB)
    return _DB


async def init_db(db_path: str | Path | None = None) -> None:
    path = Path(db_path or get_settings().database_path)
    async with aiosqlite.connect(path) as conn:
        conn.row_factory = aiosqlite.Row
        await _ensure_schema_async(conn)


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    db = await _db()
    cursor = await db.execute(
        f"{_USER_SELECT} WHERE telegram_id = ?;",
        (telegram_id,),
    )
    row = await cursor.fetchone()
    return build_profile_meta(dict(row)) if row else None


async def get_all_users() -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        f"{_USER_SELECT};",
    )
    rows = await cursor.fetchall()
    return [build_profile_meta(dict(row)) for row in rows]


async def create_user(
    telegram_id: int,
    username: str | None = None,
    weight: float | None = None,
    height: float | None = None,
    goal_calories: int | None = None,
) -> dict[str, Any]:
    db = await _db()
    await db.execute(
        """
        INSERT OR IGNORE INTO users (
            telegram_id, username, weight, height, weight_kg, height_cm, goal_calories, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (telegram_id, username, weight, height, weight, height, goal_calories, _now_timestamp()),
    )
    await db.commit()
    user = await get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to create user.")
    return user


async def update_user_goal(telegram_id: int, goal_calories: int) -> None:
    db = await _db()
    await db.execute(
        "UPDATE users SET goal_calories = ?, updated_at = ? WHERE telegram_id = ?;",
        (goal_calories, _now_timestamp(), telegram_id),
    )
    await db.commit()


async def get_user_profile(telegram_id: int) -> dict[str, Any] | None:
    return await get_user(telegram_id)


async def update_user_profile(telegram_id: int, profile_data: dict[str, Any]) -> dict[str, Any]:
    db = await _db()
    existing = await get_user(telegram_id)
    if existing is None:
        raise ValueError("User not found.")

    cleaned = sanitize_profile_input(profile_data, partial=True)
    merged = {**existing, **cleaned}
    goal_calories = merged.get("goal_calories")
    if is_profile_complete(merged):
        goal_calories = calculate_goal_calories(merged)

    merged["goal_calories"] = goal_calories
    merged["updated_at"] = _now_timestamp()

    await db.execute(
        """
        UPDATE users
        SET
            username = COALESCE(?, username),
            sex = ?,
            age = ?,
            height_cm = ?,
            weight_kg = ?,
            activity_level = ?,
            goal_type = ?,
            goal_calories = ?,
            weight = ?,
            height = ?,
            updated_at = ?
        WHERE telegram_id = ?;
        """,
        (
            merged.get("username"),
            merged.get("sex"),
            merged.get("age"),
            merged.get("height_cm"),
            merged.get("weight_kg"),
            merged.get("activity_level"),
            merged.get("goal_type"),
            merged.get("goal_calories"),
            merged.get("weight_kg"),
            merged.get("height_cm"),
            merged.get("updated_at"),
            telegram_id,
        ),
    )
    await db.execute(
        """
        INSERT INTO user_profile_history (
            telegram_user_id,
            sex,
            age,
            height_cm,
            weight_kg,
            activity_level,
            goal_type,
            goal_calories,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            telegram_id,
            merged.get("sex"),
            merged.get("age"),
            merged.get("height_cm"),
            merged.get("weight_kg"),
            merged.get("activity_level"),
            merged.get("goal_type"),
            merged.get("goal_calories"),
            merged.get("updated_at"),
        ),
    )
    await db.commit()
    user = await get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to update profile.")
    return user


async def add_meal(
    user_id: int,
    description: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> int:
    db = await _db()
    cursor = await db.execute(
        """
        INSERT INTO meals (user_id, description, calories, protein, fat, carbs)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (user_id, description, calories, protein, fat, carbs),
    )
    await db.commit()
    meal_id = cursor.lastrowid
    if meal_id is None:
        raise RuntimeError("Failed to create meal.")
    return meal_id


async def get_today_meals(user_id: int) -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT id, user_id, description, calories, protein, fat, carbs, created_at
        FROM meals
        WHERE user_id = ?
          AND date(created_at, 'localtime') = date('now', 'localtime')
        ORDER BY created_at ASC, id ASC;
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_meal_by_id(meal_id: int, telegram_user_id: int) -> dict[str, Any] | None:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT id, user_id, description, calories, protein, fat, carbs, created_at
        FROM meals
        WHERE id = ? AND user_id = ?;
        """,
        (meal_id, telegram_user_id),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_meal(
    meal_id: int,
    telegram_user_id: int,
    description: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> dict[str, Any] | None:
    db = await _db()
    cursor = await db.execute(
        """
        UPDATE meals
        SET description = ?, calories = ?, protein = ?, fat = ?, carbs = ?
        WHERE id = ? AND user_id = ?;
        """,
        (description, calories, protein, fat, carbs, meal_id, telegram_user_id),
    )
    await db.commit()
    if cursor.rowcount <= 0:
        return None
    return await get_meal_by_id(meal_id, telegram_user_id)


async def delete_meal(meal_id: int, telegram_user_id: int) -> bool:
    db = await _db()
    cursor = await db.execute(
        "DELETE FROM meals WHERE id = ? AND user_id = ?;",
        (meal_id, telegram_user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def add_activity(
    user_id: int,
    description: str,
    calories_burned: float,
    duration_minutes: int | None = None,
) -> int:
    db = await _db()
    cursor = await db.execute(
        """
        INSERT INTO activities (user_id, description, calories_burned, duration_minutes)
        VALUES (?, ?, ?, ?);
        """,
        (user_id, description, calories_burned, duration_minutes),
    )
    await db.commit()
    activity_id = cursor.lastrowid
    if activity_id is None:
        raise RuntimeError("Failed to create activity.")
    return activity_id


async def get_today_activities(user_id: int) -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT id, user_id, description, calories_burned, duration_minutes, created_at
        FROM activities
        WHERE user_id = ?
          AND date(created_at, 'localtime') = date('now', 'localtime')
        ORDER BY created_at ASC, id ASC;
        """,
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_activities_history(user_id: int, days: int) -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT date(created_at, 'localtime') as date,
               SUM(calories_burned) as calories_burned
        FROM activities
        WHERE user_id = ?
          AND date(created_at, 'localtime') >= date('now', 'localtime', ?)
        GROUP BY date
        ORDER BY date DESC;
        """,
        (user_id, f"-{days} days"),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


# --- Meal templates ---

import json as _json


async def create_meal_template(
    telegram_user_id: int,
    title: str,
    structure: dict,
) -> int:
    db = await _db()
    cursor = await db.execute(
        """
        INSERT INTO meal_templates (telegram_user_id, title, structure_json)
        VALUES (?, ?, ?);
        """,
        (telegram_user_id, title, _json.dumps(structure, ensure_ascii=False)),
    )
    await db.commit()
    return cursor.lastrowid


async def list_meal_templates(telegram_user_id: int) -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT id, telegram_user_id, title, structure_json, created_at
        FROM meal_templates
        WHERE telegram_user_id = ?
        ORDER BY created_at DESC;
        """,
        (telegram_user_id,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_meal_template(template_id: int, telegram_user_id: int) -> dict[str, Any] | None:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT id, telegram_user_id, title, structure_json, created_at
        FROM meal_templates
        WHERE id = ? AND telegram_user_id = ?;
        """,
        (template_id, telegram_user_id),
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    result = dict(row)
    # Parse JSON
    try:
        result["structure"] = _json.loads(result["structure_json"])
    except _json.JSONDecodeError:
        result["structure"] = None
    return result


async def delete_meal_template(template_id: int, telegram_user_id: int) -> bool:
    db = await _db()
    cursor = await db.execute(
        "DELETE FROM meal_templates WHERE id = ? AND telegram_user_id = ?;",
        (template_id, telegram_user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


# --- Notification log ---

async def get_today_totals(user_id: int) -> dict[str, Any]:
    """Возвращает агрегированные totals за сегодня + meals_count."""
    db = await _db()
    cursor = await db.execute(
        """
        SELECT SUM(calories) as calories,
               SUM(protein) as protein,
               SUM(fat) as fat,
               SUM(carbs) as carbs,
               COUNT(*) as meals_count
        FROM meals
        WHERE user_id = ?
          AND date(created_at, 'localtime') = date('now', 'localtime');
        """,
        (user_id,),
    )
    row = await cursor.fetchone()
    if row is None or row["meals_count"] == 0:
        return {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "meals_count": 0}
    return {
        "calories": row["calories"] or 0,
        "protein": row["protein"] or 0,
        "fat": row["fat"] or 0,
        "carbs": row["carbs"] or 0,
        "meals_count": row["meals_count"],
    }


async def get_user_goal_calories(telegram_id: int) -> int | None:
    user = await get_user(telegram_id)
    if user is None:
        return None
    return user.get("goal_calories")


async def get_users_for_notifications() -> list[dict[str, Any]]:
    """Возвращает всех пользователей с telegram_id и goal_calories."""
    return await get_all_users()


async def has_sent_notification_today(user_id: int) -> bool:
    """Проверяет, отправляли ли уже уведомление сегодня."""
    today = datetime.now().strftime("%Y-%m-%d")
    db = await _db()
    cursor = await db.execute(
        "SELECT id FROM notification_log WHERE telegram_user_id = ? AND sent_date = ? LIMIT 1;",
        (user_id, today),
    )
    row = await cursor.fetchone()
    return row is not None


async def log_notification(user_id: int, notif_type: str) -> None:
    """Логирует отправку уведомления."""
    today = datetime.now().strftime("%Y-%m-%d")
    db = await _db()
    await db.execute(
        "INSERT INTO notification_log (telegram_user_id, notif_type, sent_date) VALUES (?, ?, ?);",
        (user_id, notif_type, today),
    )
    await db.commit()


# --- Sync helpers for FastAPI ---

import sqlite3


def ensure_db_schema_sync(db_path: str | Path | None = None) -> None:
    conn = _sync_connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                weight REAL,
                height REAL,
                goal_calories INTEGER,
                sex TEXT,
                age INTEGER,
                height_cm REAL,
                weight_kg REAL,
                activity_level TEXT,
                goal_type TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users);").fetchall()}
        for statement in _missing_user_column_statements(columns):
            conn.execute(statement)
        conn.execute(
            """
            UPDATE users
            SET
                weight_kg = COALESCE(weight_kg, weight),
                height_cm = COALESCE(height_cm, height),
                updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            ;
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                calories REAL NOT NULL DEFAULT 0,
                protein REAL NOT NULL DEFAULT 0,
                fat REAL NOT NULL DEFAULT 0,
                carbs REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                calories_burned REAL NOT NULL DEFAULT 0,
                duration_minutes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meal_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                structure_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                notif_type TEXT NOT NULL,
                sent_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                sex TEXT,
                age INTEGER,
                height_cm REAL,
                weight_kg REAL,
                activity_level TEXT,
                goal_type TEXT,
                goal_calories INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_user_id) REFERENCES users (telegram_id) ON DELETE CASCADE
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _sync_connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or get_settings().database_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def sync_get_user(telegram_id: int) -> dict[str, Any] | None:
    conn = _sync_connect()
    try:
        cur = conn.execute(f"{_USER_SELECT} WHERE telegram_id = ?;", (telegram_id,))
        row = cur.fetchone()
        return build_profile_meta(dict(row)) if row else None
    finally:
        conn.close()


def sync_update_user_goal(telegram_id: int, goal_calories: int) -> None:
    conn = _sync_connect()
    try:
        conn.execute(
            "UPDATE users SET goal_calories = ?, updated_at = ? WHERE telegram_id = ?;",
            (goal_calories, _now_timestamp(), telegram_id),
        )
        conn.commit()
    finally:
        conn.close()


def sync_create_user(
    telegram_id: int,
    username: str | None = None,
    weight: float | None = None,
    height: float | None = None,
    goal_calories: int | None = None,
) -> dict[str, Any]:
    conn = _sync_connect()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (
                telegram_id,
                username,
                weight,
                height,
                weight_kg,
                height_cm,
                goal_calories,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (telegram_id, username, weight, height, weight, height, goal_calories, _now_timestamp()),
        )
        conn.commit()
    finally:
        conn.close()
    user = sync_get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to create user.")
    return user


def sync_get_user_profile(telegram_id: int) -> dict[str, Any] | None:
    return sync_get_user(telegram_id)


def sync_update_user_profile(telegram_id: int, profile_data: dict[str, Any]) -> dict[str, Any]:
    conn = _sync_connect()
    try:
        cur = conn.execute(f"{_USER_SELECT} WHERE telegram_id = ?;", (telegram_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError("User not found.")

        existing = build_profile_meta(dict(row))
        cleaned = sanitize_profile_input(profile_data, partial=True)
        merged = {**existing, **cleaned}
        goal_calories = merged.get("goal_calories")
        if is_profile_complete(merged):
            goal_calories = calculate_goal_calories(merged)

        merged["goal_calories"] = goal_calories
        merged["updated_at"] = _now_timestamp()

        conn.execute(
            """
            UPDATE users
            SET
                username = COALESCE(?, username),
                sex = ?,
                age = ?,
                height_cm = ?,
                weight_kg = ?,
                activity_level = ?,
                goal_type = ?,
                goal_calories = ?,
                weight = ?,
                height = ?,
                updated_at = ?
            WHERE telegram_id = ?;
            """,
            (
                merged.get("username"),
                merged.get("sex"),
                merged.get("age"),
                merged.get("height_cm"),
                merged.get("weight_kg"),
                merged.get("activity_level"),
                merged.get("goal_type"),
                merged.get("goal_calories"),
                merged.get("weight_kg"),
                merged.get("height_cm"),
                merged.get("updated_at"),
                telegram_id,
            ),
        )
        conn.execute(
            """
            INSERT INTO user_profile_history (
                telegram_user_id,
                sex,
                age,
                height_cm,
                weight_kg,
                activity_level,
                goal_type,
                goal_calories,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                telegram_id,
                merged.get("sex"),
                merged.get("age"),
                merged.get("height_cm"),
                merged.get("weight_kg"),
                merged.get("activity_level"),
                merged.get("goal_type"),
                merged.get("goal_calories"),
                merged.get("updated_at"),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    user = sync_get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to update profile.")
    return user


def sync_add_meal(
    user_id: int,
    description: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> int:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            "INSERT INTO meals (user_id, description, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?);",
            (user_id, description, calories, protein, fat, carbs),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def sync_get_today_meals(user_id: int) -> list[dict[str, Any]]:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, description, calories, protein, fat, carbs, created_at
            FROM meals
            WHERE user_id = ?
              AND date(created_at, 'localtime') = date('now', 'localtime')
            ORDER BY created_at ASC, id ASC;
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def sync_get_meal_by_id(meal_id: int, telegram_user_id: int) -> dict[str, Any] | None:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, description, calories, protein, fat, carbs, created_at
            FROM meals
            WHERE id = ? AND user_id = ?;
            """,
            (meal_id, telegram_user_id),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def sync_update_meal(
    meal_id: int,
    telegram_user_id: int,
    description: str,
    calories: float,
    protein: float,
    fat: float,
    carbs: float,
) -> dict[str, Any] | None:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            UPDATE meals
            SET description = ?, calories = ?, protein = ?, fat = ?, carbs = ?
            WHERE id = ? AND user_id = ?;
            """,
            (description, calories, protein, fat, carbs, meal_id, telegram_user_id),
        )
        conn.commit()
        if cur.rowcount <= 0:
            return None
    finally:
        conn.close()
    return sync_get_meal_by_id(meal_id, telegram_user_id)


def sync_delete_meal(meal_id: int, telegram_user_id: int) -> bool:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            "DELETE FROM meals WHERE id = ? AND user_id = ?;",
            (meal_id, telegram_user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def sync_get_meals_history(user_id: int, days: int) -> list[dict[str, Any]]:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            SELECT date(created_at, 'localtime') as date,
                   SUM(calories) as calories,
                   SUM(protein) as protein,
                   SUM(fat) as fat,
                   SUM(carbs) as carbs
            FROM meals
            WHERE user_id = ?
              AND date(created_at, 'localtime') >= date('now', 'localtime', ?)
            GROUP BY date
            ORDER BY date DESC;
            """,
            (user_id, f"-{days} days"),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def sync_add_activity(
    user_id: int,
    description: str,
    calories_burned: float,
    duration_minutes: int | None = None,
) -> int:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            "INSERT INTO activities (user_id, description, calories_burned, duration_minutes) VALUES (?, ?, ?, ?);",
            (user_id, description, calories_burned, duration_minutes),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def sync_get_today_activities(user_id: int) -> list[dict[str, Any]]:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            SELECT id, user_id, description, calories_burned, duration_minutes, created_at
            FROM activities
            WHERE user_id = ?
              AND date(created_at, 'localtime') = date('now', 'localtime')
            ORDER BY created_at ASC, id ASC;
            """,
            (user_id,),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def sync_get_activities_history(user_id: int, days: int) -> list[dict[str, Any]]:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            """
            SELECT date(created_at, 'localtime') as date,
                   SUM(calories_burned) as calories_burned
            FROM activities
            WHERE user_id = ?
              AND date(created_at, 'localtime') >= date('now', 'localtime', ?)
            GROUP BY date
            ORDER BY date DESC;
            """,
            (user_id, f"-{days} days"),
        )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
