import mysql.connector
from woob.capabilities.base import NotLoadedType, NotAvailableType

import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))

from instance.config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB


def exect_query(*args):
    conn = mysql.connector.connect(
        host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB
    )
    curr = conn.cursor()
    curr.execute(*args)
    resp = curr.fetchall()
    conn.close()
    return resp


def executemany(query, records):
    try:
        records = [
            tuple(
                [
                    element if (not isinstance(element, NotLoadedType)) and (not isinstance(element, NotAvailableType) )else None
                    for element in record
                ]
            )
            for record in records
        ]
        connection = mysql.connector.connect(
            host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASSWORD, database=MYSQL_DB
        )
        cursor = connection.cursor()
        cursor.executemany(query, records)
        connection.commit()
        print(cursor.rowcount, "Record inserted or updated successfully")

    except mysql.connector.Error as error:
        print(f"Failed to insert record into MySQL table {error}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")
