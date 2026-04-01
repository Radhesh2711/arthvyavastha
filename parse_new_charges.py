#!/usr/bin/env python3
import argparse
import csv
import re
import sys
from pathlib import Path


DATE_RE = re.compile(r"^(\d{2}/\d{2}/\d{2})\s+(.+)$")
AMOUNT_RE = re.compile(r"^[+-]?\$[\d,]+\.\d{2}$")
PAGE_MARKER_RE = re.compile(r"^--\s*\d+\s+of\s+\d+\s*--$")

KNOWN_TYPE_LINES = {
    "Pay Over Time",
    "and/or Cash",
    "Advance",
    "Pay In Full",
    "Cash Advance",
}

BANK_CHOICES = ["amex", "bank_of_america", "chase", "wells_fargo", "discover"]

BANK_SECTION_RULES = {
    "amex": {
        "start_markers": ["New Charges Details"],
        "end_markers": ["Fees", "Total Fees for this Period"],
        "skip_lines": {"Date Description Type Amount"},
        "default_type": "",
    },
    "bank_of_america": {
        "start_markers": ["Transactions", "Transaction Details", "Purchases and Adjustments"],
        "end_markers": ["Fees Charged", "Interest Charged", "Payment Information"],
        "skip_lines": {"Date Description Amount"},
        "default_type": "Transaction",
    },
    "chase": {
        "start_markers": ["$ Amount", "Transaction Description"],
        "end_markers": ["Total fees", "Total interest", "Year-to-date totals"],
        "skip_lines": {"Date Description Amount"},
        "default_type": "",
    },
    "wells_fargo": {
        "start_markers": ["Transactions", "Purchases, Balance Transfers and Other Debits"],
        "end_markers": ["Interest Charge Calculation", "Fees", "Important Information"],
        "skip_lines": {"Date Description Amount"},
        "default_type": "Transaction",
    },
    "discover": {
        "start_markers": ["New Transactions", "Transaction Details", "Transactions"],
        "end_markers": ["Interest Charge Calculation", "Fees", "Rewards"],
        "skip_lines": {"Date Description Amount"},
        "default_type": "Transaction",
    },
}


# Order matters: more specific banks first, Amex last (its patterns are generic).
BANK_DETECT_PATTERNS: list[tuple[str, list[str]]] = [
    ("chase", [
        "chase.com",
        "chase mobile",
        "chase freedom",
        "chase sapphire",
        "jpmorgan chase",
    ]),
    ("bank_of_america", [
        "bank of america",
        "bankofamerica.com",
        "bankofamerica",
        "bofa",
    ]),
    ("wells_fargo", [
        "wells fargo",
        "wellsfargo.com",
    ]),
    ("discover", [
        "discover bank",
        "discover.com",
        "discover it",
        "discover card",
    ]),
    ("amex", [
        "american express",
        "americanexpress.com",
        "amex",
        "pay over time",
        "new charges details",
    ]),
]


def detect_bank(pdf_path: Path) -> str | None:
    """Auto-detect bank from first two pages of PDF text. Returns bank key or None."""
    try:
        from pypdf import PdfReader
    except Exception:
        return None

    reader = PdfReader(str(pdf_path))
    if not reader.pages:
        return None

    # Scan first 2 pages for broader coverage.
    pages_to_scan = min(2, len(reader.pages))
    text = ""
    for i in range(pages_to_scan):
        text += (reader.pages[i].extract_text() or "") + "\n"
    text = text.lower()

    for bank, patterns in BANK_DETECT_PATTERNS:
        if any(p in text for p in patterns):
            return bank
    return None


def extract_pdf_lines(pdf_path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency: pypdf. Install with `python3 -m pip install pypdf`."
        ) from exc

    reader = PdfReader(str(pdf_path))
    lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        for raw in text.splitlines():
            line = raw.strip()
            if line:
                lines.append(line)
    return lines


