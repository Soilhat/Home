import re
from datetime import datetime
from typing import List

import pandas as pd
from flask import request, session

from core.entities.bank import Transaction
from flaskr.db import get_db
from flaskr.extensions import bank_repository

bank_config = {"ca-paris": {"module": "cragr", "website": "www.ca-paris.fr"}}


def get_banks(case_module=True):
    user_id = session.get("user_id")
    return bank_repository.get_banks(user_id, case_module)


def category_convertion(label: str):
    convertions = {"PAIEMENT CB ": ("FACTURE CARTE", "TYPE_CARD")}
    for value, conv in convertions.items():
        if value in label:
            return label.replace(value, ""), conv[0], conv[1]

    return label, None, None


def process_bnp_excel(df: pd.DataFrame):
    """Convert Dataframe to usable transactions, upload_date and balance.

    Returns:
        - transactions (pd.DataFrame): transactions with columns ["date", "label", "amount"]
        - account_number (string): Account identifier
        - upload_date (datetime): date of the extraction
        - balance (float): balance at upload date
    """
    balance_row = df.iloc[0].index.tolist()
    new_header = df.iloc[1].values.tolist()  # grab the first row for the header
    df = df[2:]  # take the data less the header row
    df.columns = new_header  # set the header row as the df header
    df.rename(
        columns={
            "Date operation": "date",
            "Libelle operation": "label",
            "Montant operation": "amount",
        },
        inplace=True,
    )
    df = df[["date", "label", "amount"]]
    df[["label", "category", "type"]] = df.apply(
        lambda x: category_convertion(x["label"]), axis=1, result_type="expand"
    )

    return (
        list(map(lambda x: Transaction(x), df.to_dict(orient="records"))),
        balance_row[0].split(" ")[-1],
        datetime.strptime(balance_row[1].split(" ")[-1], "%d/%m/%Y"),
        balance_row[2],
    )


def process_ca_excel(df: pd.DataFrame):
    """Convert Dataframe to usable transactions, upload_date and balance.

    Returns:
        - transactions (pd.DataFrame): transactions with columns ["date", "label", "amount"]
        - account_number (string): Account identifier
        - upload_date (datetime): date of the extraction
        - balance (float): balance at upload date
    """
    upload_date = datetime.strptime(df.iloc[0].index[0].split(" ")[-1], "%d/%m/%Y")
    balance = float(df.iloc[5].values[2].split(" ")[1].replace(",", ".").replace(" ", ""))
    account_number = df.iloc[3].values[0].split(" ")[-1]
    new_header = df.iloc[8].values.tolist()  # grab the first row for the header
    df = df[9:]  # take the data less the header row
    df.columns = new_header  # set the header row as the df header
    df.rename(
        columns={
            "Date": "date",
            "Libellé": "label",
        },
        inplace=True,
    )
    df["amount"] = df.apply(
        lambda x: x["Crédit euros"] if x["Crédit euros"] > 0 else 0 - x["Débit euros"],
        axis=1,
    )
    df = df[["date", "label", "amount"]]
    df[["label", "category", "type"]] = df.apply(
        lambda x: category_convertion(x["label"]), axis=1, result_type="expand"
    )

    return (
        list(map(lambda x: Transaction(x), df.to_dict(orient="records"))),
        account_number,
        upload_date,
        balance,
    )


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
