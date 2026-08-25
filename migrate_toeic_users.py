"""Migration script to merge users from TOEIC (Django/FastAPI) and CareerPath (toeic_learningpath)
into the Central Auth DB (auth_db.users).

Quy tắc chuẩn hóa:
  - Role:
      'admin'    : khi role == 'admin' hoặc role_id == 2 hoặc is_superuser == 1
      'employee' : mọi giá trị còn lại (student, teacher, learner,…)
  - Email: Làm sạch whitespace, chuyển về chữ thường.
  - Tránh trùng lặp (Idempotent): Bỏ qua nếu email hoặc username đã tồn tại trong auth_db.users.
  - Giữ nguyên mật khẩu đã băm (hỗ trợ cả bcrypt và Django pbkdf2_sha256).

Usage:
    cd auth-service
    venv/Scripts/python.exe migrate_toeic_users.py --all
"""

import argparse
import pymysql
from app.core.config import app_config

_VALID_ROLES = {"admin", "employee"}


def _normalize_role(value) -> str:
    """Chuẩn hóa role: chỉ 'admin' hoặc 'employee'."""
    if isinstance(value, int):
        return "admin" if value == 2 else "employee"
    if isinstance(value, str) and value.strip().lower() in _VALID_ROLES:
        return value.strip().lower()
    return "employee"


def migrate_single_db(cur, source_db_name: str) -> tuple[int, int]:
    """Migrate users from a specific database into auth_db."""
    print(f"\n--- Checking source database '{source_db_name}' ---")
    
    # Check if DB exists
    cur.execute("SHOW DATABASES LIKE %s;", (source_db_name,))
    if not cur.fetchone():
        print(f"⚠️  Database '{source_db_name}' does not exist on this MySQL server. Skipping.")
        return 0, 0

    cur.execute(f"USE `{source_db_name}`")
    cur.execute("SHOW TABLES;")
    tables = [row[0] for row in cur.fetchall()]

    users_data = []
    
    # Case 1: Custom TOEIC App User (Django custom user model)
    if "toeicapp_user" in tables:
        print(f"  -> Found 'toeicapp_user' table in '{source_db_name}'")
        cur.execute("SELECT id, username, email, password, full_name, role, is_active, date_joined FROM `toeicapp_user`")
        for r in cur.fetchall():
            uid, uname, email, pwd, fname, role, is_act, created = r
            if email:
                users_data.append((uid, uname, email.strip().lower(), pwd, fname, _normalize_role(role), is_act, created))

    # Case 2: Standard Django auth_user
    elif "auth_user" in tables:
        print(f"  -> Found 'auth_user' table in '{source_db_name}'")
        cur.execute("SELECT id, username, email, password, first_name, last_name, is_active, is_superuser, date_joined FROM `auth_user`")
        for r in cur.fetchall():
            uid, uname, email, pwd, fname, lname, is_act, is_super, created = r
            full_name = f"{fname} {lname}".strip() or None
            role = "admin" if is_super else "employee"
            if email:
                users_data.append((uid, uname, email.strip().lower(), pwd, full_name, role, is_act, created))

    # Case 3: CareerPath user table (toeic_learningpath.user)
    if "user" in tables:
        print(f"  -> Found 'user' table (CareerPath) in '{source_db_name}'")
        cur.execute("SELECT id, name, email, hashed_password, role_id, created_at FROM `user`")
        for r in cur.fetchall():
            uid, name, email, pwd, role_id, created = r
            if email:
                uname = email.split("@")[0]
                users_data.append((uid, uname, email.strip().lower(), pwd, name, _normalize_role(role_id), 1, created))

    if not users_data:
        print(f"  -> No user records found in '{source_db_name}'.")
        return 0, 0

    print(f"  -> Found {len(users_data)} users to process from '{source_db_name}'.")

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

    return migrated_count, skipped_count


def migrate_all_users(databases: list[str]):
    print("==================================================================")
    print("      MERGING USERS INTO CENTRAL AUTH DB (auth_db.users)          ")
    print("==================================================================")

    conn = pymysql.connect(
        host=app_config.MYSQL_HOST,
        user=app_config.MYSQL_USER,
        password=app_config.MYSQL_PASSWORD,
        port=app_config.MYSQL_PORT,
        charset="utf8mb4",
    )

    try:
        total_migrated = 0
        total_skipped = 0

        with conn.cursor() as cur:
            for db_name in databases:
                migrated, skipped = migrate_single_db(cur, db_name)
                total_migrated += migrated
                total_skipped += skipped
            
            conn.commit()

        print("\n==================================================================")
        print(f"✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print(f"   • Total new users merged: {total_migrated}")
        print(f"   • Total skipped (already existed): {total_skipped}")
        print("==================================================================")

    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge TOEIC & CareerPath users into auth_db")
    parser.add_argument("--all", action="store_true", default=True, help="Migrate from both 'toeic' and 'toeic_learningpath'")
    parser.add_argument("--db", type=str, help="Specific DB to migrate from (e.g. 'toeic' or 'toeic_learningpath')")
    args = parser.parse_args()

    if args.db:
        target_dbs = [args.db]
    else:
        target_dbs = ["toeic", "toeic_learningpath"]

    migrate_all_users(target_dbs)
