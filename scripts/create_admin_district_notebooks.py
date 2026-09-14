"""Generate and execute two standalone pandas cleaning notebooks offline."""
import contextlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(kind):
    district = kind == "district_profile"
    title = "District profile" if district else "Council administration"
    suffix = "district_profile" if district else "admin"
    cells = []

    def md(text):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)})

    def code(text):
        cells.append({"cell_type": "code", "metadata": {}, "source": text.splitlines(True), "execution_count": None, "outputs": []})

    md(f"""# {title} cleaning: Detect -> Judge -> Act
This notebook uses pandas and regex to inspect, clean and export only the {title.lower()} dataset. Run from the repository root. Input is preserved on first execution under `raw/before_cleaning/`; later runs replay that snapshot. No web requests or inferred demographic/contact values are introduced. The CDF datasets are not modified.
""")
    code(f'''from pathlib import Path
import html
import re
import shutil
import pandas as pd

ROOT = Path.cwd()
filename = "db-unza26-csc4792-zimba_town_council_{suffix}.csv"
target = ROOT / "data" / filename
snapshot = ROOT / "raw/before_cleaning" / filename
assert target.exists(), "Run from the repository root"
snapshot.parent.mkdir(parents=True, exist_ok=True)
if not snapshot.exists():
    shutil.copyfile(target, snapshot)
# Read as strings so phone prefixes and identifiers survive loading.
raw = pd.read_csv(snapshot, sep="|", dtype="string")
print("Input shape:", raw.shape)
print(raw.head().to_string(index=False))
raw.info()
print(raw.describe(include="all").to_string())
print("Missing values:\\n", raw.isnull().sum())
''')
    md("""## Duplicates and text normalization: Detect
Inspect exact duplicates and repeated source URLs before making removal decisions. Decode HTML entities and collapse whitespace in ordinary text. Preserve URL punctuation, telephone prefixes and names; these are evidence fields, not a bag of words.
""")
    code('''print("Exact duplicate rows:", raw.duplicated().sum())
print("Repeated source URLs:", raw.duplicated(subset=["source_url"]).sum())
clean = raw.copy()
def normalize(value):
    if pd.isna(value):
        return pd.NA
    return re.sub(r"\\s+", " ", html.unescape(str(value))).strip() or pd.NA
for column in clean.columns:
    if column.endswith("url"):
        clean[column] = clean[column].str.strip().replace("", pd.NA)
    else:
        clean[column] = clean[column].map(normalize).astype("string")
''')
    if district:
        md("""## Duplicates: Judge and Act
Three Zimba rows report 2010 census data, a 2018 projection and 2022 census data. Neither a shared URL nor name/level alone makes these duplicates. Remove only identical non-ID records and check name/level/year for conflicting observations. Preserve projection notes and report years so the observations are not misrepresented as equivalent census counts.
""")
        code('''clean["level"] = clean["level"].str.lower().str.strip()
keys = [column for column in clean.columns if column != "record_id"]
before = len(clean)
clean = clean.drop_duplicates(subset=keys, keep="first").copy()
duplicates_removed = before - len(clean)
conflicts = clean[clean.duplicated(subset=["name", "level", "population_year"], keep=False)]
print("True duplicates removed:", duplicates_removed)
print("Conflicting name/level/year records:", len(conflicts))
assert conflicts.empty, "Review conflicting observations before export"
''')
        md("""## Missing values and types: Detect -> Judge -> Act
Population and area are potential targets for demographic analyses; year is essential context for a population observation. Male/female counts and household counts are numeric supporting features or targets for other questions. Missing values are retained because the published constituency row is still useful as an administrative reference, and later-year district rows remain useful without sex/household breakdowns. Never copy a district total into a constituency row or carry 2010 counts forward to 2022. Province, neighbors, notes and secondary URLs are supporting features. A missing secondary URL means no secondary source is recorded, not a missing primary source.

Use `pd.to_numeric(errors='coerce')` and check whether conversion would discard a nonblank input. No outside-source supplementation is claimed. Missing demographic figures remain an explicitly documented limitation.
""")
        code('''print(clean.isnull().sum())
numeric = ["population", "population_year", "population_male", "population_female", "households", "area_km2"]
for column in numeric:
    original = clean[column]
    values = pd.to_numeric(original, errors="coerce")
    assert not (original.notna() & values.isna()).any(), f"Review invalid {column}"
    assert (values.dropna() >= 0).all(), f"Review negative {column}"
    if column != "area_km2":
        assert (values.dropna() % 1 == 0).all(), f"Review fractional {column}"
        clean[column] = values.astype("Int64")
    else:
        clean[column] = values.astype("Float64")
assert clean.loc[clean["population"].notna(), "population_year"].notna().all()
assert clean["level"].isin(["district", "constituency", "ward"]).all()
both = clean[["population", "population_male", "population_female"]].notna().all(axis=1)
assert (clean.loc[both, "population_male"] + clean.loc[both, "population_female"] == clean.loc[both, "population"]).all()
''')
        md("""## Outliers: Detect -> Judge -> Act
Compute 1.5-IQR fences separately by administrative level, excluding missing measurements and year identifiers. With only three district population observations, one sex/household observation and a repeated district area, these diagnostics are weak: no flags does not establish accuracy. Do not compare constituency and district populations as if they were the same measurement scale. A future flagged value requires checking its source; this notebook stops rather than removing or correcting it automatically.
""")
        code('''iqr_rows = []
flagged_indices = set()
for level, group in clean.groupby("level"):
    for column in ["population", "population_male", "population_female", "households", "area_km2"]:
        values = group[column].dropna().astype(float)
        if values.empty:
            continue
        Q1, Q3 = values.quantile([0.25, 0.75])
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        flags = values[(values < lower) | (values > upper)]
        flagged_indices.update(flags.index)
        iqr_rows.append({"level": level, "column": column, "n": len(values), "lower": lower, "upper": upper, "flags": len(flags)})
print(pd.DataFrame(iqr_rows).to_string(index=False))
print("Flagged records:", len(flagged_indices))
assert not flagged_indices, "Review source evidence for flagged values before export"
outliers_removed = outliers_corrected = 0
''')
    else:
        md("""## Duplicates: Judge and Act
The current file has two records from different contact pages. Remove exact duplicates excluding record IDs; only deduplicate by URL after confirming remaining rows on that URL have identical contents. Different officials or departments may share a page, so conflicting same-URL rows require review instead of silently keeping the first. This gives the same result as the existing administration cleaner on the current data while protecting future multi-record pages.
""")
        code('''before = len(clean)
clean = clean.drop_duplicates(subset=[c for c in clean.columns if c != "record_id"], keep="first").copy()
assert not clean.duplicated(subset=["source_url"]).any(), "Review distinct records sharing a page"
clean = clean.drop_duplicates(subset=["source_url"], keep="first").copy()
duplicates_removed = before - len(clean)
print("Duplicates removed:", duplicates_removed)
''')
        md("""## Missing values: Detect -> Judge -> Act
This contact directory has no predefined prediction target. Names, role titles, departments, telephone numbers, emails and addresses are supporting features; do not invent a person's identity or discard a usable email-only contact point. Missing source URLs make a record unauditable and require review. Retain other gaps as blank cells. Keep phone values as strings, including the leading zero. Lowercase emails and normalize phone whitespace without guessing country codes or altering published digits.

IQR is not applicable: this file contains no numeric measurement columns. Phone numbers and record IDs are identifiers, not quantities; outliers corrected/removed are therefore not applicable rather than evidence of an IQR test.
""")
        code('''print("Missing values:\\n", clean.isnull().sum())
clean["email"] = clean["email"].str.lower()
clean["phone"] = clean["phone"].str.replace(r"\\s+", " ", regex=True).str.strip()
email_pattern = r"[^\\s@]+@[^\\s@]+\\.[^\\s@]+"
invalid_email = clean["email"].notna() & ~clean["email"].str.fullmatch(email_pattern, na=False)
print("Email syntax flags:", int(invalid_email.sum()))
assert not invalid_email.any(), "Review email syntax without guessing a replacement"
print("IQR: not applicable; no numeric measurements")
''')
    md("""## Final validation and export
Preserve the original columns and source links. Optional punctuation removal/tokenization is omitted for this structured directory/profile: it would damage contacts and is unnecessary for the demographic measurements. Narrative notes remain intact. Export with `sep='|'` and `index=False`, retaining blanks, then reload as strings to check every exported field and schema. Existing identical files are not rewritten, allowing a file to remain open in a spreadsheet application.
""")
    code('''assert clean["source_url"].notna().all(), "Review missing traceability URLs"
assert clean["source_url"].str.match(r"https?://", na=False).all()
assert clean["record_id"].notna().all() and clean["record_id"].is_unique
assert list(clean.columns) == list(raw.columns)
clean.info()
print(clean.describe(include="all").to_string())
exported = clean.to_csv(sep="|", index=False, na_rep="").encode("utf-8-sig")
if target.read_bytes() != exported:
    target.write_bytes(exported)
roundtrip = pd.read_csv(target, sep="|", dtype="string")
assert roundtrip.shape == clean.shape
pd.testing.assert_frame_equal(roundtrip.fillna(""), clean.astype("string").fillna(""), check_dtype=False)
print("Final rows:", len(clean), "columns:", len(clean.columns))
print("Duplicates removed:", duplicates_removed)
print("Final missing values:\\n", clean.isnull().sum())
print("Saved:", filename)
''')
    md("""## Handoff summary
""" + ("""The district profile retains four rows and 14 columns, including the separate 2010 census, 2018 projection and 2022 census observations. No true duplicates are removed, and no IQR outliers are corrected or removed; the small sample limits outlier inference. Missing constituency measurements and later-year sex/household breakdowns remain blank rather than estimated. Notes and source URLs are preserved, and integer measurements use nullable integer types during processing.
""" if district else """The administration directory retains two rows and nine columns, with no duplicates removed. Missing names, roles, departments and addresses remain blank in both records, while one telephone number is missing; both records retain emails and source URLs. Text whitespace/entities and email case are normalized while telephone digits and prefixes remain unchanged. Numeric outlier analysis is not applicable to this contact directory.
"""))
    return cells


def main():
    for kind in ["district_profile", "council_admin"]:
        cells = build(kind)
        namespace = {"__name__": "__main__"}
        count = 0
        for cell in cells:
            if cell["cell_type"] != "code":
                continue
            count += 1
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                exec(compile("".join(cell["source"]), f"{kind}-cell-{count}", "exec"), namespace)
            cell["execution_count"] = count
            cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": stream.getvalue().splitlines(True)}]
        notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 4}
        path = ROOT / f"{kind}_cleaning.ipynb"
        path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Created {path.name}: {count} cells executed successfully")


if __name__ == "__main__":
    main()
