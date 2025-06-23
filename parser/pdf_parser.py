import pdfplumber
import re
import pandas as pd

def categorize_transaction(description: str) -> str:
    description = description.lower()

    if "pak n save" in description or "four square" in description or "woolworths" in description:
        return "Groceries"
    elif "fuel" in description or "mobil" in description or "z " in description:
        return "Transport"
    elif "cityfitness" in description:
        return "Fitness"
    elif any(x in description for x in ["kfc", "dominos", "mcdonalds", "subway", "burger king", "pizza hut", "break time", "st pierre"]):
        return "Eating Out"
    elif any(x in description for x in ["google one", "steam", "adobe", "apple", "shein", "aliex", "eneba", "spotify", "netflix"]):
        return "Subscriptions"
    elif "credit transfer" in description or "ird" in description or "deposit" in description:
        return "Income"
    else:
        return "Other"


def parse_statement(pdf_path: str) -> pd.DataFrame:
    transactions = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for line in lines:
                match = re.match(r"^(\d{2} \w{3})\s+([A-Z]{2})\s+(.+?)\s+(\d+\.\d{2})\s+(\d+\.\d{2})$", line.strip())
                if match:
                    date, tx_type, desc, amount, balance = match.groups()
                    category = categorize_transaction(desc)
                    transactions.append({
                        "date": date,
                        "type": tx_type,
                        "description": desc.strip(),
                        "amount": float(amount),
                        "balance": float(balance),
                        "category": category
                    })

    df = pd.DataFrame(transactions)
    return df
