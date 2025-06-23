from parser.pdf_parser import parse_statement
from visualizer.html_report import generate_html_report
import os

def main():
    df = parse_statement("./data/bank-statement.pdf")
    if df is None:
        print("Error: Failed to parse PDF.")
        return

    os.makedirs("output", exist_ok=True)
    generate_html_report(df, "output/report.html")
    print("Report generated: output/report.html")

if __name__ == "__main__":
    main()