import datetime
import decimal
import sqlite3
import mysql.connector
from instance.config import MYSQL_DB, MYSQL_HOST, MYSQL_PASSWORD, MYSQL_USER

conn = sqlite3.connect("databases/5.db")
curr = conn.cursor()

src_conn = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB,
)
src_curr = src_conn.cursor()

def convert_type(entries:list):
    result= []
    for entry in entries:
        result_entry=[]
        for value in entry:
            if isinstance(value, decimal.Decimal):
                result_entry.append(float(value))
            elif isinstance(value,datetime.date):
                result_entry.append(value.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                result_entry.append(value)
        result.append(result_entry)
    return result

tables = ["account", "budget", "loan", "saving","transaction"]
for table in tables:
    src_curr.execute(f"SELECT * FROM {table}")
    rows = src_curr.fetchall()
    if table == "transaction":
        rows = [row + (None,) for row in rows]
    curr.executemany(
        f"REPLACE INTO '{table}' VALUES ({','.join(['?']*len(rows[0]))})",convert_type(rows)
    )

conn.commit()
curr.close()
conn.close()
src_curr.close()
src_conn.close()
