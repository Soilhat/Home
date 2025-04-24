from datetime import datetime
from typing import List

from adapters.sqllite.commun import ExecuteSqlite
from core.entities.bank import Account, Bank, Loan, Transaction
from core.ports.bank_repository import BankRepository


class SqlliteBankRepository(BankRepository):
    "SQLlite implementation of BankRepository"

    def __init__(self) -> None:
        super().__init__()
        self.executor = None

    def __init_executor(self, user_id):
        if self.executor is None:
            print("read db")
            self.executor = ExecuteSqlite(f"{user_id}.db", "create_bank.sql")

    def get_balance(self, user_id: int, loans=False):
        self.__init_executor(user_id)

        return self.executor.execute(
            f"""
                SELECT sum(balance) as balance
                FROM account LEFT JOIN loan on account.id=loan.id
                WHERE loan.id IS {'NOT' if loans else ''} NULL
            """,
            one=True,
        )[0]

    def get_savings(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """
                SELECT sum(amount) saving
                FROM "transaction"
                LEFT JOIN saving on "transaction".saving_id = saving.id
                WHERE saving.id IS NOT NULL
            """,
            one=True,
        )[0]

    def get_last_month(self, user_id):
        self.__init_executor(user_id)
        month = self.executor.execute(
            """
                SELECT strftime('%Y-%m', Date) month
                FROM "transaction" ORDER BY Date DESC LIMIT 1
            """,
            one=True,
        )
        if month:
            month = month[0]
        else:
            month = datetime.today().strftime("%Y-%m")
        return month

    def get_pending_budget(self, user_id, month):
        self.__init_executor(user_id)
        return self.executor.execute(
            f"""
                SELECT sum(budget) + sum(amount) as pending
                FROM (
                    SELECT trac.amount, 0 as budget
                    FROM "transaction" as trac
                    INNER JOIN account as acc on trac.account=acc.id
                    LEFT OUTER JOIN 'transaction' child on LTRIM(child.parent,0) = LTRIM(trac.id,0)
                    WHERE strftime('%Y-%m',trac.Date) = '{month}'
                        AND trac.amount < 0
                        AND trac.internal IS NULL
                        AND trac.saving_id IS NULL
                        AND child.id IS NULL
                UNION ALL
                    SELECT 0 as 'real_amount', budget.amount as budget
                    FROM budget
                    WHERE ( start IS NULL OR (strftime('%Y-%m',start) <= '{month}'))
                        AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
                        AND (type <> 'Income' OR type IS NULL)
                )labels
            """,
            one=True,
        )[0]

    def get_incomes(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """
                SELECT sum(amount) as revenus
                FROM budget
                WHERE Type = 'Income'
                    AND (end IS NULL OR end > DATE('now'))
            """,
            one=True,
        )[0]

    def get_incomes_avg(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """
                SELECT CAST(sum(amount)/3 AS DECIMAL(10,2)) as revenus_avg
                FROM "transaction" trac
                INNER JOIN account as acc on trac.account=acc.id
                WHERE amount > 0 
                    AND acc.type = 'CHECKING'
                    AND internal IS NULL
                    AND parent IS NULL
                    AND date BETWEEN 
                        DATE((SELECT MAX(date) from "transaction"),'start of month','-3 month')
                        AND DATE((SELECT MAX(date) from "transaction"), 'start of month')
            """,
            one=True,
        )[0]

    def get_curr_expenses(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """select
                    substr('--JanFebMarAprMayJunJulAugSepOctNovDec',strftime ('%m', date) * 3, 3)||' '||strftime ('%Y', date) as Date,
                    sum(CASE WHEN amount<0 THEN ABS(amount) END) as expenses,
                    sum(CASE WHEN amount>0 THEN amount END) as earnings
                from "transaction" trac
                INNER JOIN account as acc on trac.account=acc.id
                WHERE acc.type = 'CHECKING'
                    AND trac.internal IS NULL
                    AND account IS NOT NULL
                    AND date BETWEEN 
                        DATE(DATE(DATE(DATE((SELECT MAX(date) from "transaction"), '-1 year'), '-2 month'), 'start of month', '+1 month', '-1 day') ,'-1 day')
                        AND DATE(DATE((SELECT MAX(date) from "transaction"), '-1 month'), 'start of month', '+1 month', '-1 day') 
                    AND trac.parent IS NULL
                group by strftime('%Y', date),strftime('%m', date)
                order by strftime('%Y', date),strftime('%m', date);
            """
        )

    def get_monthly_savings(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """
            SELECT sum(monthly_saving) as savings
            FROM saving
            """,
            one=True,
        )[0]

    def get_monthly_savings_avg(self, user_id):
        self.__init_executor(user_id)

        return self.executor.execute(
            """
            SELECT CAST(sum(amount)/3 AS DECIMAL(10,2)) as savings_avg
            FROM "transaction"
            WHERE saving_id IS NOT NULL
                AND amount > 0
                AND date BETWEEN DATE((SELECT MAX(date) from "transaction"),'start of month','-3 month')
                    AND DATE((SELECT MAX(date) from "transaction"),'start of month')
            """,
            one=True,
        )[0]

    def get_bud_expenses(self, user_id, fixed=False):
        self.__init_executor(user_id)

        return self.executor.execute(
            f"""
            SELECT sum(amount) as exps
            FROM budget
            WHERE fixed = {fixed}
                AND Type <> 'Income'
                AND (start IS NULL OR start <= DATE('now'))
                AND (end IS NULL OR end > DATE('now'))
            """,
            one=True,
        )[0]

    def get_bud_expenses_avg(self, user_id, fixed=False):
        self.__init_executor(user_id)

        return self.executor.execute(
            f"""
            SELECT ABS(CAST(sum(trac.amount)/3 AS DECIMAL(10,2))) as exps_avg
            FROM "transaction" as trac
            LEFT JOIN budget 
                on {"UPPER(trac.label) LIKE '%'||UPPER(budget.label)||'%'" if fixed else 'budget_id = budget.id'}
            WHERE {"budget_id IS NOT NULL AND " if not fixed else ""}
                budget.Type <> 'Income'
                AND fixed = {fixed}
				AND trac.amount < 0
				AND (start IS NULL OR date >= start ) AND ( end IS NULL OR date <= end )
                AND date BETWEEN DATE((SELECT MAX(date) from "transaction"),'start of month','-3 month')
                    AND DATE((SELECT MAX(date) from "transaction"),'start of month')
            """,
            one=True,
        )[0]

    def get_all_accounts(self, user_id):
        self.__init_executor(user_id)
        return self.executor.execute("SELECT * FROM account")

    def get_transactions_count(self, user_id: int, month: str) -> int:
        self.__init_executor(user_id)

        return self.executor.execute(
            f"""
            SELECT COUNT(*)
            FROM 'transaction'
            WHERE strftime('%Y-%m',Date) = '{month}'
        """,
            one=True,
        )[0]

    def get_transactions(
        self, user_id: int, month: str, length: int = 10, curr_page: int = 1
    ) -> tuple:
        self.__init_executor(user_id)

        return self.executor.execute(
            f"""
            SELECT LTRIM(trac.id,'0'), strftime('%Y-%m-%d',Date), bank, Category, Amount, trac.Label, trac.Type, CASE WHEN internal IS NOT NULL THEN 'TRUE' ELSE 'FALSE' END, '' as edit
            FROM 'transaction' trac
            JOIN account ON account.id = trac.account
            WHERE strftime('%Y-%m',Date) = '{month}'
            ORDER BY date DESC
            LIMIT {length}
            OFFSET {(curr_page-1)*length}
        """
        )

    def get_budget_types(self, user_id):
        self.__init_executor(user_id)
        return self.executor.execute("SELECT DISTINCT type FROM budget")

    def get_budgeted_transactions(
        self, user_id: int, month: str, fixed: bool = False
    ) -> tuple:
        self.__init_executor(user_id)
        month = f"{month}-01"
        if fixed:
            query = f"""
                SELECT budget.label, IFNULL(GROUP_CONCAT(bank, ','),''), IFNULL(strftime('%Y-%m-%d',trac.Date),'') as date, budget.amount as budget, IFNULL(abs(sum(trac.amount)),0) as 'real_amount', budget.type
                FROM budget
                LEFT JOIN 'transaction' as trac on UPPER(trac.label) LIKE '%'||UPPER(budget.label)||'%'
                    AND strftime('%Y-%m',Date) = strftime('%Y-%m','{month}')
                    AND trac.amount <= 0
                LEFT OUTER JOIN account on account.id = trac.account
            """
        else:
            query = f"""
                SELECT budget.label, budget.amount as budget, IFNULL(abs(sum(trac.amount)),0) as 'real_amount', 
                    budget.amount * (
                        CASE WHEN strftime('%Y-%m',Date('now')) = strftime('%Y-%m','{month}')
                            THEN CAST(strftime('%d',DATE('now'))AS FLOAT)/CAST(strftime('%d',DATE(DATE('now'), 'start of month', '+1 month', '-1 day'))AS FLOAT)
                            ELSE 1 END
                        )-(IFNULL(abs(sum(trac.amount)),0))
                    remaining_prct, budget.type
                FROM budget
                LEFT JOIN 'transaction' as trac on budget.id = trac.budget_id AND strftime('%Y-%m',Date) = strftime('%Y-%m','{month}')
            """
        query += f"""
            WHERE  ( start IS NULL OR start <= '{month}')
                AND ( end IS NULL OR end >= '{month}')
                AND budget.fixed = {fixed}
                AND (budget.type <> 'Income' OR budget.type IS NULL)
            GROUP BY budget.label, budget.type
        """
        total = ""
        if not fixed :
            total = """
                IFNULL(sum(budget),0) as budget,
                IFNULL(sum(real_amount),0) as 'real_amount',
                '' as remaining_prct,
                '' as type
            """
        else :
            total = """
                '' as bank,
                '' as date,
                IFNULL(sum(budget),0) as budget,
                IFNULL(sum(real_amount),0) as 'real_amount',
                '' as type
            """
        return self.executor.execute(
            f"""
                {query}
            UNION ALL
                select 'Total' label,
                    {total}
                FROM (
                    {query}
                )s
        """
        )

    def __get_budgeted_income(self, user_id: int, month: str):
        self.__init_executor(user_id)
        return (
            self.executor.execute(
                f"""
            SELECT sum(budget.amount) as bedget
            FROM budget
            WHERE budget.type = 'Income' 
                AND ( start IS NULL OR strftime('%Y-%m',start) < '{month}')
                AND ( end IS NULL OR strftime('%Y-%m',end) > '{month}')
        """,
                one=True,
            )[0]
            or 0
        )

    def get_summary(self, user_id: int, month: str):
        self.__init_executor(user_id)
        query = f"""
            SELECT type, IFNULL(abs(sum(budget))*100/{self.__get_budgeted_income(user_id, month)},0) as '%', sum(budget) as budget, abs(sum(real_amount)) as 'real_amount'
            FROM (
                SELECT type, sum(amount) as 'real_amount', sum(budget)  as budget
                FROM (
                    SELECT IFNULL(budget.type, fixed_bud.type) as type, trac.amount, 0 as budget
                    FROM 'transaction' as trac
                    INNER JOIN account as acc on trac.account=acc.id
                    LEFT OUTER JOIN budget on budget.id = trac.budget_id AND strftime('%Y-%m',trac.Date) = '{month}'
                    LEFT OUTER JOIN budget as fixed_bud on UPPER(trac.label) LIKE '%'||UPPER(fixed_bud.label)||'%' AND strftime('%Y-%m',trac.Date) = '{month}'
                    LEFT OUTER JOIN 'transaction' as child ON LTRIM(child.parent,'0') = LTRIM(trac.id,'0')
                    WHERE strftime('%Y-%m',trac.Date) = '{month}'
                        AND (budget.type <> 'Income' OR budget.type IS NULL)
                        AND trac.amount < 0
                        AND trac.internal IS NULL
                        AND trac.saving_id IS NULL
                        AND child.id IS NULL
                    GROUP BY trac.id
                UNION ALL
                    SELECT budget.type, 0.0 as 'real_amount', budget.amount as budget
                    FROM budget
                    WHERE ( start IS NULL OR (strftime('%Y-%m',start) <= '{month}'))
                        AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
                        AND (type <> 'Income' OR type IS NULL)
                )labels
                GROUP BY type
            )type_table
            GROUP BY type
        """
        return self.executor.execute(
            f"""
                {query}
            UNION ALL
                select 'Total' type,
                    IFNULL(abs(sum(budget))*100/{self.__get_budgeted_income(user_id, month)},0) as '%',
                    sum(budget) as budget,
                    sum(real_amount) as 'real_amount'
                FROM (
                    {query}
                )s
        """
        )

    def get_revenus(self, user_id: int, month: str):
        self.__init_executor(user_id)
        revenus = f"""
            SELECT label, IFNULL(strftime('%Y-%m-%d',MAX(date)),'') as date, sum(amount) as 'real_amount', IFNULL(MAX(budget),0) as budget
            FROM (
                SELECT trac.label, trac.date, trac.amount, budget.amount as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
                FROM 'transaction' as trac
                INNER JOIN account as acc on trac.account=acc.id
                LEFT OUTER JOIN budget on Upper(trac.label) LIKE '%'||Upper(budget.label)||'%' AND budget.type = 'Income'
                    AND ( start IS NULL OR strftime('%Y-%m',start) <= '{month}')
                    AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
                WHERE acc.type = 'CHECKING' AND trac.amount > 0 AND strftime('%Y-%m',Date) = '{month}'
                    AND trac.internal IS NULL
            UNION ALL
                SELECT DISTINCT budget.label, '' as date, 0 as 'real', budget.amount as budget, CASE WHEN budget.label IS NULL THEN trac.label else budget.label END as budget_label
                FROM budget
                LEFT JOIN 'transaction' as trac on Upper(trac.label) LIKE '%'||Upper(budget.label)||'%'
                WHERE (trac.id IS NULL OR strftime('%Y-%m',Date) <> '{month}')
                    AND (budget.type = 'Income' OR budget.type IS NULL) 
                    AND ( start IS NULL OR strftime('%Y-%m',start) <= '{month}')
                    AND ( end IS NULL OR (strftime('%Y-%m',end) >= '{month}'))
            )a
            GROUP BY budget_label
        """
        return self.executor.execute(
            f"""
            {revenus}
        UNION ALL
            select 'Total' label,
                '' date,
                IFNULL(sum(real_amount),0) as 'real_amount',
                IFNULL(sum(budget),0) as budget
            FROM (
                {revenus}
            )s
        """
        )

    def get_expenses(self, user_id: int, month: str):
        self.__init_executor(user_id)
        query = f"""
            SELECT LTRIM(trac.id,'0') as id, trac.label, account.bank, strftime('%Y-%m-%d',trac.date) as date, abs(trac.amount) as amount, 
                CASE 
                    WHEN trac.saving_id is NOT NULL THEN 'Saving - '||saving.name
                    WHEN trac.budget_id is NOT NULL THEN budget.label
                    WHEN child.id IS NOT NULL THEN 'Split'
                    ELSE ''
                END budget,
                '' as edit
            FROM 'transaction' as trac
            LEFT OUTER JOIN budget fix on UPPER(trac.label) LIKE '%'||UPPER(fix.label)||'%'
            LEFT JOIN budget on trac.budget_id = budget.id
            LEFT JOIN saving on trac.saving_id = saving.id
            LEFT OUTER JOIN account on trac.account = account.id
            LEFT OUTER JOIN 'transaction' child on LTRIM(child.parent,'0') = LTRIM(trac.id,'0')
            WHERE 
                trac.amount < 0
                AND strftime('%Y-%m',trac.Date) = '{month}'
                AND trac.internal IS NULL
                AND fix.label IS NULL
                AND trac.parent IS NULL
            GROUP BY trac.id
        """
        return self.executor.execute(
            f"""
                {query}
            UNION ALL
                select '' as id, 'Total' label, '' as bank, '' as 'date', 
                    IFNULL(sum(amount),0) as amount,
                    '' as 'budget', '' as edit
                FROM (
                    {query}
                )s
            ORDER BY date DESC, amount desc
        """
        )

    def get_spendings(self, user_id: int, month: str):
        self.__init_executor(user_id)
        labels = self.executor.execute(
            f"""
                SELECT budget.label
                FROM budget
                WHERE budget.type <> 'Income' AND budget.fixed = 0
                    AND ( start IS NULL OR strftime('%Y-%m',start) <= '{month}')
                    AND ( end IS NULL OR strftime('%Y-%m',end) >= '{month}')
            UNION ALL
                SELECT "Saving - "||name
                FROM saving
        """
        )
        result = ["", "Split"]
        return [spending[0] for spending in labels] + result

    def get_banks(self, user_id: int, case_module=True) -> list:
        self.__init_executor(user_id)
        if case_module:
            case = "CASE "
            for b_key, bank in self.bank_config.items():
                case += "WHEN "
                case += " AND ".join(
                    [f"""{key}='{value}'""" for key, value in bank.items()]
                )
                case += f""" THEN '{b_key}'"""
            case += " ELSE module END as module"
        else:
            case = "module"
        return self.executor.execute(
            f"""
            SELECT login, {case}, name, password, website{", '' as del_col" if case_module else ""}
            FROM bank
            """
        )

    def upload_transactions(self, user_id, transactions: List[Transaction]):
        self.__init_executor(user_id)

        self.executor.executemany(
            """
                UPDATE 'transaction'
                SET id = ?, category = ?, date = ?, type = ?, 
                    value_date = ?, real_date = ?, coming = 0, label = ?
                WHERE id <> ? AND account = ? AND amount = ? AND coming = 1 
                    AND ? BETWEEN DATE(date, '-7 days') AND DATE(date, '7 days')
            """,
            [
                (
                    tra.id,
                    tra.category,
                    tra.date,
                    tra.type,
                    tra.value_date,
                    tra.real_date,
                    tra.label,
                    tra.id,
                    tra.account.id,
                    tra.amount,
                    tra.date,
                )
                for tra in transactions
            ],
        )

        records = [
            (
                transaction.id,
                transaction.account.id,
                transaction.amount,
                transaction.category,
                transaction.date,
                transaction.label,
                transaction.type,
                transaction.real_date,
                transaction.value_date,
                transaction.coming,
            )
            for transaction in transactions
        ]
        self.executor.executemany(
            """
                INSERT OR IGNORE INTO 'transaction' 
                    (id, account, amount,
                    category, date, label,
                    type, real_date, value_date, coming)
                VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    def check_internal(self, user_id: int):
        self.__init_executor(user_id)
        self.executor.execute("""UPDATE 'transaction' SET internal = NULL WHERE internal = 'None'""")
        self.executor.execute("""
            DELETE FROM 'transaction' WHERE id IN (
                SELECT
                    CASE WHEN 
                        csv.internal IS NOT NULL OR csv.budget_id IS NOT NULL OR csv.saving_id IS NOT NULL OR csv.comment IS NOT NULL
                        OR EXISTS (
                            SELECT null FROM 'transaction' intern
                            WHERE intern.parent = csv.id
                        )
                        THEN woob.id
                    ELSE csv.id END
                FROM 'transaction' woob
                JOIN 'transaction' csv ON woob.amount = csv.amount AND woob.date = csv.date AND woob.account = csv.account
                WHERE woob.real_date IS NOT NULL AND csv.real_date IS NULL AND csv.parent IS NULL
                ORDER BY woob.date desc
            )
        """)
        internals = self.executor.execute(
            """
            SELECT 
                coming.id, exp.id
            FROM 'transaction' coming
            JOIN 'transaction' exp ON coming.amount + exp.amount = 0 AND NOT EXISTS (
                SELECT null from 'transaction' tmp
                WHERE coming.amount + tmp.amount = 0 
                    AND tmp.date <= coming.date
                    AND tmp.date > exp.date
                    AND coming.account IS NOT NULL
                    AND tmp.account IS NOT NULL
            )
                AND (exp.date BETWEEN DATE(coming.date, '-7 days') AND DATE(coming.date, '7 days'))
            WHERE coming.amount > 0 
                AND coming.internal IS NULL
                AND exp.internal IS NULL
                AND coming.account IS NOT NULL
                AND exp.account IS NOT NULL
        """
        )
        update_list = []
        for internal in internals:
            update_list.append((internal[0], internal[1]))
            update_list.append((internal[1], internal[0]))
        if update_list:
            print("Update Internal transactions...")
            self.executor.executemany(
                """
                UPDATE 'transaction' set internal = ? WHERE id = ?
            """,
                update_list,
            )

    def get_account(self, user_id: int, account_number: str) -> Account:
        self.__init_executor(user_id)
        account = self.executor.execute(
            f"""
            SELECT * FROM account
            WHERE id = '{account_number}'
                or SUBSTR('{account_number}', LENGTH('{account_number}') - 3) = SUBSTR(number, LENGTH(number) - 3)
        """,
            one=True,
        )
        res_account = Account(
            {
                "id": account[0],
                "bank": Bank(name=account[1]),
                "label": account[2],
                "type": account[3],
                "balance": account[4],
                "coming": account[5],
                "iban": account[6],
                "number": account[7],
            }
        )
        return res_account

    def update_trac(self, user_id, trac_id, budget_name):
        self.__init_executor(user_id)
        if budget_name.startswith("Saving"):
            budget_table = "saving"
            budget_column = "saving_id"
            rvrt_budget_column = "budget_id"
            compare = "'Saving - '||saving.name"
        else:
            budget_table = "budget"
            budget_column = "budget_id"
            rvrt_budget_column = "saving_id"
            compare = "budget.label"

        budget_id = self.executor.execute(
            f""" SELECT id FROM {budget_table} WHERE {compare} = ?""",
            (budget_name,),
            one=True,
        )
        self.executor.execute(
            f"""UPDATE 'transaction' SET {budget_column} = ? , {rvrt_budget_column} = NULL WHERE id LIKE '%'||?""",
            (budget_id[0] if budget_id else None, trac_id),
            commit=True,
        )

    def get_all_savings(self, user_id: int):
        self.__init_executor(user_id)
        return self.executor.execute(
            """
            SELECT saving.id, saving.name, IFNULL(sum('transaction'.amount),0) balance, saving.monthly_saving, saving.goal
            FROM saving
            LEFT JOIN 'transaction' on 'transaction'.saving_id = saving.id
            group by saving.id
            """
        )

    def get_saving_trac(self, user_id, saving_id):
        self.__init_executor(user_id)
        return self.executor.execute(
            f"""
            SELECT 'transaction'.label, bank, strftime('%Y-%m-%d',date), amount
            FROM 'transaction'
            LEFT JOIN saving on 'transaction'.saving_id = saving.id
            LEFT JOIN account on 'transaction'.account = account.id
            WHERE saving.id = {saving_id}
            ORDER BY date desc
            """
        )

    def upload_accounts(self, user_id, accounts: List[Account]):
        self.__init_executor(user_id)
        records = [
            (
                account.id,
                account.bank.name,
                account.label,
                account.type,
                account.balance,
                None if account.coming is None else float(account.coming),
                account.iban,
                account.number,
            )
            for account in accounts
        ]
        self.executor.executemany(
            """
                REPLACE INTO account 
                    (id, bank, label, type, balance, coming, iban, number)
                VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    def upload_loans(self, user_id, loans: List[Loan]):
        self.__init_executor(user_id)
        records = [
            (
                loan.id,
                loan.duration,
                loan.insurance_amount,
                loan.maturity_date,
                loan.nb_payments_left,
                None if loan.next_payment_amount is None else float(loan.next_payment_amount),
                loan.next_payment_date,
                loan.rate,
                loan.total_amount,
            )
            for loan in loans
        ]
        self.executor.executemany(
            """
                REPLACE INTO loan 
                    (id, duration, insurance_amount,
                    maturity_date, nb_payments_left, next_payment_amount,
                    next_payment_date, rate, total_amount)
                VALUES 
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )

    def delete_bank(self, user_id: int, login):
        self.__init_executor(user_id)
        self.executor.execute("DELETE FROM bank WHERE login = ?", (login,), commit=True)

    def get_budget(self, user_id, current: bool, fixed: bool, income: bool):
        self.__init_executor(user_id)
        query = "SELECT * FROM budget WHERE "
        query += (
            "(end IS NULL OR end >= DATE('now')) " if current else "end <= DATE('now') "
        )
        query += f"AND fixed = {fixed} AND type {'='if income else '<>'} 'Income' "
        query += "ORDER BY end IS NULL DESC, end desc, start IS NULL DESC, start desc"
        return self.executor.execute(query)

    def update_budget(self, user_id, label, amount, budget_type, start, end, fixed, id):
        self.__init_executor(user_id)
        return self.executor.execute(
            "UPDATE budget SET label = ?, amount = ?, type = ?, start = ?, end = ?, fixed = ?"
            " WHERE id = ?",
            (label, amount, budget_type, start, end, fixed, id),
        )
