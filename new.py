import os
import re
import json
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI
import webbrowser
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("set OPENAI_API_KEY environment variable")

client = OpenAI(api_key=api_key)

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
    return full_text

def parse_transactions(text, year):
    lines = text.splitlines()
    transactions = []
    pattern = re.compile(r"(\d{1,2} [A-Za-z]{3})\s+(.+?)\s+(-?\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)$")
    for line in lines:
        match = pattern.search(line)
        if match:
            date_str = match.group(1)
            description = match.group(2).strip()
            amount_str = match.group(3).replace("$", "").replace(",", "")
            try:
                amount = float(amount_str)
                date = pd.to_datetime(f"{date_str} {year}", format="%d %b %Y")
            except Exception:
                continue
            transactions.append([date, description, amount])
    df = pd.DataFrame(transactions, columns=["date", "description", "amount"])
    return df

def build_prompt(df):
    table_md = df.to_markdown(index=False)
    prompt = f"""
You are a financial assistant

Here is a table of financial transactions with the following columns:
- date (format YYYY-MM-DD)
- description
- amount (positive = income, negative = expense)

{table_md}

Instructions:
1. Group transactions into categories you think are appropriate (e.g., food, transport, subscriptions, etc.).
2. For each category, sum the expenses (amount < 0) per month.
3. Output the result as a JSON with this format:

{{
  "Food": {{
    "2025-03": 123.45,
    "2025-04": 99.99,
    "2025-05": 210.00,
    "2025-06": 0.00
  }},
  "Transport": {{
    "2025-03": 20.00,
    ...
  }}
}}

Do not explain anything. Return only valid JSON with categories as top-level keys and months as subkeys.
"""
    return prompt

def ask_openai_for_analysis(df):
    prompt = build_prompt(df)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def parse_openai_response(text):
    start = text.find("{")
    end = text.rfind("}") + 1
    json_str = text[start:end]
    return json.loads(json_str)

def save_to_excel(data, filename="financial_report.xlsx"):
    df_incomes = pd.DataFrame(data.get("incomes", []))
    df_expenses = pd.DataFrame(data.get("expenses", []))
    df_summary = pd.DataFrame(data.get("summary", {})).T

    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:
        if not df_incomes.empty:
            df_incomes.to_excel(writer, sheet_name="incomes", index=False)
        if not df_expenses.empty:
            df_expenses.to_excel(writer, sheet_name="expenses", index=False)
        if not df_summary.empty:
            df_summary.to_excel(writer, sheet_name="summary")

            workbook = writer.book
            worksheet = writer.sheets["summary"]

            plt.figure(figsize=(8,5))
            df_summary["expense"].plot(kind="bar", color="tomato", title="expenses by category")
            plt.ylabel("amount")
            plt.tight_layout()
            plt.savefig("expenses.png")
            plt.close()

            worksheet.insert_image("D2", "expenses.png")

        if not df_expenses.empty:
            df_expenses["date"] = pd.to_datetime(df_expenses["date"])
            df_expenses["month"] = df_expenses["date"].dt.strftime("%b")
            pivot = df_expenses.pivot_table(index="category", columns="month", values="amount", aggfunc="sum", fill_value=0)
            pivot = pivot.reindex(columns=["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
            pivot.to_excel(writer, sheet_name="monthly_budget")

def main():
    file_path = "./data/bank-statement.pdf"
    if not os.path.exists(file_path):
        print(f"file not found {file_path}")
        return

    print(f"extracting text from {file_path}")
    text = extract_text_from_pdf(file_path)
    YEAR = 2025
    print("parsing transactions from text")
    df = parse_transactions(text, YEAR)
    print(f"found transactions {len(df)}")

    if df.empty:
        print("no transactions found please check the pdf format")
        return

    print("sending data to openai for analysis")
    response_text = ask_openai_for_analysis(df)

    print("parsing openai response")
    try:
        data = parse_openai_response(response_text)
    except Exception as e:
        print("failed to parse json from openai response", e)
        print("raw response", response_text)
        return

    print("saving data to excel")
    save_to_excel(data)
    print("done excel report saved as financial_report.xlsx")
    webbrowser.open(os.path.abspath("financial_report.xlsx"))

if __name__ == "__main__":
    main()
