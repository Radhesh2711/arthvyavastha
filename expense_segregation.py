#!/usr/bin/env python3
import argparse
import csv
import json
import re
from decimal import Decimal
from pathlib import Path

from parse_new_charges import BANK_CHOICES
from parse_new_charges import parse_pdf_to_csv


DEFAULT_RULES = {
    "ignore_patterns": [
        r"((walmart|wal-?mart)\s*\+\s*member|(walmart|wal-?mart|wmt)\s*plus(\s*member)?)"
    ],
    "special_misc_patterns": [r"uber\s*costco"],
    "categories": {
        "car": [
            "turo",
            "uber",
            "lyft",
            "walmart fuel",
            "wal-mart fuel",
            "chevron",
            "circlek",
            "circle k",
            "shell",
            "bp",
            "exxon",
            "mobil",
            "marathon petro",
            "marathon gas",
            "valero",
            "sunoco",
            "citgo",
            "phillips 66",
            "conoco",
            "texaco",
            "sinclair",
            "speedway",
            "quiktrip",
            "quik trip",
            "wawa",
            "sheetz",
            "racetrac",
            "murphy usa",
            "murphy express",
            "casey's",
            "pilot travel",
            "pilot flying",
            "flying j",
            "love's travel",
            "loves travel",
            "7-eleven fuel",
            "buc-ee",
            "bucees",
            "maverik",
            "kwik trip",
            "kwik star",
            "kroger fuel",
            "heb fuel",
            "h-e-b fuel",
            "costco gas",
            "costco gasoline",
            "sam's club fuel",
            "sams club fuel",
            "bj's fuel",
            "fuel",
            "gasoline",
            "petroleum",
            "geico",
            "state farm",
            "progressive ins",
            "progressive *ins",
            "progressive casualty",
            "allstate",
            "usaa",
            "liberty mutual",
            "nationwide ins",
            "nationwide mutual",
            "farmers ins",
            "travelers ins",
            "travelers indemnity",
            "erie insurance",
            "root insurance",
            "lemonade ins",
            "auto ins",
            "car ins",
            "ntta",
            "tolltag",
            "txtag",
            "e-zpass",
            "ezpass",
            "sunpass",
            "fastrak",
            "platepass",
            "parking",
            "hertz",
            "enterprise rent",
            "avis",
            "budget rent",
            "national car",
        ],
        "grocery": [
            "walmart",
            "wal-mart",
            "braums",
            "tom thumb",
            "india bazaar",
            "costco",
            "market place",
            "ralphs",
            "patel brothers",
            "patel bro",
            "kroger",
            "aldi",
            "trader joe",
            "whole foods",
            "safeway",
            "publix",
            "h-e-b",
            "heb ",
            "meijer",
            "winco",
            "food lion",
            "giant food",
            "giant eagle",
            "stop & shop",
            "stop and shop",
            "shoprite",
            "wegmans",
            "sprouts",
            "harris teeter",
            "piggly wiggly",
            "winn-dixie",
            "winn dixie",
            "food city",
            "bi-lo",
            "save-a-lot",
            "save a lot",
            "food 4 less",
            "food4less",
            "stater bros",
            "vons",
            "albertsons",
            "jewel-osco",
            "jewel osco",
            "acme market",
            "hannaford",
            "shaw's",
            "shaws",
            "price chopper",
            "market basket",
            "grocery",
            "supermarket",
            "fresh market",
            "fresh thyme",
            "natural grocers",
            "earth fare",
            "99 ranch",
            "h mart",
            "hmart",
            "lotte plaza",
            "mitsuwa",
            "ranch 99",
            "sam's club",
            "sams club",
            "bj's wholesale",
            "bjs wholesale",
        ],
        "travel": [
            "airline",
            "airlines",
            "airways",
            "american air",
            "delta air",
            "united air",
            "southwest air",
            "jetblue",
            "jet blue",
            "spirit air",
            "frontier air",
            "alaska air",
            "hawaiian air",
            "sun country",
            "allegiant",
            "breeze airways",
            "avelo",
            "qatar",
            "emirates",
            "british airways",
            "lufthansa",
            "air france",
            "klm",
            "air india",
            "air canada",
            "westjet",
            "turkish air",
            "singapore air",
            "cathay pacific",
            "japan air",
            "ana ",
            "korean air",
            "qantas",
            "virgin atlantic",
            "icelandair",
            "aer lingus",
            "swiss air",
            "iberia",
            "tap air",
            "scandinavian air",
            "copa air",
            "avianca",
            "latam",
            "volaris",
            "aeromexico",
            "interjet",
            "vivaaerobus",
            "etihad",
            "saudia",
            "oman air",
            "air new zealand",
            "fiji airways",
            "expedia",
            "booking.com",
            "priceline",
            "kayak",
            "orbitz",
            "travelocity",
            "hopper",
            "skiplagged",
            "kiwi.com",
            "passenger ticket",
            "date of departure",
            "amtrak",
            "greyhound",
            "flixbus",
            "megabus",
            "peter pan bus",
            "trailways",
            "ourbus",
            "redcoach",
            "barons bus",
            "wanderu",
            "busbud",
            "gotobus",
            "brightline",
            "caltrain",
            "metra",
            "metro-north",
            "metro north",
            "nj transit",
            "lirr",
            "septa",
            "marta",
            "dart ",
            "trimet",
            "wmata",
            "metrolink",
            "coaster",
            "ace rail",
            "via rail",
            "rail pass",
            "trainline",
        ],
        "restaurant": [
            "restaurant",
            "pizza",
            "taco",
            "taco bell",
            "subway",
            "panda express",
            "grill",
            "bbq",
            "sushi",
            "curry",
            "thai",
            "indian cuisin",
            "cafe",
            "caffe",
            "coffee",
            "starbucks",
            "velvet taco",
            "summer moon",
            "simply south",
            "hashtag india",
            "bambu thai",
            "eataly",
            "haagen dazs",
            "amorino",
            "el charrito",
            "el favorito",
            "golden boy pizza",
            "spaghetteria",
            "apna punjab",
            "madina halal",
            "ka thai",
            "elia greek",
            "espumoso",
            "the monk",
            "rockn wraps",
            "blue bottle",
            "beans & bubbles",
            "fat ni bbq",
            "hot pizza",
            "bravo farms",
            "karya siddhi",
        ],
    },
    "grocery_store_aliases": {
        "Walmart": ["walmart", "wal-mart"],
        "Costco": ["costco"],
        "Tom Thumb": ["tom thumb"],
        "Braums": ["braums"],
        "Patel Brothers": ["patel brothers", "patel bro"],
        "India Bazaar": ["india bazaar"],
        "Ralphs": ["ralphs"],
        "Safeway": ["safeway"],
        "Aldi's": ["aldi", "aldi's"],
        "Kroger": ["kroger"],
    },
}


