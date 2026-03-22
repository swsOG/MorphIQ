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


def main() -> None:
    print("Morph IQ Portal — Seed admin and demo users")
    conn = get_connection()
    try:
        # Admin user
        admin_email = "filip@morphiq.co.uk"
        if user_exists(conn, admin_email):
            print(f"Admin user {admin_email} already exists — skipping.")
        else:
            admin_password = getpass(
                f"Enter password for admin user {admin_email}: "
            )
            if not admin_password:
                print("No password entered, skipping admin user creation.")
            else:
                create_user(
                    conn,
                    email=admin_email,
                    password=admin_password,
                    full_name="Filip",
                    role="admin",
                    client_id=None,
                )
                print(f"Admin user created: {admin_email}")

        # Demo manager user
        demo_email = "demo@agency.co.uk"
        demo_password = "demo123"
        if user_exists(conn, demo_email):
            print(f"Demo manager user {demo_email} already exists — skipping.")
        else:
            create_user(
                conn,
                email=demo_email,
                password=demo_password,
                full_name="Demo Manager",
                role="manager",
                client_id=1,
            )
            print(
                "Demo manager user created:\n"
                f"  Email: {demo_email}\n"
                f"  Password: {demo_password}\n"
                "  Role: manager (client_id=1)"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    main()

