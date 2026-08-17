import mysql.connector
from flask import current_app


def get_db_connection(include_database=True):
    """Create a new MySQL connection using Flask configuration."""
    config = {
        "host": current_app.config["DB_HOST"],
        "port": current_app.config["DB_PORT"],
        "user": current_app.config["DB_USER"],
        "password": current_app.config["DB_PASSWORD"],
    }

    if include_database:
        config["database"] = current_app.config["DB_NAME"]

    return mysql.connector.connect(**config)


def database_health():
    """Return (ok, message) so routes can safely report DB health."""
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE(), VERSION()")
        database_name, version = cursor.fetchone()
        return True, f"Connected to {database_name} on MySQL {version}"
    except mysql.connector.Error as exc:
        return False, str(exc)
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()
