"""Collect Zimba Town Council district-profile records (population, area,
province, and neighboring-district facts) for the district-profile dataset."""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://www.zimbacouncil.gov.zm/"
USER_AGENT = "UNZA-CSC4792-Group45-research-project"
WHO_WE_ARE_URL = "https://www.zimbacouncil.gov.zm/?page_id=759"
CDF_URL = "https://www.zimbacouncil.gov.zm/?page_id=2737"
WIKIPEDIA_DISTRICT_URL = "https://en.wikipedia.org/wiki/Zimba_District"

OUTPUT_COLUMNS = [
    "record_id",
    "level",
    "name",
    "population",
    "population_year",
    "population_male",
    "population_female",
    "households",
    "area_km2",
    "province",
    "neighboring_districts",
    "notes",
    "source_url",
    "secondary_source_url",
]

# Known Zambian districts bordering Zimba, per the council's own "Who We Are"
# text. Matched against the boundaries sentence rather than guessed, so a
# change on the page (e.g. a renamed neighbour) would simply fail to match
# instead of silently keeping a stale name.
CANDIDATE_NEIGHBORS = ["Kalomo", "Kazungula", "Choma", "Sinazongwe"]


def get_html(session: requests.Session, url: str, delay: float, verify_ssl: bool) -> str:
    response = session.get(url, timeout=30, verify=verify_ssl)
    response.raise_for_status()
    time.sleep(delay)
    return response.text


def strip_html(raw_html: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", raw_html)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = re.sub(r"&#8211;|&ndash;", "-", text, flags=re.IGNORECASE)
    text = re.sub(r"&nbsp;", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def to_int(value: str | None) -> str:
    return value.replace(",", "") if value else ""


def extract_area_km2(text: str) -> str:
    match = re.search(r"total land area of ([\d,]+) square kilomet", text, re.IGNORECASE)
    return to_int(match.group(1)) if match else ""


def extract_province(text: str) -> str:
    match = re.search(r"Zambia\W?s (\w+) Province", text, re.IGNORECASE)
    return match.group(1) if match else ""


def extract_neighboring_districts(text: str) -> str:
    match = re.search(r"boundaries with[^.]*\.", text, re.IGNORECASE)
    window = match.group(0) if match else text
    found = [name for name in CANDIDATE_NEIGHBORS if name in window]
    return ";".join(found)


def extract_2010_census(text: str) -> dict[str, str]:
    match = re.search(
        r"2010 Census by the Central Statistical Office \(CSO\), Zimba District had "
        r"([\d,]+) households and a population of ([\d,]+), consisting of ([\d,]+) males "
        r"and ([\d,]+) females",
        text,
    )
    if not match:
        return {}
    households, population, males, females = match.groups()
    growth = re.search(r"growth rate of ([\d.]+)%", text)
    growth_note = f"; annual population growth rate reported as {growth.group(1)}%" if growth else ""
    return {
        "population": to_int(population),
        "population_year": "2010",
        "population_male": to_int(males),
        "population_female": to_int(females),
        "households": to_int(households),
        "notes": "2010 Census by the Central Statistical Office (CSO)" + growth_note,
    }


def extract_2018_projection(text: str) -> dict[str, str]:
    match = re.search(r"rise to approximately ([\d,]+) by (\d{4})", text)
    if not match:
        return {}
    population, year = match.groups()
    return {
        "population": to_int(population),
        "population_year": year,
        "notes": "Growth-rate projection from the 2010 Census, not an actual census count",
    }


def extract_2022_census(text: str) -> dict[str, str]:
    match = re.search(
        r"(\d{4}) Census of Population and Housing indicates significant growth, with "
        r"the district\W?s population increasing to ([\d,]+) residents",
        text,
    )
    if not match:
        return {}
    year, population = match.groups()
    return {
        "population": to_int(population),
        "population_year": year,
        "notes": "2022 Census of Population and Housing",
    }


def build_district_rows(who_we_are_text: str) -> list[dict[str, str]]:
    area_km2 = extract_area_km2(who_we_are_text)
    province = extract_province(who_we_are_text)
    neighbors = extract_neighboring_districts(who_we_are_text)
    shared = {
        "level": "district",
        "name": "Zimba",
        "area_km2": area_km2,
        "province": province,
        "neighboring_districts": neighbors,
        "source_url": WHO_WE_ARE_URL,
    }

    rows = []
    for extractor in (extract_2010_census, extract_2018_projection, extract_2022_census):
        facts = extractor(who_we_are_text)
        if not facts:
            continue
        row = {column: "" for column in OUTPUT_COLUMNS}
        row.update(shared)
        row.update(facts)
        rows.append(row)

    if rows:
        rows[-1]["notes"] += (
            "; district was separated from Kalomo District in 2012 (Wikipedia, cross-checked "
            "because the council site does not state a founding date)"
        )
        rows[-1]["secondary_source_url"] = WIKIPEDIA_DISTRICT_URL

    return rows


def build_constituency_rows(cdf_text: str) -> list[dict[str, str]]:
    rows = []
    if "Mapatizya" in cdf_text:
        row = {column: "" for column in OUTPUT_COLUMNS}
        row.update(
            {
                "level": "constituency",
                "name": "Mapatizya",
                "province": "Southern",
                "notes": (
                    "Named as a constituency in Zimba Town Council's own CDF financial "
                    "statement listings (2023 and 2024); no population or area figures "
                    "are published at this level, so those fields are left blank rather "
                    "than estimated"
                ),
                "source_url": CDF_URL,
            }
        )
        rows.append(row)
    return rows


def assign_record_ids(rows: list[dict[str, str]]) -> None:
    for index, row in enumerate(rows, start=1):
        row["record_id"] = f"ZTC-DIST-{index:03d}"


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(output_path, sep="|", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/db-unza26-csc4792-zimba_town_council_district_profile.csv"),
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("raw"))
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Use only when local certificate trust prevents HTTPS requests "
        "(this site's chain is missing an intermediate certificate)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    verify_ssl = not args.no_verify_ssl

    who_we_are_html = get_html(session, WHO_WE_ARE_URL, args.delay, verify_ssl)
    (args.raw_dir / "district_profile_page_759_who_we_are.html").write_text(who_we_are_html, encoding="utf-8")

    cdf_html = get_html(session, CDF_URL, args.delay, verify_ssl)
    (args.raw_dir / "district_profile_page_2737_cdf.html").write_text(cdf_html, encoding="utf-8")

    who_we_are_text = strip_html(who_we_are_html)
    cdf_text = strip_html(cdf_html)

    rows = build_district_rows(who_we_are_text) + build_constituency_rows(cdf_text)
    assign_record_ids(rows)
    write_csv(rows, args.output)

    print(f"Wrote {len(rows)} district-profile record(s) to {args.output}")
    print(f"Raw HTML evidence saved in {args.raw_dir}")


if __name__ == "__main__":
    main()
