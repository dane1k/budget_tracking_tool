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
    df_small = df.tail(50)
    table_md = df_small.to_markdown(index=False)
    prompt = f"""
you are a financial analyst

given the following transactions table in markdown

{table_md}

tasks
1) assign each transaction a category (e.g. food, salary, transport, housing, fitness, gaming, technology, deposit, finance)
2) return a JSON with:
   - incomes: list of income transactions (amount > 0) with category
   - expenses: list of expense transactions (amount < 0) with category
   - summary: dictionary where each category has income and expense totals

format:
{{
  "incomes": [
    {{"date": "2025-05-01", "description": "salary", "amount": 2000.00, "category": "salary"}}
  ],
  "expenses": [
    {{"date": "2025-05-02", "description": "pak n save", "amount": -50.00, "category": "food"}}
  ],
  "summary": {{
    "salary": {{"income": 2000.00, "expense": 0}},
    "food": {{"income": 0, "expense": 50.00}}
  }}
}}

return only valid JSON without explanation or comments
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
    input_start = input("start date (yyyy-mm-dd), e.g. 2025-05-01: ")
    input_end = input("end date (yyyy-mm-dd), e.g. 2025-06-09: ")
    try:
        start_date = pd.to_datetime(input_start)
        end_date = pd.to_datetime(input_end)
    except Exception:
        print("invalid date format")
        return
    df_filtered = df[(df["date"] >= start_date) & (df["date"] <= end_date)]
    print(f"filtered transactions {len(df_filtered)}")
    if df_filtered.empty:
        print("no transactions found in this period")
        return
    print("sending data to openai for analysis")
    response_text = ask_openai_for_analysis(df_filtered)
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
