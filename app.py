#!/usr/bin/env python3
import csv
from decimal import Decimal
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

from expense_segregation import load_rules
from expense_segregation import process_single_pdf
from parse_new_charges import BANK_CHOICES
from parse_new_charges import detect_bank

DATASET_DIR = Path("dataset")
OUTPUT_ROOT = Path("processed_dataset")

CATEGORIES = ["grocery", "car", "travel", "restaurant", "miscellaneous"]

BANK_DISPLAY = {
    "amex": "Amex",
    "bank_of_america": "Bank of America",
    "chase": "Chase",
    "wells_fargo": "Wells Fargo",
    "discover": "Discover",
}


def ensure_dirs() -> None:
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)


def sum_amounts_from_csv(csv_path: Path) -> Decimal:
    total = Decimal("0.00")
    if not csv_path.exists():
        return total
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            amount = row.get("Amount", "").replace("$", "").replace(",", "").strip()
            if amount:
                total += Decimal(amount)
    return total


def read_category_details(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.exists():
        return []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    details: list[dict[str, str]] = []
    for row in rows:
        details.append(
            {
                "Date": row.get("Date", ""),
                "Description": row.get("Description", ""),
                "Amount": row.get("Amount", ""),
            }
        )
    return details


def sorted_details(
    rows: list[dict[str, str]], sort_by: str, ascending: bool
) -> list[dict[str, str]]:
    if sort_by == "Date":
        def date_key(row: dict[str, str]) -> tuple[int, int, int]:
            mm, dd, yy = row.get("Date", "00/00/00").split("/")
            return (int(yy), int(mm), int(dd))

        return sorted(rows, key=date_key, reverse=not ascending)

    if sort_by == "Amount":
        def amount_key(row: dict[str, str]) -> Decimal:
            raw = row.get("Amount", "").replace("$", "").replace(",", "").strip()
            if not raw:
                return Decimal("0.00")
            return Decimal(raw)

        return sorted(rows, key=amount_key, reverse=not ascending)

    return rows


def main() -> None:
    st.set_page_config(page_title="Expense Segregator", layout="centered")
    st.markdown(
        """
        <style>
        /* Selected values chips in multiselect */
        [data-baseweb="tag"] {
            background-color: #d9f2d9 !important;
        }
        [data-baseweb="tag"] span {
            color: #1b5e20 !important;
        }
        /* Category row: single horizontal line */
        .category-row {
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            margin-bottom: 0.8rem;
        }
        .category-row .cat-item {
            flex: 1;
            text-align: center;
            padding: 0.55rem 0.3rem;
            border-radius: 0.6rem;
        }
        .category-row .cat-item.cat-grocery   { background: rgba(46,125,50,0.10); }
        .category-row .cat-item.cat-car        { background: rgba(239,108,0,0.10); }
        .category-row .cat-item.cat-travel     { background: rgba(21,101,192,0.10); }
        .category-row .cat-item.cat-restaurant { background: rgba(106,27,154,0.10); }
        .category-row .cat-item.cat-misc       { background: rgba(198,40,40,0.10); }
        .category-row .cat-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .cat-grocery .cat-label   { color: #2E7D32; }
        .cat-car .cat-label        { color: #EF6C00; }
        .cat-travel .cat-label     { color: #1565C0; }
        .cat-restaurant .cat-label { color: #6A1B9A; }
        .cat-misc .cat-label       { color: #C62828; }
        .category-row .cat-value {
            font-size: 1.05rem;
            font-weight: 600;
            white-space: nowrap;
        }
        /* Total expense centered */
        .total-row {
            text-align: center;
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;
        }
        .total-row .total-label {
            font-size: 0.85rem;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .total-row .total-value {
            font-size: 1.8rem;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h1 style='text-align: center;'>Artha Vyavastha</h1>"
        "<p style='text-align: center; color: #888;'>Upload one or more credit card statement PDFs to track expenses.</p>",
        unsafe_allow_html=True,
    )

    ensure_dirs()
    rules = load_rules(Path("stores_config.json"))
    grocery_store_options = list(rules.get("grocery_store_aliases", {}).keys())

    selected_grocery_stores = st.multiselect(
        "Grocery stores I usually visit",
        options=grocery_store_options,
        default=grocery_store_options,
    )

    uploaded_files = st.file_uploader(
        "Upload statement PDFs", type=["pdf"], accept_multiple_files=True
    )
    if not uploaded_files:
        return

    # Save files, auto-detect banks
    pdf_paths: list[Path] = []
    detected_banks: dict[str, str] = {}
    undetected: list[str] = []

    for uf in uploaded_files:
        pdf_path = DATASET_DIR / uf.name
        pdf_path.write_bytes(uf.getbuffer())
        pdf_paths.append(pdf_path)
        bank = detect_bank(pdf_path)
        if bank:
            detected_banks[uf.name] = bank
        else:
            undetected.append(uf.name)

    # Show detected banks and let user override / pick for undetected
    if detected_banks:
        st.markdown("**Detected banks:**")
        for name, bank in detected_banks.items():
            display = BANK_DISPLAY.get(bank, bank.replace("_", " ").title())
            st.write(f"- {name} → {display}")

    file_banks: dict[str, str] = dict(detected_banks)
    if undetected:
        st.warning("Could not auto-detect bank for the following files:")
        for name in undetected:
            file_banks[name] = st.selectbox(
                f"Select bank for {name}",
                options=BANK_CHOICES,
                index=0,
                format_func=lambda x: BANK_DISPLAY.get(x, x.replace("_", " ").title()),
                key=f"bank_{name}",
            )

    # Process all PDFs
    results: list[dict] = []
    output_folders: list[Path] = []
    errors: list[str] = []

    with st.spinner("Processing PDFs..."):
        for pdf_path in pdf_paths:
            try:
                result = process_single_pdf(
                    pdf_path,
                    OUTPUT_ROOT,
                    Path("stores_config.json"),
                    bank=file_banks[pdf_path.name],
                    selected_grocery_stores=selected_grocery_stores,
                )
                results.append(result)
                output_folders.append(Path(result["output_folder"]))
            except Exception as exc:
                errors.append(f"{pdf_path.name}: {exc}")

    if errors:
        for err in errors:
            st.error(err)
    if not results:
        return

    st.success(f"Processed {len(results)} statement(s).")

    # Aggregate totals across all processed PDFs
    totals: dict[str, Decimal] = {cat: Decimal("0.00") for cat in CATEGORIES}
    all_details: dict[str, list[dict[str, str]]] = {cat: [] for cat in CATEGORIES}

    cat_filenames = {
        "grocery": "grocery.csv",
        "car": "car.csv",
        "travel": "travel.csv",
        "restaurant": "restaurant.csv",
        "miscellaneous": "miscellaneous.csv",
    }

    for folder in output_folders:
        for cat, fname in cat_filenames.items():
            csv_path = folder / fname
            totals[cat] += sum_amounts_from_csv(csv_path)
            all_details[cat].extend(read_category_details(csv_path))

    grocery_total = totals["grocery"]
    car_total = totals["car"]
    travel_total = totals["travel"]
    restaurant_total = totals["restaurant"]
    misc_total = totals["miscellaneous"]
    total_expense = sum(totals.values())

    st.markdown(
        f"""
        <div class="category-row">
            <div class="cat-item cat-grocery"><div class="cat-label">Grocery</div><div class="cat-value">${grocery_total:.2f}</div></div>
            <div class="cat-item cat-car"><div class="cat-label">Car</div><div class="cat-value">${car_total:.2f}</div></div>
            <div class="cat-item cat-travel"><div class="cat-label">Travel</div><div class="cat-value">${travel_total:.2f}</div></div>
            <div class="cat-item cat-restaurant"><div class="cat-label">Restaurant</div><div class="cat-value">${restaurant_total:.2f}</div></div>
            <div class="cat-item cat-misc"><div class="cat-label">Misc</div><div class="cat-value">${misc_total:.2f}</div></div>
        </div>
        <div class="total-row">
            <div class="total-label">Total Expense</div>
            <div class="total-value">${total_expense:.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Expense Proportions")
    labels = ["Grocery", "Car", "Travel", "Restaurant", "Misc"]
    values = [float(grocery_total), float(car_total), float(travel_total), float(restaurant_total), float(misc_total)]
    colors = ["#2E7D32", "#EF6C00", "#1565C0", "#6A1B9A", "#C62828"]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.6,
                marker={"colors": colors},
                textinfo="none",
                hoverlabel={"font": {"size": 18}},
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "<b>$%{value:,.2f}</b><br>"
                    "<b>%{percent}</b>"
                    "<extra></extra>"
                ),
            )
        ]
    )
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Details")
    selected_category = st.selectbox(
        "Choose category",
        CATEGORIES,
        index=0,
    )
    detail_rows = all_details[selected_category]
    s1, s2 = st.columns(2)
    sort_by = s1.selectbox("Sort by", ["Date", "Amount"], index=0)
    sort_order = s2.selectbox("Order", ["Ascending", "Descending"], index=0)
    detail_rows = sorted_details(detail_rows, sort_by, sort_order == "Ascending")
    st.write(f"Showing {len(detail_rows)} rows for **{selected_category}**")
    st.dataframe(detail_rows, use_container_width=True)


if __name__ == "__main__":
    main()
