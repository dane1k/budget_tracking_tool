import pdfplumber
import re
import pandas as pd
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def categorize_transaction(description: str) -> str:
    description = description.lower()

    if any(x in description for x in ["pak n save", "four square", "woolworths", "countdown"]):
        return "Groceries"
    elif any(x in description for x in ["fuel", "mobil", "z ", "bp ", "gas station"]):
        return "Transport"
    elif "cityfitness" in description or "gym" in description:
        return "Fitness"
    elif any(x in description for x in ["kfc", "dominos", "mcdonalds", "subway", "burger king", "pizza hut"]):
        return "Eating Out"
    elif any(x in description for x in ["google one", "spotify", "netflix", "youtube premium"]):
        return "Subscriptions"
    elif any(x in description for x in ["credit transfer", "ird", "deposit", "salary"]):
        return "Income"
    elif any(x in description for x in ["medical", "doctor", "pharmacy"]):
        return "Health"
    else:
        return "Other"

def parse_statement(pdf_path: str) -> Optional[pd.DataFrame]:
    transactions = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split("\n"):
                    match = re.match(
                        r"^(\d{2} \w{3})\s+([A-Z]{2})\s+(.+?)\s+([-+]?\d+\.\d{2})\s+([-+]?\d+\.\d{2})$", 
                        line.strip()
                    )
                    if match:
                        date, tx_type, desc, amount, balance = match.groups()
                        amount = float(amount)
                        if tx_type == "DR":
                            amount = -abs(amount)
                        category = categorize_transaction(desc)
                        transactions.append({
                            "date": date,
                            "type": tx_type,
                            "description": desc.strip(),
                            "amount": amount,
                            "balance": float(balance),
                            "category": category
                        })
        return pd.DataFrame(transactions)
    except Exception as e:
        logger.error(f"PDF parsing error: {e}")
        return None