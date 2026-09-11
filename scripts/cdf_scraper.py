"""Scrape CDF project announcements from the Zimba Town Council website.

CSC 4792 - Group 45

The script uses only requests, regular expressions, pandas, and Python's
standard library. It saves raw source pages for traceability and writes the
required pipe-delimited CSV file.
"""

from __future__ import annotations

import argparse
import csv
import html as html_lib
import json
import re
import sys
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

try:
    import pandas as pd
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ModuleNotFoundError:
    # This lets --self-test run before the user installs the two dependencies.
    # Normal scraping is blocked with a clear installation message in main().
    pd = None
    requests = None
    HTTPAdapter = None
    Retry = None


BASE_URL = "https://www.zimbacouncil.gov.zm"
USER_AGENT = "UNZA-CSC4792-Group45-CDF-research-project/1.0"
OUTPUT_FILENAME = "db-unza26-csc4792-zimba_town_council_cdf_projects.csv"

OUTPUT_COLUMNS = [
    "project_id",
    "project_name",
    "sector",
    "constituency",
    "funding_source",
    "funding_amount_zmw",
    "status",
    "date_reported",
    "description",
    "source_url",
]

# Check specific wards first. "Zimba" alone is not used because it would also
# match the council name; it counts as a place only when the text says "Ward".
PLACE_PATTERNS = [
    ("Chalimongela", r"\bChalimongela(?:\s+Ward)?\b"),
    ("Chuundwe", r"\bChuundwe(?:\s+Ward)?\b"),
    ("Siamafumba", r"\bSiamafumba(?:\s+Ward)?\b"),
    ("Simwatachela", r"\bSimwatachela(?:\s+Ward)?\b"),
    ("Mangonda", r"\bMangonda(?:\s+Ward)?\b"),
    ("Mulamfu", r"\bMulamfu(?:\s+Ward)?\b"),
    ("Kanyanga", r"\bKanyanga(?:\s+Ward)?\b"),
    ("Mafumba", r"\bMafumba(?:\s+Ward)?\b"),
    ("Misika", r"\bMisika(?:\s+Ward)?\b"),
    ("Luyaba", r"\bLuyaba(?:\s+Ward)?\b"),
    ("Chidi", r"\bChidi(?:\s+Ward)?\b"),
    ("Zimba", r"\bZimba\s+Ward\b"),
    ("Mapatizya", r"\bMapatizya(?:\s+Constituency)?\b"),
]

PROJECT_ACTIONS = (
    "construction",
    "construct",
    "rehabilitation",
    "rehabilitate",
    "procurement",
    "purchase",
    "installation",
    "install",
    "drilling",
    "development",
    "grading",
    "completion",
    "commissioned",
    "project",
    "projects",
)

SECTOR_KEYWORDS = {
    "water_sanitation": (
        "water",
        "borehole",
        "sanitation",
        "latrine",
        "toilet",
        "reticulation",
        "waste management",
    ),
    "education": (
        "school",
        "classroom",
        "education",
        "pupil",
        "student",
        "desk",
        "bursary",
        "skills development",
    ),
    "health": (
        "health",
        "clinic",
        "hospital",
        "maternity",
        "medical",
        "rural health post",
        "rural health centre",
        "rural health center",
    ),
    "agriculture": (
        "agriculture",
        "farmer",
        "farming",
        "livestock",
        "fisheries",
        "irrigation",
    ),
    "infrastructure": (
        "road",
        "bridge",
        "market",
        "electricity",
        "electrification",
        "staff house",
        "civic centre",
        "civic center",
    ),
}


def clean_space(value: str) -> str:
    """Collapse whitespace and remove pipe characters that could break the CSV."""
    return re.sub(r"\s+", " ", value.replace("|", "/")).strip()


def strip_html(raw_html: str) -> str:
    """Remove scripts, styles, tags, and decode HTML entities using regex."""
    text = re.sub(
        r"<(script|style|noscript|svg)\b[^>]*>.*?</\1>",
        " ",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return clean_space(html_lib.unescape(text))


def build_session(verify_ssl: bool = True) -> requests.Session:
    """Create a polite requests session with retry handling."""
    session = requests.Session()
    session.verify = verify_ssl
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }
    )
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1.0,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session


