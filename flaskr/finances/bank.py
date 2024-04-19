import re
from typing import List

from flask import request

from flaskr.db import get_db

bank_config = {"ca-paris": {"module": "cragr", "website": "www.ca-paris.fr"}}


def get_banks(case_module=True):
    curr = get_db()[0]
    if case_module:
        case = "CASE "
        for b_key, bank in bank_config.items():
            case += "WHEN "
            case += " AND ".join(
                [f"""{key}='{value}'""" for key, value in bank.items()]
            )
            case += f""" THEN '{b_key}'"""
        case += " ELSE module END as module"
    else:
        case = "module"
    curr.execute(
        f"""
        SELECT login, {case}, name, password, website{", '' as del_col" if case_module else ""}
        FROM bank
        """
    )
    return curr.fetchall()


def create_banks():
    banks_: dict = request.values.dicts[1].to_dict()
    if banks_:
        banks: List[dict] = []
        for key, value in banks_.items():
            ind = re.findall(r"\d+", key)[0]
            column = key.replace(ind, "")
            if column == "module" and value in bank_config:
                element = bank_config[value]
            else:
                element = {column: value}
            if len(banks) < int(ind):
                banks.append(element)
            else:
                banks[int(ind) - 1].update(element)

        curr, conn = get_db()
        for bank in banks:
            curr.execute(
                "REPLACE INTO bank (login, module, name, password, website) VALUES (?,?,?,?,?)",
                (
                    bank["login"],
                    bank["module"],
                    bank["name"],
                    bank["password"],
                    bank.get("website", None),
                ),
            )
            conn.commit()


def delete_bank(login):
    curr, conn = get_db()
    curr.execute("DELETE FROM bank WHERE login = ?", (login,))
    conn.commit()
