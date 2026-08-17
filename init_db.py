import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"
MIGRATIONS_DIR = BASE_DIR / "database" / "migrations"


def clean_sql(sql_text):
    """Remove full-line SQL comments and return executable statements."""
    lines = []
    for line in sql_text.splitlines():
        if not line.strip().startswith("--"):
            lines.append(line)

    return [statement.strip() for statement in "\n".join(lines).split(";") if statement.strip()]


def apply_migrations(connection, cursor):
    """Apply each SQL migration exactly once."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_name VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB
        """
    )

    if not MIGRATIONS_DIR.exists():
        return 0

    applied_count = 0
    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        cursor.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_name = %s",
            (migration_file.name,),
        )
        if cursor.fetchone():
            continue

        for statement in clean_sql(migration_file.read_text(encoding="utf-8")):
            cursor.execute(statement)

        cursor.execute(
            "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
            (migration_file.name,),
        )
        connection.commit()
        applied_count += 1

    return applied_count


def main():
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "faceattend")

    print(f"Connecting to MySQL at {host}:{port} as {user}...")

    admin_connection = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
    )
    admin_cursor = admin_connection.cursor()

    admin_cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{database}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
    )
    admin_connection.commit()
    admin_cursor.close()
    admin_connection.close()

    connection = mysql.connector.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
    )
    cursor = connection.cursor()

    schema_text = SCHEMA_FILE.read_text(encoding="utf-8")
    for statement in clean_sql(schema_text):
        cursor.execute(statement)

    connection.commit()
    migration_count = apply_migrations(connection, cursor)
    cursor.close()
    connection.close()

    print(f"✓ Database '{database}' is ready.")
    print("✓ FaceAttend tables created successfully.")
    print(f"✓ Applied {migration_count} new database migration(s).")


if __name__ == "__main__":
    try:
        main()
    except mysql.connector.Error as exc:
        print("\nDatabase setup failed.")
        print(f"MySQL error: {exc}")
        print("\nCheck that MySQL is running and that your .env credentials are correct.")
        raise SystemExit(1)
