"""Collect Zimba Town Council administration/contact records ."""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

BASE_URL = "https://www.zimbacouncil.gov.zm/"
USER_AGENT = "UNZA-CSC4792-Group45-research-project"
OUTPUT_COLUMNS = [
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
PHONE_RE = re.compile(r"(?:\+?260[\s-]?)?(?:0\d{2}[\s-]?\d{3}[\s-]?\d{3,4})")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PAGE_KEYWORDS = re.compile(
    r"who we are|about us|contact us|contact|administration|department|council structure|staff",
    re.IGNORECASE,
)


def get_html(session: requests.Session, url: str, delay: float, verify_ssl: bool) -> str:
    response = session.get(url, timeout=30, verify=verify_ssl)
    response.raise_for_status()
    time.sleep(delay)
    return response.text


def strip_html(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def page_title(raw_html: str, fallback: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw_html)
    title = strip_html(match.group(1)) if match else fallback
    return re.sub(r"\s*[|:-]\s*Zimba Town Council.*$", "", title, flags=re.IGNORECASE).strip()


def discover_admin_pages(raw_html: str) -> list[str]:
    links: list[str] = []
    for href, label in re.findall(
        r'''(?is)<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>''', raw_html
    ):
        visible_label = strip_html(label)
        if PAGE_KEYWORDS.search(visible_label) or PAGE_KEYWORDS.search(href):
            links.append(urljoin(BASE_URL, href))
    return list(dict.fromkeys(links))


def normalize_phone(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()


def extract_records(text: str, source_page: str, source_url: str) -> list[dict[str, str]]:
    emails = list(dict.fromkeys(EMAIL_RE.findall(text)))
    phones = list(dict.fromkeys(normalize_phone(item) for item in PHONE_RE.findall(text)))
    records: list[dict[str, str]] = []

    # A contact page often has one contact point rather than a staff table.
    if emails or phones:
        records.append(
            {
                "record_id": "",
                "name": "",
                "role_title": "",
                "department": "",
                "phone": "; ".join(phones),
                "email": "; ".join(emails),
                "office_address": extract_address(text),
                "source_page": source_page,
                "source_url": source_url,
            }
        )
    return records


def extract_address(text: str) -> str:
    match = re.search(
        r"(?i)(?:physical address|postal address|address)\s*[:\-]?\s*(.{10,180}?)(?=\s+(?:phone|tel|email|e-mail)\b|$)",
        text,
    )
    return match.group(1).strip(" .:-") if match else ""


def read_manual_records(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{column: row.get(column, "") for column in OUTPUT_COLUMNS} for row in csv.DictReader(handle)]


def write_csv(records: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    numbered_records = []
    for index, record in enumerate(records, start=1):
        record["record_id"] = record.get("record_id") or f"ZTC-ADM-{index:03d}"
        numbered_records.append({column: record.get(column, "") for column in OUTPUT_COLUMNS})
    pd.DataFrame(numbered_records, columns=OUTPUT_COLUMNS).to_csv(
        output_path, sep="|", index=False
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", action="append", help="Additional organizational page URL")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--output", type=Path, default=Path("data/db-unza26-csc4792-zimba_town_council_admin.csv"))
    parser.add_argument("--raw-dir", type=Path, default=Path("raw"))
    parser.add_argument("--manual-records", type=Path, help="Optional pipe-delimited file for manually verified staff rows")
    parser.add_argument("--no-verify-ssl", action="store_true", help="Use only when local certificate trust prevents HTTPS requests")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    verify_ssl = not args.no_verify_ssl
    seed_urls = [BASE_URL, "https://www.zimbacouncil.gov.zm/?page_id=118"]
    seed_urls.extend(args.url or [])
    pages: list[str] = []

    for url in dict.fromkeys(seed_urls):
        raw_html = get_html(session, url, args.delay, verify_ssl)
        pages.append(url)
        (args.raw_dir / "home.html" if url == BASE_URL else args.raw_dir / f"page_{len(pages):03d}.html").write_text(raw_html, encoding="utf-8")
        if url == BASE_URL:
            pages.extend(discover_admin_pages(raw_html))

    pages = list(dict.fromkeys(pages))
    records: list[dict[str, str]] = []
    for index, url in enumerate(pages, start=1):
        if index > 2 or url not in seed_urls:
            raw_html = get_html(session, url, args.delay, verify_ssl)
            (args.raw_dir / f"page_{index:03d}.html").write_text(raw_html, encoding="utf-8")
        else:
            raw_html = (args.raw_dir / ("home.html" if url == BASE_URL else "page_002.html")).read_text(encoding="utf-8")
        text = strip_html(raw_html)
        title = page_title(raw_html, url)
        records.extend(extract_records(text, title, url))

    records.extend(read_manual_records(args.manual_records) if args.manual_records else [])
    deduped = {(row["source_url"], row["email"], row["phone"]): row for row in records}
    write_csv(list(deduped.values()), args.output)
    print(f"Wrote {len(deduped)} administration records to {args.output}")
    print(f"Fetched {len(pages)} page(s); raw HTML saved in {args.raw_dir}")


if __name__ == "__main__":
    main()
