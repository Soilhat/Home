import os
import sqlite3
from sqlite3 import Cursor, Row


def dict_factory(cursor: Cursor, row: Row) -> dict:
    "Transform sqlite3 results to dictionaries"
    return dict(zip(enumerate(cursor.description), row))


class ExecuteSqlite:
    base_path = "adapters/sqllite/databases"

    def __init__(self, usage_path, creation_path):
        self.path = f"{self.base_path}/{usage_path}"
        exist_path = os.path.isfile(self.path)
        if not exist_path:
            file = open(self.path, "w", encoding="utf8")
            file.close()
            with sqlite3.connect(self.path) as conn:
                db = conn.cursor()
                if not exist_path:
                    with open(
                        f"{self.base_path}/{creation_path}",
                        "r",
                        encoding="utf8",
                    ) as sql_file:
                        sql_script = sql_file.read()
                    db.executescript(sql_script)
                    conn.commit()

    def execute(self, query: str, args=(), one=False, commit=False):
        with sqlite3.connect(self.path) as conn:
            db = conn.cursor()
            db.execute(query, args)
            if commit:
                conn.commit()
            if one:
                return db.fetchone()
            return db.fetchall()

    def executemany(self, query: str, args=()):
        with sqlite3.connect(self.path) as conn:
            db = conn.cursor()
            if "UPDATE" in query.upper():
                db.execute("PRAGMA foreign_keys=ON")
            db.executemany(query, args)
            conn.commit()
            print(db.rowcount, "Record inserted or updated successfully")
            if "UPDATE" in query.upper():
                db.execute("PRAGMA foreign_keys=OFF")
