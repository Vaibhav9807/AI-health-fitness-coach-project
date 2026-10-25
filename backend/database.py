"""SQLAlchemy initialization plus a one-time import from the previous SQLite file."""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import Engine, event
from .extensions import db
from .models import User, UserProfile, WorkoutRecord, WeightRecord


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(connection, _record):
    if isinstance(connection, sqlite3.Connection):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _legacy_datetime(value):
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value)).replace(tzinfo=None)
    except ValueError:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def migrate_legacy_sqlite(old_path, new_path):
    """Copy old raw-SQL data without changing IDs or password hashes."""
    old_path, new_path = Path(old_path), Path(new_path)
    if not old_path.is_file() or old_path.resolve() == new_path.resolve():
        return 0
    connection = sqlite3.connect(old_path)
    connection.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "users" not in tables:
            return 0
        if User.query.first() is not None:
            return 0
        users = connection.execute("SELECT * FROM users ORDER BY id").fetchall()
        for row in users:
            user = User(id=row["id"], email=row["email"], password_hash=row["password_hash"], created_at=_legacy_datetime(row["created_at"]))
            db.session.add(user)
            if "user_profiles" in tables:
                p = connection.execute("SELECT * FROM user_profiles WHERE user_id=?", (row["id"],)).fetchone()
                if p:
                    db.session.add(UserProfile(user_id=row["id"], age=p["age"], height_cm=p["height_cm"], weight_kg=p["weight_kg"], sex=p["sex"], activity_level=p["activity_level"], goal=p["goal"], dietary_preference=p["dietary_preference"], experience=p["experience"], workout_minutes=p["workout_minutes"], restrictions=p["restrictions"]))
            if "workout_records" in tables:
                for w in connection.execute("SELECT * FROM workout_records WHERE user_id=?", (row["id"],)):
                    db.session.add(WorkoutRecord(id=w["id"], user_id=row["id"], exercise_type=w["exercise_type"], duration_minutes=w["duration_minutes"], exercise_date=w["exercise_date"], notes=w["notes"], created_at=_legacy_datetime(w["created_at"])))
            if "weight_records" in tables:
                for w in connection.execute("SELECT * FROM weight_records WHERE user_id=?", (row["id"],)):
                    db.session.add(WeightRecord(id=w["id"], user_id=row["id"], weight_kg=w["weight_kg"], record_date=w["record_date"]))
        db.session.commit()
        return len(users)
    except Exception:
        db.session.rollback()
        raise
    finally:
        connection.close()


def init_db(app):
    with app.app_context():
        db.create_all()
        try:
            with db.engine.begin() as conn:
                info = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
                col_names = [r[1] for r in info]
                if "full_name" not in col_names:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN full_name VARCHAR(120)")
        except Exception:
            pass
        old_path = app.config.get("LEGACY_DATABASE")
        new_path = app.config.get("DATABASE_FILE")
        if old_path and new_path:
            migrated = migrate_legacy_sqlite(old_path, new_path)
            if migrated:
                app.logger.info("Imported %s legacy account(s) into fitness.db.", migrated)
