import pdfplumber
import re
import pandas as pd
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def categorize_transaction(description: str) -> str:
    description = description.lower()
    
    if any(x in description for x in ["pak n save", "four square", "countdown"]):
        return "Groceries"
    elif any(x in description for x in ["fuel", "mobil", "z ", "bp ", "gas station"]):
        return "Transport"
    elif "cityfitness" in description or "gym" in description:
        return "Fitness"
    elif any(x in description for x in ["kfc", "mcdonalds", "burger king"]):
        return "Eating Out"
    elif any(x in description for x in ["spotify", "netflix", "youtube premium"]):
        return "Subscriptions"
    elif any(x in description for x in ["credit", "deposit", "salary", "ird"]):
        return "Income"
    else:
        return "Other"

def parse_statement(pdf_path: str) -> Optional[pd.DataFrame]:
    transactions = []
    prev_balance = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                for line in text.split("\n"):
                    match = re.match(
                        r"^(\d{2} \w{3})\s+([A-Z]{2})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})$", 
                        line.strip()
                    )
                    if match:
                        date, tx_type, desc, amount_str, balance_str = match.groups()
                        
                        amount = float(amount_str.replace(",", ""))
                        balance = float(balance_str.replace(",", ""))
                        
                        if prev_balance is not None:
                            if balance > prev_balance:
                                tx_type = "CR"
                                amount = abs(amount)
                            else:
                                tx_type = "DR" 
                                amount = -abs(amount)
                        
                        category = categorize_transaction(desc)
                        transactions.append({
                            "date": date,
                            "type": tx_type,
                            "description": desc.strip(),
                            "amount": amount,
                            "balance": balance,
                            "category": category
                        })
                        prev_balance = balance
        
        return pd.DataFrame(transactions)
    
    except Exception as e:
        logger.error(f"Error parsing PDF: {e}")
        return None