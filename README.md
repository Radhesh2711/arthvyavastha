# Artha Vyavastha

Personal expense tracker that parses credit card statement PDFs and categorizes transactions into **Grocery**, **Car**, **Travel**, **Restaurant**, and **Miscellaneous**.

Supports: **Amex**, **Chase**, **Bank of America**, **Wells Fargo**, **Discover** — with automatic bank detection.

## Quick Start

**Prerequisites:** Python 3.10+ installed on your machine.

**macOS / Linux:**
```bash
git clone <repo-url>
cd arthvyavastha
./setup.sh
```

**Windows:**
```bash
git clone <repo-url>
cd arthvyavastha
setup.bat
```

The script creates a virtual environment, installs dependencies, and launches the app. Your browser will open automatically.

**Next time**, just run `./setup.sh` (or `setup.bat`) again — it skips setup if already done.

## Usage

1. Select the grocery stores you visit (all pre-selected by default)
2. Upload one or more credit card statement PDFs (drag & drop or browse)
3. The app auto-detects which bank each statement is from
4. View category totals, donut chart breakdown, and sortable detail tables
5. Press `Ctrl+C` in the terminal to stop the app

## How it works

1. **PDF Parsing** — Extracts transaction tables from statement PDFs using `pypdf`
2. **Categorization** — Keyword-based classification using rules in `stores_config.json`
3. **Dashboard** — Streamlit UI with per-category totals, proportions chart, and sortable detail tables

All processing happens locally. No data leaves your machine.