def same_site(url: str, base_url: str) -> bool:
    """Allow crawling only within the assigned council website."""
    target = urlparse(url)
    base = urlparse(base_url)
    target_host = target.netloc.lower().removeprefix("www.")
    base_host = base.netloc.lower().removeprefix("www.")
    return target.scheme in {"http", "https"} and target_host == base_host


def load_robots(
    session: requests.Session, base_url: str, raw_dir: Path
) -> RobotFileParser | None:
    """Download robots.txt; only a confirmed 404 permits proceeding without it."""
    robots_url = urljoin(base_url, "/robots.txt")
    try:
        response = session.get(robots_url, timeout=(10, 30))
        if response.status_code == 404:
            print("robots.txt was not found; continuing with a one-second delay.")
            return None
        response.raise_for_status()
        raw_dir.joinpath("robots.txt").write_text(response.text, encoding="utf-8")
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(response.text.splitlines())
        return parser
    except requests.RequestException as exc:
        raise RuntimeError(f"Cannot check robots.txt; scraping stopped: {exc}") from exc


def ensure_allowed(robots: RobotFileParser | None, url: str) -> None:
    """Stop before requesting a URL forbidden by robots.txt."""
    if robots is not None and not robots.can_fetch(USER_AGENT, url):
        raise PermissionError(f"robots.txt does not allow this script to fetch: {url}")


def fetch(
    session: requests.Session,
    url: str,
    base_url: str,
    robots: RobotFileParser | None,
    delay: float,
) -> requests.Response:
    """Fetch one same-site URL, then pause to avoid overloading the server."""
    if not same_site(url, base_url):
        raise ValueError(f"Refusing to fetch a URL outside the council site: {url}")
    ensure_allowed(robots, url)
    try:
        response = session.get(url, timeout=(10, 40))
        response.raise_for_status()
    except requests.exceptions.SSLError as exc:
        raise RuntimeError(
            "The council website's HTTPS certificate could not be verified. "
            "Update certifi/requests or explicitly pass --no-verify-ssl "
            "to collect without certificate verification."
        ) from exc
    finally:
        time.sleep(max(delay, 1.0))
    return response


def safe_filename(url: str, prefix: str = "post") -> str:
    """Create a stable filename from a WordPress URL."""
    parsed = urlparse(url)
    post_id = parse_qs(parsed.query).get("p", [""])[0]
    if post_id:
        token = post_id
    else:
        token = parsed.path.strip("/").split("/")[-1] or "home"
    token = re.sub(r"[^A-Za-z0-9_-]+", "_", token)[:100]
    return f"{prefix}_{token}.html"


def extract_title(raw_html: str) -> str:
    """Extract a WordPress post title using several common patterns."""
    patterns = [
        r'<h1[^>]*class=["\'][^"\']*entry-title[^"\']*["\'][^>]*>(.*?)</h1>',
        r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
        r"<title[^>]*>(.*?)</title>",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            title = strip_html(match.group(1))
            title = re.sub(
                r"\s*[-–—|]\s*Zimba Town Council\s*$", "", title, flags=re.IGNORECASE
            )
            return clean_space(title)
    return ""


def extract_date(raw_html: str) -> str:
    """Extract the publication date and return YYYY-MM-DD."""
    patterns = [
        r'<time[^>]+datetime=["\'](\d{4}-\d{2}-\d{2})',
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\'](\d{4}-\d{2}-\d{2})',
        r'published(?:\s+on)?\s+(\w+\s+\d{1,2},?\s+\d{4})',
    ]
    for pattern in patterns[:2]:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE)
        if match:
            return match.group(1)

    # WordPress sometimes prints dates only as readable text.
    match = re.search(patterns[2], strip_html(raw_html), flags=re.IGNORECASE)
    if match:
        parsed = pd.to_datetime(match.group(1), errors="coerce")
        if not pd.isna(parsed):
            return parsed.strftime("%Y-%m-%d")
    return ""


