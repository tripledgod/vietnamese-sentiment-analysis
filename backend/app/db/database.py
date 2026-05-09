"""
SQLite: classes, users, feedbacks theo ERD.
"""
import sqlite3
from contextlib import contextmanager

from app.core.config import DATABASE_PATH


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ).fetchone()
    return row is not None


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row[1] for row in cur.fetchall()}


def _users_table_sql(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    return (row[0] or "").lower() if row else ""


def _migrate_classes_if_needed(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "classes")
    if "class_name" in cols and "department" in cols:
        return
    if "code" not in cols and "name" not in cols:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE IF EXISTS classes")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT NOT NULL,
                department TEXT NOT NULL DEFAULT ''
            );
            """
        )
        return

    conn.executescript(
        """
        CREATE TABLE _classes_migrated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT NOT NULL,
            department TEXT NOT NULL DEFAULT ''
        );
        """
    )
    conn.execute(
        """
        INSERT INTO _classes_migrated (id, class_name, department)
        SELECT
            id,
            TRIM(CASE
                WHEN COALESCE(TRIM(name), '') != '' THEN name
                ELSE COALESCE(TRIM(code), '')
            END),
            ''
        FROM classes;
        """
    )
    conn.execute("DROP TABLE classes")
    conn.execute("ALTER TABLE _classes_migrated RENAME TO classes")


def _migrate_users_if_needed(conn: sqlite3.Connection) -> None:
    cols = _table_columns(conn, "users")
    create_sql = _users_table_sql(conn)
    need_rebuild = (
        "full_name" not in cols
        or "class_id" not in cols
        or "lecturer" in create_sql
    )
    if not need_rebuild:
        return

    full_sel = (
        "CASE WHEN TRIM(COALESCE(full_name, '')) != '' THEN TRIM(full_name) ELSE TRIM(username) END"
        if "full_name" in cols
        else "TRIM(username)"
    )
    class_sel = "class_id" if "class_id" in cols else "NULL"

    conn.executescript(
        """
        CREATE TABLE _users_migrated (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL CHECK(role IN ('student', 'teacher')),
            class_id INTEGER REFERENCES classes(id) ON DELETE SET NULL,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        """
    )
    conn.execute(
        f"""
        INSERT INTO _users_migrated (
            id, username, password_hash, full_name, role, class_id, must_change_password, created_at
        )
        SELECT
            id,
            username,
            password_hash,
            {full_sel},
            CASE
                WHEN role IN ('lecturer', 'teacher') THEN 'teacher'
                WHEN role = 'student' THEN 'student'
                ELSE 'student'
            END,
            {class_sel},
            must_change_password,
            created_at
        FROM users;
        """
    )
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE _users_migrated RENAME TO users")


CREATE_USERS_NEW = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL CHECK(role IN ('student', 'teacher')),
    class_id INTEGER REFERENCES classes(id) ON DELETE SET NULL,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

CREATE_FEEDBACKS = """
CREATE TABLE feedbacks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    label TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_feedbacks_user_id ON feedbacks(user_id);
CREATE INDEX IF NOT EXISTS idx_feedbacks_created_at ON feedbacks(created_at);
"""

CREATE_SEMESTERS = """
CREATE TABLE IF NOT EXISTS semesters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);
"""

CREATE_SUBJECTS = """
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT NOT NULL,
    subject_code TEXT NOT NULL DEFAULT ''
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_code ON subjects(subject_code);
"""

CREATE_SEMESTER_SUBJECTS = """
CREATE TABLE IF NOT EXISTS semester_subjects (
    semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    PRIMARY KEY (semester_id, subject_id)
);
"""

CREATE_SURVEY_CONFIGS = """
CREATE TABLE IF NOT EXISTS survey_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
    semester_id INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK(is_active IN (0, 1)),
    UNIQUE(class_id, semester_id, subject_id)
);
CREATE INDEX IF NOT EXISTS idx_survey_configs_class_sem ON survey_configs(class_id, semester_id);
CREATE INDEX IF NOT EXISTS idx_survey_configs_active ON survey_configs(class_id, is_active);
"""


def _ensure_survey_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(CREATE_SEMESTERS)
    conn.executescript(CREATE_SUBJECTS)
    conn.executescript(CREATE_SEMESTER_SUBJECTS)
    conn.executescript(CREATE_SURVEY_CONFIGS)


def _migrate_feedbacks_survey_config(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "feedbacks"):
        return
    cols = _table_columns(conn, "feedbacks")
    if "survey_config_id" in cols:
        return
    conn.execute(
        """
        ALTER TABLE feedbacks ADD COLUMN survey_config_id INTEGER
        REFERENCES survey_configs(id) ON DELETE SET NULL;
        """
    )


def _seed_survey_catalog_if_empty(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT COUNT(*) FROM semesters")
    if cur.fetchone()[0] > 0:
        return
    conn.execute(
        "INSERT INTO semesters (name) VALUES (?), (?)",
        ("Kỳ 1 - 2025-2026", "Kỳ 2 - 2025-2026"),
    )
    subs = [
        ("Lập trình Python", "CNTT301"),
        ("Cơ sở dữ liệu", "CNTT302"),
        ("Cấu trúc dữ liệu & Giải thuật", "CNTT303"),
        ("Mạng máy tính", "CNTT304"),
    ]
    for name, code in subs:
        conn.execute(
            "INSERT INTO subjects (subject_name, subject_code) VALUES (?, ?)",
            (name, code),
        )
    rows = conn.execute("SELECT id FROM semesters ORDER BY id").fetchall()
    sem1, sem2 = int(rows[0][0]), int(rows[1][0])
    sub_ids = [
        int(r[0])
        for r in conn.execute("SELECT id FROM subjects ORDER BY id").fetchall()
    ]
    for sid in sub_ids:
        conn.execute(
            "INSERT OR IGNORE INTO semester_subjects (semester_id, subject_id) VALUES (?, ?)",
            (sem1, sid),
        )
    for sid in sub_ids[:2]:
        conn.execute(
            "INSERT OR IGNORE INTO semester_subjects (semester_id, subject_id) VALUES (?, ?)",
            (sem2, sid),
        )


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        if not _table_exists(conn, "classes"):
            conn.execute(
                """
                CREATE TABLE classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_name TEXT NOT NULL,
                    department TEXT NOT NULL DEFAULT ''
                );
                """
            )
        else:
            _migrate_classes_if_needed(conn)

        if not _table_exists(conn, "users"):
            conn.executescript(CREATE_USERS_NEW)
        else:
            _migrate_users_if_needed(conn)

        if not _table_exists(conn, "feedbacks"):
            conn.executescript(CREATE_FEEDBACKS)

        if _table_exists(conn, "users"):
            conn.execute(
                "UPDATE users SET must_change_password = 0 WHERE role = 'teacher'"
            )

        _ensure_survey_tables(conn)
        _migrate_feedbacks_survey_config(conn)
        _seed_survey_catalog_if_empty(conn)

        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
