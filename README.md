# Artha Vyavastha

Personal expense tracker that parses credit card statement PDFs and categorizes transactions into **Grocery**, **Car**, **Travel**, **Restaurant**, and **Miscellaneous**.

Supports: **Amex**, **Chase**, **Bank of America**, **Wells Fargo**, **Discover** — with automatic bank detection.

## Setup

```bash
git clone <repo-url>
cd arthvyavastha
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Upload one or more credit card statement PDFs. The app auto-detects which bank each statement is from, parses transactions, and categorizes them with totals and a donut chart breakdown.

## How it works

1. **PDF Parsing** — Extracts transaction tables from statement PDFs using `pypdf`
2. **Categorization** — Keyword-based classification using rules in `stores_config.json`
3. **Dashboard** — Streamlit UI with per-category totals, proportions chart, and sortable detail tables

All processing happens locally. No data leaves your machine.
