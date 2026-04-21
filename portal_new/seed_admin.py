import os
import sqlite3
from datetime import datetime
from getpass import getpass

from werkzeug.security import generate_password_hash


def get_db_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.environ.get("DATABASE_URL", os.path.join(base_dir, "..", "portal.db"))


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(get_db_path())


def user_exists(conn: sqlite3.Connection, email: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = ?", (email,))
    return cur.fetchone() is not None


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    full_name: str,
    role: str,
    client_id,
) -> None:
    cur = conn.cursor()
    password_hash = generate_password_hash(password)
    now = datetime.utcnow().isoformat(timespec="seconds")
    cur.execute(
        """
        INSERT INTO users (email, password_hash, full_name, role, client_id, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        """,
        (email, password_hash, full_name, role, client_id, now),
    )
    conn.commit()


def get_demo_user_seed():
    password = (os.environ.get("MORPHIQ_DEMO_PASSWORD") or "").strip()
    if not password:
        return None

    return {
        "email": (os.environ.get("MORPHIQ_DEMO_EMAIL") or "demo@example.invalid").strip(),
        "password": password,
        "full_name": (os.environ.get("MORPHIQ_DEMO_NAME") or "Demo Manager").strip(),
        "role": "manager",
        "client_id": 1,
    }


def main() -> None:
    print("Morph IQ Portal - Seed admin and demo users")
    conn = get_connection()
    try:
        admin_email = "admin@yourdomain.com"
        if user_exists(conn, admin_email):
            print(f"Admin user {admin_email} already exists - skipping.")
        else:
            admin_password = getpass(f"Enter password for admin user {admin_email}: ")
            if not admin_password:
                print("No password entered, skipping admin user creation.")
            else:
                create_user(
                    conn,
                    email=admin_email,
                    password=admin_password,
                    full_name="Admin",
                    role="admin",
                    client_id=None,
                )
                print(f"Admin user created: {admin_email}")

        demo_user = get_demo_user_seed()
        if demo_user is None:
            print("No MORPHIQ_DEMO_PASSWORD set; skipping demo user creation.")
        elif user_exists(conn, demo_user["email"]):
            print(f"Demo manager user {demo_user['email']} already exists - skipping.")
        else:
            create_user(
                conn,
                email=demo_user["email"],
                password=demo_user["password"],
                full_name=demo_user["full_name"],
                role=demo_user["role"],
                client_id=demo_user["client_id"],
            )
            print(
                "Demo manager user created:\n"
                f"  Email: {demo_user['email']}\n"
                "  Password: supplied via MORPHIQ_DEMO_PASSWORD\n"
                f"  Role: {demo_user['role']} (client_id={demo_user['client_id']})"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