def load_rules(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        return DEFAULT_RULES

    with config_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    rules = {
        "ignore_patterns": loaded.get(
            "ignore_patterns", DEFAULT_RULES["ignore_patterns"]
        ),
        "special_misc_patterns": loaded.get(
            "special_misc_patterns", DEFAULT_RULES["special_misc_patterns"]
        ),
        "categories": loaded.get("categories", DEFAULT_RULES["categories"]),
        "grocery_store_aliases": loaded.get(
            "grocery_store_aliases", DEFAULT_RULES["grocery_store_aliases"]
        ),
    }

    categories = rules["categories"]
    if not isinstance(categories, dict):
        raise ValueError("Invalid config: 'categories' must be an object.")
    if "car" not in categories or "grocery" not in categories:
        raise ValueError("Invalid config: categories must include 'car' and 'grocery'.")
    return rules


def resolve_grocery_keywords(
    rules: dict[str, object], selected_grocery_stores: list[str] | None
) -> list[str]:
    aliases = rules.get("grocery_store_aliases", {})
    if not isinstance(aliases, dict):
        return list(rules.get("categories", {}).get("grocery", []))

    if selected_grocery_stores is None:
        selected = list(aliases.keys())
    else:
        selected = selected_grocery_stores

    resolved: list[str] = []
    for store_name in selected:
        keywords = aliases.get(store_name, [])
        resolved.extend(str(k).lower() for k in keywords)
    return resolved


def classify_row(
    description: str,
    rules: dict[str, object],
    selected_grocery_stores: list[str] | None = None,
) -> str | None:
    text = description.lower()
    ignore_patterns = [
        re.compile(p, re.IGNORECASE) for p in rules.get("ignore_patterns", [])
    ]
    special_misc_patterns = [
        re.compile(p, re.IGNORECASE) for p in rules.get("special_misc_patterns", [])
    ]
    categories = rules.get("categories", {})
    car_keywords = categories.get("car", [])
    grocery_keywords = resolve_grocery_keywords(rules, selected_grocery_stores)

    if any(p.search(description) for p in ignore_patterns):
        return None

    if any(p.search(description) for p in special_misc_patterns):
        return "miscellaneous"

    # Car checks must come before grocery checks so fuel-like strings
    # are not misclassified as grocery.
    if any(keyword.lower() in text for keyword in car_keywords):
        return "car"
    if any(keyword.lower() in text for keyword in grocery_keywords):
        return "grocery"
    travel_keywords = categories.get("travel", [])
    if any(keyword.lower() in text for keyword in travel_keywords):
        return "travel"
    restaurant_keywords = categories.get("restaurant", [])
    if any(keyword.lower() in text for keyword in restaurant_keywords):
        return "restaurant"
    return "miscellaneous"


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def segregate_csv(
    input_csv: Path,
    output_dir: Path,
    rules: dict[str, object],
    selected_grocery_stores: list[str] | None = None,
) -> dict[str, int]:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_csv}")

    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("Input CSV has no header.")
        fieldnames = reader.fieldnames
        rows = list(reader)

    required = {"Date", "Description", "Type", "Amount"}
    if not required.issubset(set(fieldnames)):
        raise ValueError(
            "Input CSV missing required columns: Date, Description, Type, Amount"
        )

    grouped: dict[str, list[dict[str, str]]] = {
        "grocery": [],
        "car": [],
        "travel": [],
        "restaurant": [],
        "miscellaneous": [],
    }
    ignored_rows = 0

    for row in rows:
        category = classify_row(
            row.get("Description", ""),
            rules,
            selected_grocery_stores=selected_grocery_stores,
        )
        if category is None:
            ignored_rows += 1
            continue
        grouped[category].append(row)

    def total_amount(category_rows: list[dict[str, str]]) -> Decimal:
        total = Decimal("0.00")
        for row in category_rows:
            amt = row.get("Amount", "").replace("$", "").replace(",", "").strip()
            if amt:
                total += Decimal(amt)
        return total

    write_csv(output_dir / "grocery.csv", grouped["grocery"], fieldnames)
    write_csv(output_dir / "car.csv", grouped["car"], fieldnames)
    write_csv(output_dir / "travel.csv", grouped["travel"], fieldnames)
    write_csv(output_dir / "restaurant.csv", grouped["restaurant"], fieldnames)
    write_csv(output_dir / "miscellaneous.csv", grouped["miscellaneous"], fieldnames)

    total_output_rows = sum(len(v) for v in grouped.values())
    if total_output_rows + ignored_rows != len(rows):
        raise RuntimeError(
            "Row mismatch: "
            f"input={len(rows)} output_total={total_output_rows} ignored={ignored_rows}"
        )

    return {
        "input_rows": len(rows),
        "grocery_rows": len(grouped["grocery"]),
        "car_rows": len(grouped["car"]),
        "travel_rows": len(grouped["travel"]),
        "restaurant_rows": len(grouped["restaurant"]),
        "misc_rows": len(grouped["miscellaneous"]),
        "ignored_rows": ignored_rows,
        "grocery_total": float(total_amount(grouped["grocery"])),
        "car_total": float(total_amount(grouped["car"])),
        "travel_total": float(total_amount(grouped["travel"])),
        "restaurant_total": float(total_amount(grouped["restaurant"])),
        "misc_total": float(total_amount(grouped["miscellaneous"])),
    }


