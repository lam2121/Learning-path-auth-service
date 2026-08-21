"""Migration script to copy existing TOEIC users into Central Auth DB (auth_db.users).

Quy tắc role:
  - 'admin'    : quản trị viên (role == 'admin' hoặc role_id == 2)
  - 'employee' : mọi giá trị còn lại (student, teacher, learner,…)

Usage:
    cd auth-service
    venv/bin/python3 migrate_toeic_users.py --toeic-db toeic_learningpath
"""

import argparse
import pymysql
from app.core.config import app_config

_VALID_ROLES = {"admin", "employee"}


def _normalize_role(value) -> str:
    """Chuẩn hóa role: chỉ 'admin' hoặc 'employee'.

    Args:
        value: Có thể là string ('admin', 'student', 'teacher', 'learner', …)
               hoặc int (role_id từ bảng CareerPath: 2 = admin, khác = employee).
    """
    if isinstance(value, int):
        return "admin" if value == 2 else "employee"
    if isinstance(value, str) and value.strip().lower() in _VALID_ROLES:
        return value.strip().lower()
    return "employee"


def migrate_users(toeic_db_name: str = "toeic"):
    print(f"=== MIGRATING USERS FROM '{toeic_db_name}' TO 'auth_db' ===")

    conn = pymysql.connect(
        host=app_config.MYSQL_HOST,
        user=app_config.MYSQL_USER,
        password=app_config.MYSQL_PASSWORD,
        port=app_config.MYSQL_PORT,
        charset="utf8mb4",
    )

    try:
        with conn.cursor() as cur:
            cur.execute(f"USE `{toeic_db_name}`")
            cur.execute("SHOW TABLES;")
            tables = [row[0] for row in cur.fetchall()]

            users_data = []
            if "toeicapp_user" in tables:
                print("Detected 'toeicapp_user' table (TOEIC Web)...")
                cur.execute("SELECT id, username, email, password, full_name, role, is_active, date_joined FROM `toeicapp_user`")
                for r in cur.fetchall():
                    uid, uname, email, pwd, fname, role, is_act, created = r
                    # toeicapp_user.role: 'admin' | 'student' | 'teacher' → chuẩn hóa
                    users_data.append((uid, uname, email, pwd, fname, _normalize_role(role), is_act, created))
            elif "user" in tables:
                print("Detected 'user' table (CareerPath / LearningPath)...")
                cur.execute("SELECT id, name, email, hashed_password, role_id, created_at FROM `user`")
                for r in cur.fetchall():
                    uid, name, email, pwd, role_id, created = r
                    # role_id: 2 = admin, 1 (hoặc khác) = employee
                    uname = email.split("@")[0] if email else f"user_{uid}"
                    users_data.append((uid, uname, email, pwd, name, _normalize_role(role_id), 1, created))
            elif "auth_user" in tables:
                print("Detected 'auth_user' table (Django default)...")
                cur.execute("SELECT id, username, email, password, first_name, last_name, is_active, date_joined FROM `auth_user`")
                for r in cur.fetchall():
                    uid, uname, email, pwd, fname, lname, is_act, created = r
                    full_name = f"{fname} {lname}".strip() or None
                    # Django auth_user không có role → mặc định employee
                    users_data.append((uid, uname, email, pwd, full_name, "employee", is_act, created))
            else:
                print(f"❌ No recognized user table found in '{toeic_db_name}'. Available tables: {tables}")
                return

            print(f"Found {len(users_data)} users in source DB '{toeic_db_name}'.")

            # Insert into auth_db.users
            cur.execute("USE `auth_db`")
            migrated_count = 0
            skipped_count = 0

            for user in users_data:
                uid, uname, email, pwd, fname, role, is_act, created = user
                
                # Check duplicate by email or username
                cur.execute("SELECT id FROM `users` WHERE email = %s OR username = %s", (email, uname))
                if cur.fetchone():
                    skipped_count += 1
                    continue

                cur.execute(
                    """
                    INSERT INTO `users` (username, email, hashed_password, full_name, role, is_active, is_verified, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                    """,
                    (uname, email, pwd or "", fname, role, is_act, created),
                )
                migrated_count += 1

            conn.commit()
            print(f"✅ Migration completed: {migrated_count} users migrated, {skipped_count} users skipped (already existed).")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--toeic-db", default="toeic", help="Source database name ('toeic' or 'toeic_learningpath')")
    args = parser.parse_args()
    migrate_users(args.toeic_db)