def extract_article_html(raw_html: str) -> str:
    """Keep the main article so menus and footers do not pollute the data."""
    patterns = [
        r"<article\b[^>]*>(.*?)</article>",
        r'<main\b[^>]*>(.*?)</main>',
        r'<div[^>]*class=["\'][^"\']*entry-content[^"\']*["\'][^>]*>(.*?)</div>\s*</div>',
        r"<body\b[^>]*>(.*?)</body>",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw_html, flags=re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return raw_html


def extract_paragraphs(article_html: str) -> list[str]:
    """Extract readable paragraphs from an article."""
    pieces = re.findall(
        r"<p\b[^>]*>(.*?)</p>", article_html, flags=re.IGNORECASE | re.DOTALL
    )
    paragraphs = [strip_html(piece) for piece in pieces]
    paragraphs = [piece for piece in paragraphs if len(piece) >= 25]
    if paragraphs:
        return paragraphs
    fallback = strip_html(article_html)
    return [fallback] if fallback else []


def is_cdf_post(title: str, body_text: str) -> bool:
    """Keep posts that explicitly discuss CDF and a project activity."""
    combined = f"{title} {body_text}".lower()
    mentions_cdf = bool(
        re.search(r"\bcdf\b|constituency development fund", combined, re.IGNORECASE)
    )
    mentions_project = any(keyword in combined for keyword in PROJECT_ACTIONS)
    return mentions_cdf and mentions_project


def project_units(paragraphs: list[str], title: str) -> list[str]:
    """Select project-like paragraphs; bundled announcements can create several rows."""
    chosen: list[str] = []
    for paragraph in paragraphs:
        lower = paragraph.lower()
        has_action = any(keyword in lower for keyword in PROJECT_ACTIONS)
        has_subject = any(
            keyword in lower
            for words in SECTOR_KEYWORDS.values()
            for keyword in words
        )
        boilerplate = any(
            phrase in lower
            for phrase in (
                "issued by the council secretary",
                "published by",
                "all rights reserved",
                "contact information",
            )
        )
        if has_action and has_subject and not boilerplate:
            chosen.append(paragraph)

    if chosen:
        return list(dict.fromkeys(chosen))

    whole_text = clean_space(" ".join(paragraphs))
    return [whole_text or title]


def infer_sector(text: str) -> str:
    """Map project keywords to the five sector values required by the brief."""
    lower = text.lower()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return sector
    return "other"


def infer_place(text: str) -> str:
    """Return the first explicitly named ward or constituency."""
    for place, pattern in PLACE_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return place
    return ""


def infer_funding_source(text: str) -> str:
    """Identify the stated funding programme without guessing."""
    if re.search(r"\bcdf\b|constituency development fund", text, re.IGNORECASE):
        return "CDF"
    if re.search(r"\blgef\b|local government equalisation fund", text, re.IGNORECASE):
        return "LGEF"
    if re.search(r"world bank", text, re.IGNORECASE):
        return "World Bank"
    return ""


def infer_status(text: str) -> str:
    """Map wording in a post to the permitted project status categories."""
    lower = text.lower()
    if re.search(r"\b(not|yet to be|will be|to be)\s+(completed|commissioned|handed over|officially opened)\b", lower):
        return ""
    if re.search(r"\b(completed|commissioned|handed over|officially opened)\b", lower):
        return "completed"
    if re.search(r"near(?:ing)? completion|almost complete|9\d\s*%\s*complete", lower):
        return "near_completion"
    if re.search(r"\b(ongoing|underway|in progress|being constructed)\b", lower):
        return "ongoing"
    if re.search(
        r"\b(planned|proposed|approved|ground[- ]breaking|will be constructed|to be constructed)\b",
        lower,
    ):
        return "planned"
    return ""


def extract_amount(text: str) -> int | float | str:
    """Extract a single stated kwacha amount; leave multiple amounts for review."""
    matches = list(re.finditer(
        r"\b(?:ZMW|K)\s*,?\s*([0-9][0-9,]*(?:\.\d+)?)\s*"
        r"(thousand|million|billion|m|bn)?\b",
        text,
        flags=re.IGNORECASE,
    ))
    if len(matches) != 1:
        return ""
    match = matches[0]

    number = float(match.group(1).replace(",", ""))
    suffix = (match.group(2) or "").lower()
    multipliers = {
        "thousand": 1_000,
        "million": 1_000_000,
        "m": 1_000_000,
        "billion": 1_000_000_000,
        "bn": 1_000_000_000,
    }
    number *= multipliers.get(suffix, 1)
    return int(number) if number.is_integer() else number


def make_project_name(unit: str, post_title: str, multiple_units: bool) -> str:
    """Create a short reviewable project name from an action phrase."""
    if not multiple_units and post_title:
        return post_title[:180]

    match = re.search(
        r"\b(construction|rehabilitation|procurement|purchase|installation|"
        r"drilling|grading|completion|development|provision)\b[^.!?]{0,180}",
        unit,
        flags=re.IGNORECASE,
    )
    name = match.group(0) if match else unit
    name = re.split(r"[.;]", name, maxsplit=1)[0]
    name = clean_space(name)
    if len(name) > 180:
        name = name[:177].rsplit(" ", 1)[0] + "..."
    return name


def make_description(text: str) -> str:
    """Keep the first two sentences as a concise description."""
    sentences = re.split(r"(?<=[.!?])\s+", clean_space(text))
    result = " ".join(sentences[:2])
    return result[:600].rstrip()


def find_post_links(listing_html: str, listing_url: str, base_url: str) -> list[str]:
    """Find likely WordPress post links on one HTML listing page."""
    article_blocks = re.findall(
        r"<article\b[^>]*>.*?</article>",
        listing_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    search_area = "\n".join(article_blocks) if article_blocks else listing_html
    hrefs = re.findall(
        r'<a\b[^>]+href=["\']([^"\'#]+)["\']', search_area, flags=re.IGNORECASE
    )

    results: list[str] = []
    for href in hrefs:
        url = urljoin(listing_url, html_lib.unescape(href))
        parsed = urlparse(url)
        lower_path = parsed.path.lower()
        if not same_site(url, base_url):
            continue
        if any(
            excluded in lower_path
            for excluded in ("/category/", "/tag/", "/author/", "/feed/", "/wp-content/")
        ):
            continue
        looks_like_post = (
            bool(parse_qs(parsed.query).get("p"))
            or bool(re.search(r"/20\d{2}/", lower_path))
            or any(word in url.lower() for word in ("cdf", "project", "mapatizya"))
        )
        if looks_like_post:
            results.append(url)
    return list(dict.fromkeys(results))


def discover_from_rest_api(
    session: requests.Session,
    base_url: str,
    robots: RobotFileParser | None,
    raw_dir: Path,
    delay: float,
    max_pages: int,
) -> list[str]:
    """Use WordPress's public JSON index to locate CDF posts efficiently."""
    results: list[str] = []
    api_url = urljoin(base_url, "/wp-json/wp/v2/posts")
    for page in range(1, max_pages + 1):
        url = f"{api_url}?per_page=100&page={page}&_fields=id,date,link,title,content"
        try:
            response = fetch(session, url, base_url, robots, delay)
            items = response.json()
        except (requests.RequestException, ValueError, PermissionError, RuntimeError) as exc:
            print(f"WordPress API discovery stopped: {exc}")
            break

        raw_dir.joinpath(f"wordpress_api_page_{page}.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not isinstance(items, list) or not items:
            break

        for item in items:
            title = strip_html(str(item.get("title", {}).get("rendered", "")))
            body = strip_html(str(item.get("content", {}).get("rendered", "")))
            link = str(item.get("link", ""))
            if link and same_site(link, base_url) and is_cdf_post(title, body):
                results.append(link)

        if len(items) < 100:
            break
    return list(dict.fromkeys(results))


def discover_from_sitemap(
    session: requests.Session,
    base_url: str,
    robots: RobotFileParser | None,
    raw_dir: Path,
    delay: float,
) -> list[str]:
    """Fall back to the standard WordPress post sitemap."""
    sitemap_url = urljoin(base_url, "/wp-sitemap-posts-post-1.xml")
    try:
        response = fetch(session, sitemap_url, base_url, robots, delay)
    except (requests.RequestException, PermissionError, RuntimeError) as exc:
        print(f"Sitemap discovery stopped: {exc}")
        return []

    raw_dir.joinpath("wp-sitemap-posts-post-1.xml").write_text(
        response.text, encoding="utf-8"
    )
    urls = re.findall(r"<loc>(.*?)</loc>", response.text, flags=re.IGNORECASE)
    urls = [html_lib.unescape(url.strip()) for url in urls]
    # Slug filtering prevents hundreds of unrelated posts from being downloaded.
    return [
        url
        for url in urls
        if same_site(url, base_url)
        and any(word in url.lower() for word in ("cdf", "project", "mapatizya"))
    ]


def listing_page_url(listing_url: str, page: int, pagination: str) -> str:
    """Construct either /page/2/ or ?paged=2 pagination."""
    if "{page}" in listing_url:
        return listing_url.format(page=page)
    if page == 1:
        return listing_url
    if pagination == "query":
        separator = "&" if "?" in listing_url else "?"
        return f"{listing_url}{separator}paged={page}"
    return urljoin(listing_url.rstrip("/") + "/", f"page/{page}/")


def discover_from_listings(
    session: requests.Session,
    base_url: str,
    listing_urls: Iterable[str],
    pagination: str,
    robots: RobotFileParser | None,
    raw_dir: Path,
    delay: float,
    max_pages: int,
) -> list[str]:
    """Fall back to normal blog listing pages when API/sitemap discovery fails."""
    results: list[str] = []
    for listing_number, listing_url in enumerate(listing_urls, start=1):
        empty_pages = 0
        for page in range(1, max_pages + 1):
            url = listing_page_url(listing_url, page, pagination)
            try:
                response = fetch(session, url, base_url, robots, delay)
            except (requests.RequestException, PermissionError, RuntimeError) as exc:
                print(f"Listing discovery stopped at {url}: {exc}")
                break

            raw_dir.joinpath(f"listing_{listing_number}_page_{page}.html").write_text(
                response.text, encoding="utf-8"
            )
            links = find_post_links(response.text, url, base_url)
            new_links = [link for link in links if link not in results]
            if not new_links:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0
                results.extend(new_links)
    return results


def scrape_post(raw_html: str, source_url: str) -> list[dict[str, object]]:
    """Convert one CDF post into one or more candidate project records."""
    title = extract_title(raw_html)
    date_reported = extract_date(raw_html)
    article_html = extract_article_html(raw_html)
    paragraphs = extract_paragraphs(article_html)
    body_text = clean_space(" ".join(paragraphs))

    if not is_cdf_post(title, body_text):
        return []

    units = project_units(paragraphs, title)
    multiple_units = len(units) > 1
    rows: list[dict[str, object]] = []
    for unit in units:
        evidence = clean_space(f"{title}. {unit}")
        rows.append(
            {
                "project_id": "",  # Assigned after sorting and deduplication.
                "project_name": make_project_name(unit, title, multiple_units),
                "sector": infer_sector(unit),
                "constituency": infer_place(unit) or infer_place(evidence),
                "funding_source": infer_funding_source(evidence),
                "funding_amount_zmw": extract_amount(unit),
                "status": infer_status(unit),
                "date_reported": date_reported,
                "description": make_description(unit),
                "source_url": source_url,
            }
        )
    return rows


def finalize_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Deduplicate, sort, assign IDs, and enforce the required schema."""
    if not rows:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    frame = pd.DataFrame(rows)
    for column in OUTPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""

    text_columns = [column for column in OUTPUT_COLUMNS if column != "funding_amount_zmw"]
    for column in text_columns:
        frame[column] = frame[column].fillna("").astype(str).map(clean_space)

    frame = frame.drop_duplicates(
        subset=["source_url", "project_name", "description"], keep="first"
    )
    frame = frame.sort_values(
        by=["date_reported", "source_url", "project_name"],
        na_position="last",
    ).reset_index(drop=True)
    frame["project_id"] = [f"ZTC-{number:03d}" for number in range(1, len(frame) + 1)]
    return frame[OUTPUT_COLUMNS]


def run_self_test() -> None:
    """Test the parser without contacting the website."""
    sample = """
    <html><head><title>CDF PROJECTS IMPROVE WATER ACCESS - Zimba Town Council</title>
    <meta property="article:published_time" content="2026-02-26T09:00:00+00:00"></head>
    <body><article><h1 class="entry-title">CDF PROJECTS IMPROVE WATER ACCESS</h1>
    <p>In Siamafumba Ward, construction of a water system at Mooka Primary School
    is ongoing under the Constituency Development Fund at K1.2 million.</p>
    <p>Construction of a rural health post in Chuundwe Ward has been completed.</p>
    </article></body></html>
    """
    rows = scrape_post(sample, "https://www.zimbacouncil.gov.zm/?p=9999")
    assert len(rows) == 2
    assert rows[0]["sector"] == "water_sanitation"
    assert rows[0]["funding_amount_zmw"] == 1_200_000
    assert rows[0]["status"] == "ongoing"
    assert rows[1]["sector"] == "health"
    assert rows[1]["status"] == "completed"
    assert extract_date(sample) == "2026-02-26"
    print("Self-test passed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Zimba Town Council CDF project announcements."
    )
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument(
        "--listing-url",
        action="append",
        default=[],
        help="A news/category listing URL. Repeat this option for multiple listings.",
    )
    parser.add_argument(
        "--seed-url",
        action="append",
        default=[],
        help="An exact CDF post URL to include. Repeat for multiple posts.",
    )
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument(
        "--pagination", choices=("path", "query"), default="path"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root; source evidence goes to raw/cdf_projects/ and CSVs to data/.",
    )
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--no-verify-ssl", action="store_true",
        help="Disable HTTPS certificate verification for the council site.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        run_self_test()
        return 0

    if requests is None or pd is None:
        print("Missing packages. Install them before scraping:")
        print(r"C:\Python313\python.exe -m pip install requests pandas lxml")
        return 1

    base_url = args.base_url.rstrip("/")
    project_dir = args.project_dir.resolve()
    raw_dir = project_dir / "raw" / "cdf_projects"
    data_dir = project_dir / "data"
    raw_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    session = build_session(verify_ssl=not args.no_verify_ssl)
    if args.no_verify_ssl:
        print("HTTPS certificate verification disabled for this collection run.")
    try:
        robots = load_robots(session, base_url, raw_dir)
    except RuntimeError as exc:
        print(str(exc))
        return 1

    post_urls: list[str] = []
    post_urls.extend(args.seed_url)

    print("Discovering CDF posts through the WordPress API...")
    post_urls.extend(
        discover_from_rest_api(
            session,
            base_url,
            robots,
            raw_dir,
            args.delay,
            args.max_pages,
        )
    )

    if not post_urls:
        print("Trying the WordPress post sitemap...")
        post_urls.extend(
            discover_from_sitemap(
                session, base_url, robots, raw_dir, args.delay
            )
        )

    if not post_urls:
        listings = args.listing_url or [base_url + "/"]
        print("Trying HTML news listings...")
        post_urls.extend(
            discover_from_listings(
                session,
                base_url,
                listings,
                args.pagination,
                robots,
                raw_dir,
                args.delay,
                args.max_pages,
            )
        )

    post_urls = [
        url for url in dict.fromkeys(post_urls) if same_site(url, base_url)
    ]
    if not post_urls:
        print(
            "No post URLs were discovered. Inspect the News/CDF page in Chrome, "
            "then rerun with --listing-url or one or more --seed-url options."
        )
        return 1

    print(f"Checking {len(post_urls)} candidate post(s)...")
    rows: list[dict[str, object]] = []
    posts: list[dict[str, str]] = []
    failed_urls: list[dict[str, str]] = []
    for number, url in enumerate(post_urls, start=1):
        print(f"[{number}/{len(post_urls)}] {url}")
        try:
            response = fetch(session, url, base_url, robots, args.delay)
            raw_dir.joinpath(safe_filename(url)).write_text(
                response.text, encoding="utf-8"
            )
            posts.append({
                "title": extract_title(response.text),
                "date": extract_date(response.text),
                "body_text": clean_space(" ".join(extract_paragraphs(extract_article_html(response.text)))),
                "url": url,
            })
            rows.extend(scrape_post(response.text, url))
        except (requests.RequestException, PermissionError, RuntimeError, ValueError) as exc:
            failed_urls.append({"source_url": url, "error": str(exc)})
            print(f"  Skipped: {exc}")

    pd.DataFrame(posts, columns=["title", "date", "body_text", "url"]).to_csv(
        data_dir / "cdf_source_posts.csv", sep="|", index=False, encoding="utf-8-sig"
    )
    frame = finalize_rows(rows)
    output_path = data_dir / OUTPUT_FILENAME
    frame.to_csv(
        output_path,
        sep="|",
        index=False,
        encoding="utf-8-sig",
        quoting=csv.QUOTE_MINIMAL,
    )

    if failed_urls:
        pd.DataFrame(failed_urls).to_csv(
            data_dir / "cdf_scrape_failures.csv", index=False, encoding="utf-8-sig"
        )

    print(f"Saved {len(frame)} candidate project row(s) to:")
    print(output_path)
    print(
        "Open the file and manually verify every project name, amount, status, "
        "and multi-project announcement against its source_url before handoff."
    )
    return 0 if len(frame) and not failed_urls else 1


if __name__ == "__main__":
    sys.exit(main())
