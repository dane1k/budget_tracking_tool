import os
import re
import json
import pdfplumber
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("set OPENAI_API_KEY in your .env")

client = OpenAI(api_key=api_key)

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        return "\n".join(page.extract_text() for page in pdf.pages)

def parse_transactions(text, year):
    lines = text.splitlines()
    transactions = []
    pattern = re.compile(r"(\d{1,2} [A-Za-z]{3})\s+(.+?)\s+(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)$")
    for line in lines:
        match = pattern.search(line)
        if match:
            date_str, description, amount_str = match.groups()
            try:
                amount = float(amount_str.replace("$", "").replace(",", ""))
                date = pd.to_datetime(f"{date_str} {year}", format="%d %b %Y")
                transactions.append([date.strftime("%Y-%m-%d"), description.strip(), amount])
            except:
                continue
    return pd.DataFrame(transactions, columns=["date", "description", "amount"])

def build_prompt(df):
    table = df.to_markdown(index=False)
    prompt = f"""
You are a financial assistant.

Here's a table of bank transactions:

{table}

Tasks:
1. Automatically assign a category to each transaction based on its description. Make up reasonable categories (food, rent, transport, subscriptions, etc.)
2. For each category, calculate total expenses (amount < 0) grouped by month (format YYYY-MM)
3. Return a valid JSON in this format:

{{
  "food": {{
    "2025-03": 123.45,
    "2025-04": 234.56
  }},
  "subscriptions": {{
    "2025-03": 12.99
  }}
}}

Notes:
- Only include negative amounts (expenses)
- Only include months/categories with expenses
- Return valid JSON only, no explanation or formatting
"""
    return prompt

def ask_openai(df):
    prompt = build_prompt(df)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def parse_response(text):
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception as e:
        print("⚠️ Failed to parse JSON:", e)
        print("Raw GPT response:\n", text)
        return {}

def save_to_excel(data, filename="annual_expenses.xlsx"):
    if not data:
        print("⚠️ No data to write.")
        return
    df = pd.DataFrame(data).fillna(0).T
    df.index.name = "category"
    df = df.sort_index()
    df = df.reindex(sorted(df.columns), axis=1)
    df.to_excel(filename)
    print(f"✅ Excel report saved as {filename}")

def main():
    file_path = "./data/bank-statement.pdf"
    if not os.path.exists(file_path):
        print("❌ File not found:", file_path)
        return
    print("📄 Extracting text from PDF...")
    text = extract_text_from_pdf(file_path)
    print("🔍 Parsing transactions...")
    df = parse_transactions(text, year=2025)
    print(f"📊 Parsed {len(df)} transactions.")
    if df.empty:
        print("⚠️ No transactions found.")
        return
    print("🤖 Sending to OpenAI for analysis...")
    gpt_response = ask_openai(df)
    print("📥 Parsing GPT response...")
    data = parse_response(gpt_response)
    print("💾 Saving to Excel...")
    save_to_excel(data)

if __name__ == "__main__":
    main()
