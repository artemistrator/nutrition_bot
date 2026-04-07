from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from config import get_settings

_DB: aiosqlite.Connection | None = None


async def _db() -> aiosqlite.Connection:
    global _DB
    if _DB is None or _DB._conn is None:
        path = get_settings().database_path
        _DB = await aiosqlite.connect(path)
        _DB.row_factory = aiosqlite.Row
        await _DB.execute("PRAGMA foreign_keys = ON;")
        await _DB.commit()
    return _DB


async def init_db(db_path: str | Path | None = None) -> None:
    path = Path(db_path or get_settings().database_path)
    async with aiosqlite.connect(path) as conn:
        await conn.execute("PRAGMA foreign_keys = ON;")
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                weight REAL,
                height REAL,
                goal_calories INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
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
        await conn.commit()


async def get_user(telegram_id: int) -> dict[str, Any] | None:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT telegram_id, username, weight, height, goal_calories, created_at
        FROM users
        WHERE telegram_id = ?;
        """,
        (telegram_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_all_users() -> list[dict[str, Any]]:
    db = await _db()
    cursor = await db.execute(
        """
        SELECT telegram_id, username, weight, height, goal_calories, created_at
        FROM users;
        """,
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


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
            telegram_id, username, weight, height, goal_calories
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        (telegram_id, username, weight, height, goal_calories),
    )
    await db.commit()
    user = await get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to create user.")
    return user


async def update_user_goal(telegram_id: int, goal_calories: int) -> None:
    db = await _db()
    await db.execute(
        "UPDATE users SET goal_calories = ? WHERE telegram_id = ?;",
        (goal_calories, telegram_id),
    )
    await db.commit()


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


def _sync_connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or get_settings().database_path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def sync_get_user(telegram_id: int) -> dict[str, Any] | None:
    conn = _sync_connect()
    try:
        cur = conn.execute(
            "SELECT telegram_id, username, weight, height, goal_calories, created_at FROM users WHERE telegram_id = ?;",
            (telegram_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def sync_update_user_goal(telegram_id: int, goal_calories: int) -> None:
    conn = _sync_connect()
    try:
        conn.execute(
            "UPDATE users SET goal_calories = ? WHERE telegram_id = ?;",
            (goal_calories, telegram_id),
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
            "INSERT OR IGNORE INTO users (telegram_id, username, weight, height, goal_calories) VALUES (?, ?, ?, ?, ?);",
            (telegram_id, username, weight, height, goal_calories),
        )
        conn.commit()
    finally:
        conn.close()
    user = sync_get_user(telegram_id)
    if user is None:
        raise RuntimeError("Failed to create user.")
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
