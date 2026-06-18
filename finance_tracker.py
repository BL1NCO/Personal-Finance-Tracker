import os
import json
import uuid
from pathlib import Path
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from typing import Optional
from enum import Enum


DATA_DIR = Path.home() / ".finance_tracker"
DATA_FILE = DATA_DIR / "ledger.json"
BUDGET_FILE = DATA_DIR / "budgets.json"


class TransactionType(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"


CATEGORIES = {
    TransactionType.EXPENSE: [
        "Housing", "Food & Dining", "Transportation", "Healthcare",
        "Entertainment", "Shopping", "Education", "Utilities",
        "Insurance", "Savings", "Personal Care", "Other",
    ],
    TransactionType.INCOME: [
        "Salary", "Freelance", "Investment", "Gift", "Refund", "Other",
    ],
}


@dataclass
class Transaction:
    id: str
    type: str
    amount: float
    category: str
    description: str
    date: str
    tags: list[str] = field(default_factory=list)


class Ledger:
    def __init__(self):
        DATA_DIR.mkdir(exist_ok=True)
        self._transactions: list[Transaction] = []
        self._budgets: dict[str, float] = {}
        self._load()

    def _load(self):
        if DATA_FILE.exists():
            with open(DATA_FILE) as f:
                raw = json.load(f)
            self._transactions = [Transaction(**t) for t in raw]
        if BUDGET_FILE.exists():
            with open(BUDGET_FILE) as f:
                self._budgets = json.load(f)

    def _save(self):
        with open(DATA_FILE, "w") as f:
            json.dump([asdict(t) for t in self._transactions], f, indent=2)
        with open(BUDGET_FILE, "w") as f:
            json.dump(self._budgets, f, indent=2)

    def add(self, transaction: Transaction):
        self._transactions.append(transaction)
        self._save()

    def delete(self, transaction_id: str) -> bool:
        before = len(self._transactions)
        self._transactions = [t for t in self._transactions if t.id != transaction_id]
        if len(self._transactions) < before:
            self._save()
            return True
        return False

    def all(self) -> list[Transaction]:
        return sorted(self._transactions, key=lambda t: t.date, reverse=True)

    def filter(
        self,
        tx_type: Optional[str] = None,
        category: Optional[str] = None,
        month: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[Transaction]:
        results = self.all()
        if tx_type:
            results = [t for t in results if t.type == tx_type]
        if category:
            results = [t for t in results if t.category.lower() == category.lower()]
        if month:
            results = [t for t in results if t.date.startswith(month)]
        if tag:
            results = [t for t in results if tag in t.tags]
        return results

    def set_budget(self, category: str, amount: float):
        self._budgets[category] = amount
        self._save()

    def get_budget(self, category: str) -> Optional[float]:
        return self._budgets.get(category)

    def all_budgets(self) -> dict[str, float]:
        return self._budgets


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def banner():
    print("\033[96m")
    print("  ╔══════════════════════════════════════╗")
    print("  ║       PERSONAL FINANCE TRACKER       ║")
    print("  ╚══════════════════════════════════════╝")
    print("\033[0m")


def fmt_amount(amount: float, tx_type: str) -> str:
    color = "\033[91m" if tx_type == TransactionType.EXPENSE else "\033[92m"
    sign = "-" if tx_type == TransactionType.EXPENSE else "+"
    return f"{color}{sign}${amount:,.2f}\033[0m"


def prompt_amount(label: str = "Amount") -> float:
    while True:
        try:
            val = float(input(f"  {label}: $").strip())
            if val <= 0:
                print("  Amount must be greater than zero.")
                continue
            return round(val, 2)
        except ValueError:
            print("  Invalid amount. Enter a number.")


def prompt_date(label: str = "Date (YYYY-MM-DD, blank = today)") -> str:
    while True:
        raw = input(f"  {label}: ").strip()
        if not raw:
            return date.today().isoformat()
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("  Invalid format. Use YYYY-MM-DD.")


def prompt_category(tx_type: TransactionType) -> str:
    cats = CATEGORIES[tx_type]
    print(f"\n  Categories:")
    for i, cat in enumerate(cats, 1):
        print(f"    [{i:2}] {cat}")
    while True:
        try:
            choice = int(input("  Select category: ").strip())
            if 1 <= choice <= len(cats):
                return cats[choice - 1]
        except ValueError:
            pass
        print(f"  Choose between 1 and {len(cats)}.")


def add_transaction(ledger: Ledger, tx_type: TransactionType):
    print(f"\n  — Add {tx_type.value.capitalize()} —")
    amount = prompt_amount()
    category = prompt_category(tx_type)
    description = input("  Description: ").strip() or "—"
    tx_date = prompt_date()
    tags_raw = input("  Tags (comma-separated, optional): ").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

    tx = Transaction(
        id=str(uuid.uuid4())[:8],
        type=tx_type.value,
        amount=amount,
        category=category,
        description=description,
        date=tx_date,
        tags=tags,
    )
    ledger.add(tx)
    print(f"\n  \033[92m✓ Transaction recorded — ID: {tx.id}\033[0m")


def view_transactions(ledger: Ledger):
    print("\n  — View Transactions —")
    print("  Filter by: [1] All  [2] Month  [3] Category  [4] Tag")
    choice = input("  Select: ").strip()

    filters: dict = {}
    if choice == "2":
        m = input("  Month (YYYY-MM): ").strip()
        filters["month"] = m
    elif choice == "3":
        cat = input("  Category: ").strip()
        filters["category"] = cat
    elif choice == "4":
        tag = input("  Tag: ").strip()
        filters["tag"] = tag

    tx_type_choice = input("  Type: [1] All  [2] Expenses  [3] Income — ").strip()
    if tx_type_choice == "2":
        filters["tx_type"] = TransactionType.EXPENSE.value
    elif tx_type_choice == "3":
        filters["tx_type"] = TransactionType.INCOME.value

    results = ledger.filter(**filters)

    if not results:
        print("\n  No transactions found.")
        return

    print(f"\n  {'ID':<10} {'Date':<12} {'Type':<10} {'Category':<20} {'Amount':>12}  Description")
    print("  " + "─" * 80)
    for t in results[:50]:
        amount_str = f"{'−' if t.type == 'expense' else '+'}${t.amount:,.2f}"
        color = "\033[91m" if t.type == "expense" else "\033[92m"
        print(f"  {t.id:<10} {t.date:<12} {t.type:<10} {t.category:<20} {color}{amount_str:>12}\033[0m  {t.description[:24]}")
    if len(results) > 50:
        print(f"\n  ... and {len(results) - 50} more.")


def monthly_summary(ledger: Ledger):
    print("\n  — Monthly Summary —")
    month = input("  Month (YYYY-MM, blank = current): ").strip()
    if not month:
        month = date.today().strftime("%Y-%m")

    expenses = ledger.filter(tx_type=TransactionType.EXPENSE.value, month=month)
    incomes = ledger.filter(tx_type=TransactionType.INCOME.value, month=month)

    total_exp = sum(t.amount for t in expenses)
    total_inc = sum(t.amount for t in incomes)
    net = total_inc - total_exp

    by_category: dict[str, float] = defaultdict(float)
    for t in expenses:
        by_category[t.category] += t.amount

    width = 50
    print(f"\n  ┌{'─' * width}┐")
    print(f"  │{'  SUMMARY: ' + month:^{width}}│")
    print(f"  ├{'─' * width}┤")
    print(f"  │  {'Total Income':<30} {'$' + f'{total_inc:,.2f}':>16}  │")
    print(f"  │  {'Total Expenses':<30} {'$' + f'{total_exp:,.2f}':>16}  │")
    net_color = "\033[92m" if net >= 0 else "\033[91m"
    net_str = f"{'$' if net >= 0 else '-$'}{abs(net):,.2f}"
    print(f"  │  {'Net':<30} {net_color}{net_str:>16}\033[0m  │")

    if by_category:
        print(f"  ├{'─' * width}┤")
        print(f"  │{'  EXPENSES BY CATEGORY':^{width}}│")
        print(f"  ├{'─' * width}┤")
        budgets = ledger.all_budgets()
        for cat, total in sorted(by_category.items(), key=lambda x: -x[1]):
            budget = budgets.get(cat)
            bar = ""
            if budget:
                pct = min(total / budget, 1.0)
                filled = int(pct * 10)
                bar_color = "\033[91m" if pct >= 0.9 else "\033[93m" if pct >= 0.7 else "\033[92m"
                bar = f" {bar_color}{'█' * filled}{'░' * (10 - filled)}\033[0m"
            print(f"  │  {cat:<24} {'$' + f'{total:,.2f}':>10}{bar:<22}│")

    print(f"  └{'─' * width}┘")


def manage_budgets(ledger: Ledger):
    print("\n  — Budget Manager —")
    print("  [1] Set budget  [2] View budgets")
    choice = input("  Select: ").strip()
    if choice == "1":
        cats = CATEGORIES[TransactionType.EXPENSE]
        for i, c in enumerate(cats, 1):
            print(f"    [{i}] {c}")
        try:
            idx = int(input("  Select category: ").strip()) - 1
            cat = cats[idx]
            amount = prompt_amount(f"Monthly budget for {cat}")
            ledger.set_budget(cat, amount)
            print(f"  \033[92m✓ Budget set: {cat} → ${amount:,.2f}/month\033[0m")
        except (ValueError, IndexError):
            print("  Invalid selection.")
    elif choice == "2":
        budgets = ledger.all_budgets()
        if not budgets:
            print("  No budgets configured.")
            return
        print(f"\n  {'Category':<30} {'Monthly Budget':>16}")
        print("  " + "─" * 48)
        for cat, amt in sorted(budgets.items()):
            print(f"  {cat:<30} {'$' + f'{amt:,.2f}':>16}")


def delete_transaction(ledger: Ledger):
    tx_id = input("\n  Transaction ID to delete: ").strip()
    if ledger.delete(tx_id):
        print("  \033[92m✓ Transaction deleted.\033[0m")
    else:
        print("  \033[91m✗ ID not found.\033[0m")


def main_menu(ledger: Ledger):
    options = {
        "1": ("Add Expense", lambda: add_transaction(ledger, TransactionType.EXPENSE)),
        "2": ("Add Income", lambda: add_transaction(ledger, TransactionType.INCOME)),
        "3": ("View Transactions", lambda: view_transactions(ledger)),
        "4": ("Monthly Summary", lambda: monthly_summary(ledger)),
        "5": ("Manage Budgets", lambda: manage_budgets(ledger)),
        "6": ("Delete Transaction", lambda: delete_transaction(ledger)),
        "0": ("Exit", None),
    }

    while True:
        clear()
        banner()
        print("  MAIN MENU\n")
        for key, (label, _) in options.items():
            print(f"    [{key}] {label}")
        print()

        choice = input("  Select option: ").strip()
        if choice == "0":
            print("\n  Goodbye.\n")
            break
        elif choice in options:
            _, action = options[choice]
            if action:
                action()
                input("\n  Press Enter to continue...")
        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    ledger = Ledger()
    main_menu(ledger)
