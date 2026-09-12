"""Part 1: reproducible Detect -> Judge -> Act cleaning of CDF files only."""
from io import StringIO
import json
from pathlib import Path
import re
import shutil

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROJECT_FILE = "db-unza26-csc4792-zimba_town_council_cdf_projects.csv"
SOURCE_FILE = "cdf_source_posts.csv"
# Small explicit stopword list: no NLTK downloads required. Negations are kept.
STOPWORDS = set("a an the and or of to in on at for from by with as is are was were be been being it its this that these those".split())


def clean_text(value):
    if pd.isna(value):
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value)).casefold()
    return " ".join(t for t in re.findall(r"\b\w+\b", text) if t not in STOPWORDS)


def profile(frame):
    info = StringIO()
    frame.info(buf=info)
    return {"shape": list(frame.shape), "head": frame.head().to_string(index=False),
            "info": info.getvalue(), "describe": frame.describe(include="all").to_string(),
            "missing": {k: int(v) for k, v in frame.isna().sum().items()}}


def clean(frame, projects):
    frame = frame.copy()
    derived = "description_clean" if projects else "body_text_clean"
    frame = frame.drop(columns=[derived], errors="ignore")
    before = len(frame)
    url = "source_url" if projects else "url"
    # Ignore sequential IDs when detecting identical project records. Different
    # project names/details on the same URL are distinct records, not duplicates.
    keys = [c for c in frame.columns if c != "project_id"]
    exact = int(frame.duplicated(subset=keys).sum())
    repeated_urls = int(frame.duplicated(subset=[url]).sum())
    frame = frame.drop_duplicates(subset=keys, keep="first").copy()
    near_keys = [url, "project_name"] if projects else [url]
    near = frame[frame.duplicated(subset=near_keys, keep=False)]
    # Same URL with different content is flagged for review, never silently lost.
    details = {"input_rows": before, "duplicates_removed": exact,
               "repeated_url_rows_before": repeated_urls,
               "near_duplicate_review": near.fillna("").to_dict(orient="records")}
    date_col = "date_reported" if projects else "date"
    parsed = pd.to_datetime(frame[date_col], errors="coerce")
    invalid_dates = frame[date_col].notna() & parsed.isna()
    if invalid_dates.any():
        raise ValueError(f"Invalid dates require source review: {frame.loc[invalid_dates, date_col].tolist()}")
    frame[date_col] = parsed
    if projects:
        amounts = pd.to_numeric(frame["funding_amount_zmw"], errors="coerce")
        invalid_amounts = frame["funding_amount_zmw"].notna() & amounts.isna()
        if invalid_amounts.any() or (amounts.dropna() <= 0).any():
            raise ValueError("Invalid funding amount requires source review")
        frame["funding_amount_zmw"] = amounts
        for col in ["status", "sector"]:
            frame[col] = frame[col].astype("string").str.strip().str.lower()
        frame["status"] = frame["status"].replace("", pd.NA).fillna("unspecified")
        allowed = {"planned", "ongoing", "near_completion", "completed", "unspecified"}
        if not frame["status"].isin(allowed).all():
            raise ValueError("Unexpected status requires review")
        if not frame["sector"].isin({"education", "health", "water_sanitation", "agriculture", "infrastructure", "other"}).all():
            raise ValueError("Unexpected sector requires review")
        q1, q3 = amounts.quantile([0.25, 0.75])
        lower, upper = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
        flags = frame.loc[(amounts < lower) | (amounts > upper),
                          ["project_id", "project_name", "funding_amount_zmw", "source_url"]]
        details["iqr"] = {"q1": None if pd.isna(q1) else float(q1),
                          "q3": None if pd.isna(q3) else float(q3),
                          "lower": None if pd.isna(lower) else float(lower),
                          "upper": None if pd.isna(upper) else float(upper),
                          "flagged_rows": flags.to_dict(orient="records")}
        frame[derived] = frame["description"].map(clean_text)
    else:
        # IDs/years embedded in news text are not numerical measurement columns.
        details["iqr"] = "Not applicable: source posts contain text, dates and URLs."
        frame[derived] = frame["body_text"].map(clean_text)
    if frame[url].isna().any():
        raise ValueError("Missing source URL requires review")
    details["output_rows"] = len(frame)
    return frame, details


def main():
    backup = ROOT / "raw/cdf_projects/before_cleaning"
    reports = ROOT / "docs/cdf_cleaning"
    backup.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)
    results = {}
    outputs = []
    for filename, projects in [(PROJECT_FILE, True), (SOURCE_FILE, False)]:
        source = ROOT / "data" / filename
        saved = backup / filename
        if not saved.exists():
            shutil.copyfile(source, saved)
        # Always replay the preserved input snapshot for an idempotent run.
        raw = pd.read_csv(saved, sep="|")
        before = profile(raw)
        cleaned, decisions = clean(raw, projects)
        if isinstance(decisions["iqr"], dict) and decisions["iqr"]["flagged_rows"]:
            raise ValueError("IQR flags need source review before export: " + str(decisions["iqr"]["flagged_rows"]))
        results[filename] = {"before": before, "decisions": decisions, "after": profile(cleaned)}
        outputs.append((source, cleaned))
    for source, cleaned in outputs:
        cleaned.to_csv(source, sep="|", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d", na_rep="")
        roundtrip = pd.read_csv(source, sep="|")
        assert roundtrip.shape == cleaned.shape
        assert list(roundtrip.columns) == list(cleaned.columns)
    (reports / "audit.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for filename, result in results.items():
        text = "# Detection profile: " + filename + "\n"
        for stage in ["before", "after"]:
            text += "\n## " + stage.title() + " cleaning\n"
            for item in ["head", "info", "describe"]:
                text += "\n### " + item + "\n\n```text\n" + result[stage][item] + "\n```\n"
        (reports / (filename + ".md")).write_text(text, encoding="utf-8")
        print(filename, result["decisions"])


if __name__ == "__main__":
    main()