def get_section_lines(lines: list[str]) -> list[str]:
    start_idx = None
    for i, line in enumerate(lines):
        if line == "New Charges Details":
            start_idx = i
            break
    if start_idx is None:
        raise ValueError("Could not find 'New Charges Details' section in PDF.")

    # Start after section title.
    section = lines[start_idx + 1 :]

    end_idx = None
    for i, line in enumerate(section):
        if line == "Fees" or line.startswith("Total Fees for this Period"):
            end_idx = i
            break
    if end_idx is None:
        raise ValueError("Could not find end of 'New Charges Details' section.")

    return section[:end_idx]


def get_section_lines_for_bank(lines: list[str], bank: str) -> list[str]:
    if bank == "amex":
        return get_section_lines(lines)

    rules = BANK_SECTION_RULES[bank]
    start_idx = None
    for i, line in enumerate(lines):
        if any(marker.lower() in line.lower() for marker in rules["start_markers"]):
            start_idx = i
            break
    if start_idx is None:
        raise ValueError(f"Could not find transactions section for bank '{bank}'.")

    section = lines[start_idx + 1 :]
    end_idx = None
    for i, line in enumerate(section):
        if any(marker.lower() in line.lower() for marker in rules["end_markers"]):
            end_idx = i
            break
    if end_idx is None:
        # If no clear end marker, keep a safe bounded window.
        end_idx = min(len(section), 1200)

    return section[:end_idx]


def parse_transactions(section_lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, object] | None = None

    def finalize() -> None:
        nonlocal current
        if not current:
            return
        amount = str(current.get("amount", "")).strip()
        date = str(current.get("date", "")).strip()
        desc = " ".join(str(x).strip() for x in current.get("description_lines", [])).strip()
        typ = " ".join(str(x).strip() for x in current.get("type_lines", [])).strip()
        if date and amount:
            rows.append(
                {
                    "Date": date,
                    "Description": desc,
                    "Type": typ,
                    "Amount": amount,
                }
            )
        current = None

    for line in section_lines:
        if line in {"RADHESH HARLALKA", "Card Ending 6-31000", "Date Description Type Amount"}:
            continue
        if PAGE_MARKER_RE.match(line):
            continue

        m_date = DATE_RE.match(line)
        if m_date:
            finalize()
            current = {
                "date": m_date.group(1),
                "description_lines": [m_date.group(2)],
                "type_lines": [],
                "amount": "",
                "in_type": False,
            }
            continue

        if current is None:
            continue

        if AMOUNT_RE.match(line):
            current["amount"] = line
            finalize()
            continue

        if line in KNOWN_TYPE_LINES:
            current["in_type"] = True
            current["type_lines"].append(line)
            continue

        if bool(current.get("in_type")):
            current["type_lines"].append(line)
        else:
            current["description_lines"].append(line)

    finalize()
    return rows


