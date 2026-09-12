"""Build and execute the standalone CDF Part 1 notebook with captured outputs."""
import contextlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cells = []


def markdown(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)})


def code(text):
    cells.append({"cell_type": "code", "metadata": {}, "source": text.splitlines(True),
                  "execution_count": None, "outputs": []})


markdown("""# CDF datasets: Part 1 pandas cleaning
This notebook implements sections 1.1-1.8 of the supplied cleaning instructions for CDF projects and source posts only. The manually reviewed extraction snapshot is the input, not a substitute for cleaning. Every cleaning operation below uses pandas; original snapshots and narrative evidence are preserved.

Run from the repository root. No network access is needed. The final cells export the existing submission filenames. This notebook covers only the CDF contribution, not the group's complete Part 2 notebook.
""")
code('''from pathlib import Path
import re
import pandas as pd

ROOT = Path.cwd()
assert (ROOT / "scripts/clean_cdf.py").exists(), "Run this notebook from the repository root"
PROJECT_FILE = "db-unza26-csc4792-zimba_town_council_cdf_projects.csv"
SOURCE_FILE = "cdf_source_posts.csv"
snapshot = ROOT / "raw/cdf_projects/before_cleaning"
cdf = pd.read_csv(snapshot / PROJECT_FILE, sep="|")
posts = pd.read_csv(snapshot / SOURCE_FILE, sep="|")
for name, df in [("cdf", cdf), ("posts", posts)]:
    print(name, df.shape)
    print(df.head().to_string(index=False))
    df.info()
    print(df.describe(include="all").to_string())
''')
markdown("""## 1.2 Duplicates: Detect
Count exact duplicates and repeated source URLs, and display the projects sharing URLs. A repeated URL is a candidate for investigation, not proof of duplicated project data.
""")
code('''print("Exact project duplicates:", cdf.duplicated().sum())
print("Repeated project URLs:", cdf.duplicated(subset=["source_url"]).sum())
print("Exact source-post duplicates:", posts.duplicated().sum())
print("Repeated source-post URLs:", posts.duplicated(subset=["url"]).sum())
print(cdf.loc[cdf.duplicated(subset=["source_url"], keep=False),
              ["project_id", "project_name", "source_url"]].to_string(index=False))
''')
markdown("""## 1.2 Duplicates: Judge and Act
The 25 repeated project URLs refer to different projects bundled in 19 articles. URL-only deduplication would delete valid records, so the PDF example's one-project-per-article assumption does not apply. Retain distinct projects and separate-date updates; use all original fields except the sequential ID to remove only true project duplicates. Source articles are deduplicated by URL only after confirming no URL has conflicting contents.
""")
code('''project_keys = [c for c in cdf.columns if c != "project_id"]
cdf_clean = cdf.drop_duplicates(subset=project_keys, keep="first").copy()
source_variants = posts.drop_duplicates()
assert not source_variants.duplicated(subset=["url"]).any(), "Review conflicting source versions first"
posts_clean = posts.drop_duplicates(subset=["url"], keep="first").copy()
print("Project duplicates removed:", len(cdf) - len(cdf_clean))
print("Source duplicates removed:", len(posts) - len(posts_clean))
''')
markdown("""## 1.3 Missing values: Detect
Use `.isnull().sum()` before deciding whether gaps make a record unusable.
""")
code('''print("Project missing values:\\n", cdf_clean.isnull().sum())
print("Source missing values:\\n", posts_clean.isnull().sum())
''')
markdown("""## 1.3 Missing values: Judge and Act
Funding and status may be targets in later analyses, but useful records remain usable for other questions. Follow the PDF's explicit action table: leave 33 unknown amounts blank, label four unstated statuses `unspecified`, and retain two missing locations without guessing. The illustrative `dropna(status)` snippet is not appropriate here. Description and body text are supporting features and remain unchanged; no rows are dropped for missing targets in this snapshot.
""")
code('''cdf_clean["status"] = cdf_clean["status"].astype("string").str.strip().str.lower().replace("", pd.NA).fillna("unspecified")
# Keep amounts as numeric missing values during analysis, exporting them as blank cells.
funding = pd.to_numeric(cdf_clean["funding_amount_zmw"], errors="coerce")
assert not (cdf_clean["funding_amount_zmw"].notna() & funding.isna()).any(), "Review invalid amounts"
cdf_clean["funding_amount_zmw"] = funding
print(cdf_clean.isnull().sum())
print(cdf_clean["status"].value_counts(dropna=False))
''')
markdown("""## 1.4 Outliers: Detect
Compute quartiles and 1.5-IQR bounds on observed funding amounts. Dates and numbers embedded in article text are not measurement columns. Repeated announcements mean these amounts must not be summed as total expenditure.
""")
code('''Q1 = cdf_clean["funding_amount_zmw"].quantile(0.25)
Q3 = cdf_clean["funding_amount_zmw"].quantile(0.75)
IQR = Q3 - Q1
lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
outliers = cdf_clean[(cdf_clean["funding_amount_zmw"] < lower) | (cdf_clean["funding_amount_zmw"] > upper)]
print({"Q1": Q1, "Q3": Q3, "IQR": IQR, "lower": lower, "upper": upper})
print(outliers[["project_name", "funding_amount_zmw", "source_url"]].to_string(index=False))
''')
markdown("""## 1.4 Outliers: Judge and Act
No values are flagged in this snapshot, so no source investigations or corrections are necessary. Keep all observed values. If a later dataset produces flags, stop to review their saved source HTML/URLs; do not delete an extreme value simply because it is large.
""")
code('''assert outliers.empty, "Review flagged amounts against their sources before continuing"
assert (cdf_clean["funding_amount_zmw"].dropna() > 0).all()
print("No outliers removed or corrected.")
''')
markdown("""## 1.5 Optional text cleaning: Judge and Act
Preserve original narrative evidence and add separate analysis features. Remove HTML first, then case-fold, remove punctuation through word tokenization and remove an explicit small stopword list. Regex tokenization uses the allowed toolkit without NLTK downloads; negations such as `not` are retained. This is a documented regex equivalent of the optional example, not a claim to use NLTK's tokenizer or full English stopword corpus.
""")
code('''stop_words = set("a an the and or of to in on at for from by with as is are was were be been being it its this that these those".split())
def clean_text(text):
    if pd.isna(text):
        return ""
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = text.casefold()
    tokens = re.findall(r"\\b\\w+\\b", text)
    return " ".join(token for token in tokens if token not in stop_words)

cdf_clean["description_clean"] = cdf_clean["description"].apply(clean_text)
posts_clean["body_text_clean"] = posts_clean["body_text"].apply(clean_text)
print(cdf_clean[["description", "description_clean"]].head().to_string(index=False))
''')
markdown("""## 1.6 Standardize types and categories
Convert dates with `pd.to_datetime`, funding with `pd.to_numeric`, and strip/lowercase categories. Stop on invalid nonblank values rather than silently lose evidence. CSV files do not store pandas dtypes, so dates serialize in ISO format and numeric gaps serialize as blanks.
""")
code('''for frame, column in [(cdf_clean, "date_reported"), (posts_clean, "date")]:
    parsed = pd.to_datetime(frame[column], errors="coerce")
    assert not (frame[column].notna() & parsed.isna()).any(), "Review invalid dates"
    frame[column] = parsed
cdf_clean["funding_amount_zmw"] = pd.to_numeric(cdf_clean["funding_amount_zmw"], errors="coerce")
for column in ["status", "sector"]:
    cdf_clean[column] = cdf_clean[column].astype("string").str.strip().str.lower()
assert cdf_clean["status"].isin(["planned", "ongoing", "near_completion", "completed", "unspecified"]).all()
assert cdf_clean["sector"].isin(["education", "health", "water_sanitation", "agriculture", "infrastructure", "other"]).all()
assert cdf_clean["source_url"].notna().all() and posts_clean["url"].notna().all()
for name, df in [("cdf_clean", cdf_clean), ("posts_clean", posts_clean)]:
    print(name, df.shape)
    df.info()
    print(df.describe(include="all").to_string())
''')
markdown("""## 1.7 Export and verify
Export only the two CDF submission files, with their original filenames, pipe separators and no index. Reload both exports to validate their dimensions and columns. Compare this explicitly implemented notebook pipeline against the standalone pandas cleaner to prevent divergent outputs.
""")
code('''import importlib.util
spec = importlib.util.spec_from_file_location("cdf_cleaning_script", ROOT / "scripts/clean_cdf.py")
cleaner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cleaner)
expected_cdf, _ = cleaner.clean(cdf, True)
expected_posts, _ = cleaner.clean(posts, False)
pd.testing.assert_frame_equal(cdf_clean, expected_cdf)
pd.testing.assert_frame_equal(posts_clean, expected_posts)
for filename, df in [(PROJECT_FILE, cdf_clean), (SOURCE_FILE, posts_clean)]:
    target = ROOT / "data" / filename
    exported = df.to_csv(sep="|", index=False, date_format="%Y-%m-%d", na_rep="").encode("utf-8-sig")
    # Do not rewrite identical exports, which may be open in a spreadsheet app.
    if not target.exists() or target.read_bytes() != exported:
        target.write_bytes(exported)
    reopened = pd.read_csv(target, sep="|")
    assert reopened.shape == df.shape
    assert list(reopened.columns) == list(df.columns)
    assert "|" in target.read_text(encoding="utf-8-sig").splitlines()[0]
    print(filename, reopened.shape)
print("Notebook and standalone pandas pipeline agree.")
''')
markdown("""## 1.8 Handoff
**Projects:** 44 announcement rows and 11 columns; no true duplicates removed. Unknown amounts remain blank in 33 rows and locations in two; four unstated statuses are `unspecified`. No IQR outliers were flagged or removed. Original descriptions accompany the new `description_clean` feature.

**Source posts:** 29 article rows and five columns; no duplicates removed and no missing original fields. Dates are standardized and original narrative text accompanies `body_text_clean`. Numeric IQR analysis does not apply to this text evidence table. Export round trips and agreement with the standalone pandas pipeline are checked above.

Supporting evidence: `raw/cdf_projects/before_cleaning/`, `raw/cdf_projects/post_*.html`, and `docs/cdf_cleaning/README.md`. This preserves legitimate multi-project articles and is not a unique-project expenditure register.
""")


def main():
    namespace = {"__name__": "__main__"}
    counter = 0
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        counter += 1
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exec(compile("".join(cell["source"]), f"notebook-cell-{counter}", "exec"), namespace)
        cell["execution_count"] = counter
        cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": stream.getvalue().splitlines(True)}]
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.14"}}, "nbformat": 4, "nbformat_minor": 4}
    (ROOT / "cdf_cleaning.ipynb").write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Executed {counter} code cells and saved cdf_cleaning.ipynb")


if __name__ == "__main__":
    main()
