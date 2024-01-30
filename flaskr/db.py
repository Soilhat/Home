from flask import current_app, g
import mysql.connector
from woob.capabilities.base import NotLoadedType, NotAvailableType


def get_db():
    if "db" not in g:
        g.conn = mysql.connector.connect(
            host=current_app.config["MYSQL_HOST"],
            user=current_app.config["MYSQL_USER"],
            password=current_app.config["MYSQL_PASSWORD"],
            database=current_app.config["MYSQL_DB"],
        )
        g.db = g.conn.cursor(buffered=True)
    return g.db, g.conn


def close_db():
    conn: mysql.connector.MySQLConnection = g.pop("conn", None)
    db: mysql.connector.cursor.MySQLCursor = g.pop("db", None)

    if conn is not None:
        if conn.is_connected():
            db.close()
            conn.close()


def executemany(query, records):
    try:
        records = [
            tuple(
                [
                    (
                        element
                        if (not isinstance(element, NotLoadedType))
                        and (not isinstance(element, NotAvailableType))
                        else None
                    )
                    for element in record
                ]
            )
            for record in records
        ]
        cursor, connection = get_db()
        cursor.executemany(query, records)
        connection.commit()
        print(cursor.rowcount, "Record inserted or updated successfully")

    except mysql.connector.Error as error:
        print(f"Failed to run executemany into MySQL table {error}")