def parse_transactions_generic(
    section_lines: list[str], *, skip_lines: set[str], default_type: str
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    current: dict[str, object] | None = None

    date_line_re = re.compile(r"^(\d{2}/\d{2}(?:/\d{2})?)\s+(.+)$")
    amount_in_line_re = re.compile(r"(.*)\s([+-]?\$[\d,]+\.\d{2})$")

    def normalize_date(value: str) -> str:
        if value.count("/") == 1:
            return f"{value}/26"
        return value

    def finalize() -> None:
        nonlocal current
        if not current:
            return
        date = str(current.get("date", "")).strip()
        desc = " ".join(str(x).strip() for x in current.get("description_lines", [])).strip()
        amount = str(current.get("amount", "")).strip()
        if date and desc and amount:
            rows.append(
                {
                    "Date": date,
                    "Description": desc,
                    "Type": default_type,
                    "Amount": amount,
                }
            )
        current = None

    for line in section_lines:
        if line in skip_lines or PAGE_MARKER_RE.match(line):
            continue

        # Format: DATE ... $AMOUNT on same line
        m_date = date_line_re.match(line)
        if m_date:
            rest = m_date.group(2)
            m_amt = amount_in_line_re.match(rest)
            if m_amt:
                finalize()
                rows.append(
                    {
                        "Date": normalize_date(m_date.group(1)),
                        "Description": m_amt.group(1).strip(),
                        "Type": default_type,
                        "Amount": m_amt.group(2).strip(),
                    }
                )
                continue

            finalize()
            current = {
                "date": normalize_date(m_date.group(1)),
                "description_lines": [rest],
                "amount": "",
            }
            continue

        if current is None:
            continue

        if AMOUNT_RE.match(line):
            current["amount"] = line
            finalize()
        else:
            current["description_lines"].append(line)

    finalize()
    return rows


def parse_transactions_chase(
    section_lines: list[str], default_year: str = "26"
) -> list[dict[str, str]]:
    """Parse Chase statement transactions (PURCHASE rows only)."""
    rows: list[dict[str, str]] = []
    # Chase format: MM/DD     & DESCRIPTION AMOUNT  (amount has no $ sign)
    chase_line_re = re.compile(
        r"^(\d{2}/\d{2})\s+&?\s*(.+)\s+(-?[\d,]+\.\d{2})$"
    )

    for line in section_lines:
        m = chase_line_re.match(line)
        if not m:
            continue
        date = f"{m.group(1)}/{default_year}"
        desc = m.group(2).strip()
        amount_raw = m.group(3).strip()
        # Skip negative amounts (payments and credits); keep only purchases.
        if amount_raw.startswith("-"):
            continue
        amount = f"${amount_raw}"
        rows.append(
            {
                "Date": date,
                "Description": desc,
                "Type": "",
                "Amount": amount,
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Date", "Description", "Type", "Amount"])
        writer.writeheader()
        writer.writerows(rows)


def parse_pdf_to_csv(pdf_path: Path, output_path: Path, bank: str = "amex") -> int:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Input must be a PDF: {pdf_path}")
    if bank not in BANK_CHOICES:
        raise ValueError(f"Unsupported bank '{bank}'. Must be one of: {', '.join(BANK_CHOICES)}")

    lines = extract_pdf_lines(pdf_path)
    section = get_section_lines_for_bank(lines, bank)
    if bank == "amex":
        rows = parse_transactions(section)
    elif bank == "chase":
        rows = parse_transactions_chase(section)
    else:
        rules = BANK_SECTION_RULES[bank]
        rows = parse_transactions_generic(
            section,
            skip_lines=rules["skip_lines"],
            default_type=rules["default_type"],
        )
    if not rows:
        raise ValueError(f"No transaction rows found for bank '{bank}'.")
    write_csv(rows, output_path)
    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract 'New Charges Details' table from PDF(s) into CSV(s)."
    )
    parser.add_argument(
        "input_path",
        type=Path,
        help="A single PDF file path or a dataset folder containing PDFs",
    )
    parser.add_argument(
        "--bank",
        type=str,
        default="amex",
        choices=BANK_CHOICES,
        help="Bank statement type parser to use",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("processed_dataset"),
        help="Root output folder for per-PDF subfolders (default: processed_dataset)",
    )
    args = parser.parse_args()

    input_path = args.input_path
    output_root = args.output_root
    bank = args.bank

    try:
        if input_path.is_file():
            pdf_paths = [input_path]
        elif input_path.is_dir():
            pdf_paths = sorted(p for p in input_path.iterdir() if p.suffix.lower() == ".pdf")
            if not pdf_paths:
                raise ValueError(f"No PDF files found in folder: {input_path}")
        else:
            raise FileNotFoundError(f"Input path not found: {input_path}")

        for pdf_path in pdf_paths:
            out_dir = output_root / pdf_path.stem
            output_path = out_dir / f"{pdf_path.stem}.csv"
            row_count = parse_pdf_to_csv(pdf_path, output_path, bank=bank)
            print(f"Wrote {row_count} rows to: {output_path}")
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