def process_single_pdf(
    pdf_path: Path,
    output_root: Path,
    config_path: Path = Path("stores_config.json"),
    bank: str = "amex",
    selected_grocery_stores: list[str] | None = None,
) -> dict[str, object]:
    rules = load_rules(config_path)
    per_pdf_dir = output_root / pdf_path.stem
    parsed_csv = per_pdf_dir / f"{pdf_path.stem}.csv"

    parsed_count = parse_pdf_to_csv(pdf_path, parsed_csv, bank=bank)
    stats = segregate_csv(
        parsed_csv,
        per_pdf_dir,
        rules,
        selected_grocery_stores=selected_grocery_stores,
    )
    return {
        "pdf_name": pdf_path.name,
        "output_folder": str(per_pdf_dir),
        "parsed_rows": parsed_count,
        "bank": bank,
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read all PDFs from dataset folder, parse New Charges Details, and write "
            "parsed + categorized CSVs under one folder per PDF."
        )
    )
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("dataset"),
        help="Dataset folder containing PDFs (default: dataset)",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("processed_dataset"),
        help="Output root folder for per-PDF subfolders (default: processed_dataset)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("stores_config.json"),
        help="JSON config for ignore/special/category rules (default: stores_config.json)",
    )
    parser.add_argument(
        "--bank",
        type=str,
        default="amex",
        choices=BANK_CHOICES,
        help="Bank parser to use for all PDFs in this run",
    )
    parser.add_argument(
        "--grocery-stores",
        type=str,
        default="",
        help=(
            "Comma-separated grocery store display names to include for grocery mapping. "
            "If omitted, all configured stores are used."
        ),
    )
    args = parser.parse_args()

    dataset_dir = args.dataset_dir
    output_root = args.output_root
    config_path = args.config
    bank = args.bank
    selected_grocery_stores = (
        [x.strip() for x in args.grocery_stores.split(",") if x.strip()]
        if args.grocery_stores
        else None
    )
    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise FileNotFoundError(f"Dataset folder not found: {dataset_dir}")

    pdf_paths = sorted(p for p in dataset_dir.iterdir() if p.suffix.lower() == ".pdf")
    if not pdf_paths:
        raise ValueError(f"No PDF files found in dataset folder: {dataset_dir}")

    for pdf_path in pdf_paths:
        result = process_single_pdf(
            pdf_path,
            output_root,
            config_path,
            bank=bank,
            selected_grocery_stores=selected_grocery_stores,
        )

        print(f"Processed: {pdf_path.name}")
        print(f"  Output folder: {result['output_folder']}")
        print(f"  Parsed rows: {result['parsed_rows']}")
        print(f"  Grocery rows: {result['grocery_rows']}")
        print(f"  Car rows: {result['car_rows']}")
        print(f"  Miscellaneous rows: {result['misc_rows']}")
        print(f"  Ignored rows: {result['ignored_rows']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
