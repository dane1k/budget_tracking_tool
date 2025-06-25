from jinja2 import Environment, FileSystemLoader
import base64
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import os
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_html_report(df: pd.DataFrame, output_path: str = "output/report.html") -> None:
    try:
        income = df[df["amount"] > 0]
        expenses = df[df["amount"] < 0]
        
        total_income = income["amount"].sum()
        total_expenses = expenses["amount"].sum() * -1 
        net_savings = total_income - total_expenses

        if not expenses.empty:
            expenses["amount"] = expenses["amount"].abs()
            
            top_spending = (
                expenses.nlargest(5, "amount")
                [["description", "amount"]]
                .assign(amount=lambda x: "-$" + x["amount"].astype(str))
                .to_dict("records")
            )
            
            spending_by_category = (
                expenses.groupby("category")["amount"]
                .sum()
                .reset_index()
                .sort_values("amount", ascending=False)
            )
            spending_by_category["percentage"] = (spending_by_category["amount"] / total_expenses) * 100
            spending_by_category = spending_by_category.to_dict("records")
            
            pie_chart = generate_pie_chart(expenses)
        else:
            top_spending = []
            spending_by_category = []
            pie_chart = None

        env = Environment(loader=FileSystemLoader("templates"))
        template = env.get_template("report_template.html")
        
        html_output = template.render(
            date=datetime.now().strftime("%Y-%m-%d"),
            total_income=f"${total_income:,.2f}",
            total_expenses=f"${total_expenses:,.2f}" if total_expenses > 0 else "$0.00",
            net_savings=f"${net_savings:,.2f}",
            spending_by_category=[
                {
                    "name": cat["category"],
                    "amount": f"${cat['amount']:,.2f}",
                    "percentage": round(cat["percentage"], 1)
                } 
                for cat in spending_by_category
            ],
            top_spending=top_spending,
            pie_chart=pie_chart,
            has_expenses=not expenses.empty
        )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(html_output)
            
        logger.info(f"Report generated: {output_path}")

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise

def generate_pie_chart(expenses_df: pd.DataFrame) -> str:
    try:
        plt.figure(figsize=(8, 8))
        expenses_df.groupby("category")["amount"].sum().plot(
            kind="pie",
            autopct="%1.1f%%",
            startangle=90,
            colors=["#4361ee", "#3f37c9", "#4895ef", "#4cc9f0", "#f72585"],
            wedgeprops={"linewidth": 1, "edgecolor": "white"},
            textprops={"color": "white", "weight": "bold"}
        )
        plt.title("Spending by Category", pad=20)
        plt.ylabel("")
        
        buffer = BytesIO()
        plt.savefig(
            buffer,
            format="png",
            bbox_inches="tight",
            dpi=100,
            facecolor="#2b2d42"
        )
        buffer.seek(0)
        plt.close()
        
        return f"data:image/png;base64,{base64.b64encode(buffer.read()).decode()}"
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None