import re
import pandas as pd
import pdfplumber
from openai import OpenAI
import webbrowser
from dotenv import load_dotenv
import os
import json
from openai import OpenAI

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("API key is not set in .env")

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

def ask_openai(df):
    if df.empty:
        return "Error: No transactions parsed from the file."

    df_small = df.tail(50)
    table_md = df_small.to_markdown(index=False)

    prompt = f"""
You are a financial analyst. Here is a markdown table with the last {len(df_small)} transactions:

{table_md}

Please analyze the data:
1. Categorize transactions (e.g., food, transport, housing, etc.)
2. Calculate total expenses and income per category.
3. Return the summary in two formats:
  a) A textual analytical report.
  b) A JSON object with categories as keys and their income/expense sums as values.

Example of JSON format:
{{
  "Food": {{"income": 0, "expense": 150.0}},
  "Salary": {{"income": 2000.0, "expense": 0}},
  "Transport": {{"income": 0, "expense": 100.0}}
}}

Return only the textual report followed by the JSON on a new line.
"""

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def parse_report_and_data(response_text):
    start = response_text.rfind("{")
    end = response_text.rfind("}")
    if start == -1 or end == -1 or end < start:
        print("json block not found in response.")
        return None, response_text
    json_str = response_text[start:end+1]

    json_str = json_str.strip().strip("`").strip()

    try:
        data = json.loads(json_str)
        text_without_json = response_text[:start].strip()
        return data, text_without_json
    except Exception as e:
        print(f"failed to decode JSON: {e}")
        return None, response_text


def save_summary_to_excel(summary_data, filename="summary.xlsx"):
    if not summary_data:
        print("No summary data to save.")
        return
    df_summary = pd.DataFrame.from_dict(summary_data, orient="index")
    df_summary.to_excel(filename)
    print(f"Summary saved to {filename}")

def save_html(report_text, output_path="result.html"):
    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Analysis Result</title>
    </head>
    <body>
        <h1>Financial Analysis by ChatGPT</h1>
        <pre style="font-family: monospace; white-space: pre-wrap;">{report_text}</pre>
    </body>
    </html>
    """

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    webbrowser.open(f"file://{os.path.abspath(output_path)}")

if __name__ == "__main__":
    file_path = "./data/bank-statement.pdf"
    if not os.path.exists(file_path):
        print(f"file not found: {file_path}")
        exit()

    print(f"extracting text from {file_path} ...")
    text = extract_text_from_pdf(file_path)

    YEAR = 2025

    print("parsing transactions from text...")
    df = parse_transactions(text, YEAR)
    print(f"Found transactions: {len(df)}")

    if df.empty:
        print("no transactions found for analysis please check file format")
        exit()

    print("please enter the analysis period")
    input_start = input("Start date (format YYYY-MM-DD), e.g. 2025-05-01: ")
    input_end = input("End date (format YYYY-MM-DD), e.g. 2025-06-09: ")

    try:
        start_date = pd.to_datetime(input_start)
        end_date = pd.to_datetime(input_end)
    except Exception:
        print("invalid date format")
        exit()

    df_filtered = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    print(f"Filtered transactions: {len(df_filtered)}")

    if df_filtered.empty:
        print("yo, here's no transactions found in the selected period")
        exit()

    print("sending data to chatgpt:) for analysis...")
    response_text = ask_openai(df_filtered)

    summary_data, report_text = parse_report_and_data(response_text)

    print("trying to save excel summary...")
    save_summary_to_excel(summary_data)

    print("Saving html report...")
    save_html(report_text)

    print("The report is opened in your browser, and Excel summary saved")
