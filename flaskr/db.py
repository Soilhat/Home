import os
import sqlite3

import mysql.connector
from flask import current_app, g, session
from woob.capabilities.base import NotAvailableType, NotLoadedType


def get_user_db():
    conn = mysql.connector.connect(
        host=current_app.config["MYSQL_HOST"],
        user=current_app.config["MYSQL_USER"],
        password=current_app.config["MYSQL_PASSWORD"],
        database=current_app.config["MYSQL_DB"],
    )
    return conn


def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))


def get_db(user_id: int = None, g_stored=True):
    if user_id is None:
        user_id = session["user_id"]
    if (not g_stored) or ("db" not in g):
        path = f"databases/{user_id}.db"
        exist_path = os.path.isfile(path)
        if not exist_path:
            file = open(path, "w", encoding="utf8")
            file.close()
        conn = sqlite3.connect(path)
        db = conn.cursor()
        # g.db.row_factory = make_dicts
        if not exist_path:
            with open("databases/create.sql", "r", encoding="utf8") as sql_file:
                sql_script = sql_file.read()
            db.executescript(sql_script)
            conn.commit()
        if g_stored:
            g.db = db
            g.conn = conn
    else:
        db = g.db
        conn = g.conn
    return db, conn


def close_db(conn=None, db=None):
    if conn is None:
        conn = g.pop("conn", None)
    if db is None:
        db = g.pop("db", None)
    if conn is not None:
        if conn.is_connected():
            db.close()
            conn.close()


def query_db(query, args=(), one=False):
    cur = get_db()[0].execute(query, args)
    rv = cur.fetchall()
    return (rv[0] if rv else None) if one else rv


def executemany(query: str, records: list):
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
        if "UPDATE" in query.upper():
            cursor.execute("PRAGMA foreign_keys=ON")
        cursor.executemany(query, records)
        connection.commit()
        print(cursor.rowcount, "Record inserted or updated successfully")
        if "UPDATE" in query.upper():
            cursor.execute("PRAGMA foreign_keys=OFF")

    except Exception as error:
        print(f"Failed to run executemany into SQLITE table {error}")
