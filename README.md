# Budget Tracking Tool

A simple CLI tool for tracking and categorizing personal finances using exported bank `.pdf` files.  
Built with Python for quick insights into where your money goes.

---

## Features

- 📂 Parses exported `.pdf` transaction files
- 🧠 Auto-categorizes transactions based on description
- 📊 Summarizes total spending per category
- 💾 Saves cleaned and categorized data
- 🛠 Easy to customize

---

## Installation

```bash
git clone https://github.com/dane1k/budget_tracking_tool.git
cd budget_tracking_tool
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

1. Export your bank transactions to `.pdf` format.
2. Place the file (e.g. `bank-statement.pdf`) in the root folder or `/data`.
3. Run the tool:

```bash
python main.py
```

4. Follow the prompts in the terminal.

> You can change the input/output file path in `main.py`.

---

## Project Structure

```
budget_tracking_tool/
├── data/                   # CSV input/output folder
├── main.py                 # Main script to run
├── categorizer.py          # Logic for categorizing transactions
├── parser.py               # CSV reader/formatter
├── utils.py                # Helper functions
├── requirements.txt
└── README.md
```

---

## Customization

You can modify how transactions are categorized by editing `categorizer.py`:

```python
def categorize_transaction(description: str) -> str:
    description = description.lower()

    if "pak n save" in description:
        return "Groceries"
    elif "uber" in description:
        return "Transport"
    # Add more rules here
```

---

## Example Output

```
=== Budget Summary ===
Groceries: $120.45
Transport: $34.20
Dining Out: $52.00
Total: $206.65
```

---

## Roadmap / TODO

- [ ] Add multi-language support
- [ ] GUI or web interface
- [ ] Graphs for monthly spending
- [ ] Save user preferences
- [ ] Import multiple CSVs at once

---

## License

MIT License — feel free to fork, use, and contribute!
