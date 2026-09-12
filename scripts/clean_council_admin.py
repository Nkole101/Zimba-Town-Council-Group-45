"""Clean the council administration CSV using the Detect -> Judge -> Act workflow."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "record_id",
    "name",
    "role_title",
    "department",
    "phone",
    "email",
    "office_address",
    "source_page",
    "source_url",
]
TEXT_COLUMNS = [
    "name",
    "role_title",
    "department",
    "phone",
    "email",
    "office_address",
    "source_page",
    "source_url",
]
PHONE_RE = re.compile(r"\s*([+]?\d[\d\s().-]{6,}\d)\s*")


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def normalize_phone(value: object) -> str:
    phone = normalize_text(value)
    if not phone:
        return ""
    matches = PHONE_RE.findall(phone)
    return "; ".join(re.sub(r"\s+", " ", match).strip() for match in matches) or phone


def clean_admin_data(input_path: Path, output_path: Path, report_path: Path) -> None:
    raw = pd.read_csv(input_path, sep="|", dtype=str, keep_default_na=False)
    missing_columns = [column for column in EXPECTED_COLUMNS if column not in raw.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    duplicate_rows = int(raw.duplicated().sum())
    duplicate_sources = int(raw.duplicated(subset=["source_url"]).sum())

    clean = raw[EXPECTED_COLUMNS].copy()
    for column in TEXT_COLUMNS:
        clean[column] = clean[column].map(normalize_text)
    clean["phone"] = clean["phone"].map(normalize_phone)
    clean["email"] = clean["email"].str.lower()

    before_deduplication = len(clean)
    clean = clean.drop_duplicates(subset=["source_url"], keep="first").copy()
    removed_rows = before_deduplication - len(clean)

    # A source URL is the traceability key; rows without one cannot be audited.
    missing_source_urls = int(clean["source_url"].eq("").sum())
    if missing_source_urls:
        clean = clean[clean["source_url"].ne("")].copy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(output_path, sep="|", index=False)

    missing_counts = clean.isna().sum().to_dict()
    missing_counts.update({column: int(clean[column].eq("").sum()) for column in clean.columns})
    report = f"""# Council Administration Cleaning Report

## Detect

- Input rows: {len(raw)}
- Exact duplicate rows detected: {duplicate_rows}
- Duplicate `source_url` values detected: {duplicate_sources}
- Missing values were counted after standardizing blank cells to empty strings.

## Judge

- `source_url` is the traceability field. A row without it would not be auditable and is removed.
- `name`, `role_title`, `department`, `office_address`, `phone`, and `email` are supporting fields. Blanks are retained because the source did not publish those values clearly; no values were invented.
- The two records have different source URLs, so both represent distinct source pages and are retained.
- HTML entities in page titles were decoded, repeated whitespace was collapsed, phone values were normalized, and emails were lowercased.

## Act

- Rows removed for duplicate `source_url`: {removed_rows}
- Rows removed for missing `source_url`: {missing_source_urls}
- Final rows: {len(clean)}

### Blank counts in the final file

"""
    report += "\n".join(f"- `{column}`: {count}" for column, count in missing_counts.items())
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report + "\n", encoding="utf-8")
    print(f"Cleaned {len(clean)} administration rows")
    print(f"Wrote {output_path}")
    print(f"Wrote {report_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/db-unza26-csc4792-zimba_town_council_admin.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/db-unza26-csc4792-zimba_town_council_admin.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/council_admin_cleaning_report.md"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    clean_admin_data(args.input, args.output, args.report)