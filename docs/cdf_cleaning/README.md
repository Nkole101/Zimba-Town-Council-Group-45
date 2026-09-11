# Part 1 — CDF cleaning handoff

Scope: only the CDF projects and source-post CSVs. This implements Part 1 of the supplied cleaning instructions, using pandas and regex. The administration/district data and Part 2 notebook assembly are outside this change.

## Run and reproduce

```powershell
python -m pip install -r requirements.txt
python scripts/clean_cdf.py
python -m unittest discover -s tests -v
```

The script preserves both input CSVs under `raw/cdf_projects/before_cleaning/` on its first run and always replays that snapshot afterward. Final CSVs use their existing names in `data/`, pipe separators, UTF-8 and no index. Dates are datetime columns during processing and serialize as ISO dates; funding is numeric with blank missing values. `audit.json` and the per-file profile reports record before/after `.head()`, `.info()`, `.describe()`, missing counts and decisions.

## Detect → Judge → Act: duplicates

**Detect:** 44 project rows reference 19 articles, giving 25 repeated URL occurrences. No exact project duplicates, repeated project-name/URL pairs, or source-post duplicates were found; the source table has 29 distinct URLs.

**Judge:** the PDF's URL-only deduplication example assumes one project per article. Our saved sources explicitly bundle distinct projects. Applying that example literally would delete 25 valid records. Project IDs are sequential labels and are excluded from duplicate comparison; dates and project details remain in the comparison. Similar records on different report dates are legitimate updates and must not be collapsed.

**Act:** remove only rows identical in all original non-ID fields. Flag same-name/same-URL project variants and same-URL/different-content source variants for review rather than discard them. No rows were removed in this snapshot.

## Detect → Judge → Act: missing values

**Detect:** projects have 33 missing amounts, four missing statuses and two missing constituency/ward values. Source posts have no missing original fields.

**Judge:** funding and status may be analysis targets, but the PDF's explicit column-action table preserves usable records with missing amounts and labels genuinely unstated statuses `unspecified`. This takes precedence over its illustrative status-drop code: dropping those rows here would discard useful project evidence. Location is a supporting feature and cannot be inferred safely from a speaker's name or title.

**Act:** preserve all rows, retain blank funding/location values, and label the four missing statuses `unspecified`. No amount, location or project status was inferred. No rows were removed for missing target values.

## Detect → Judge → Act: outliers

**Detect:** IQR calculation used the 11 reported amounts, excluding missing values. Q1 is K700,000, Q3 is K1,922,924.31, and the IQR fences are -K1,134,386.465 and K3,757,310.775. No amounts fall outside these bounds.

**Judge:** no outliers need further source investigation in this snapshot. IQR cannot validate a source's truth; it only detects statistical extremes. These rows include repeated announcements and are not independent expenditure observations, so their sum is not total CDF expenditure. Source-post IDs, dates and figures inside narrative text are not numeric measurement columns for an IQR test.

**Act:** retain every reported amount; no values were corrected, clipped or removed. The script stops for source review if a future input contains IQR flags or invalid amounts/dates rather than silently deleting them.

## Text, types and categories

Original `description`, `body_text`, titles and URLs are preserved. New `description_clean` and `body_text_clean` columns remove HTML first, case-fold, tokenize word characters while excluding punctuation, and remove an explicit small stopword list. This optional regex pipeline avoids NLTK downloads; the exact stopword list is recorded in the script and keeps negations such as `not`. These derived columns are for text analysis, not interpreting costs or replacing evidence.

Status and sector are stripped and lowercased, then checked against permitted categories. Missing statuses use the additional category `unspecified` required by this cleaning brief. No new project IDs are assigned. The final files have 44 rows/11 columns and 29 rows/5 columns respectively, including the optional text features.

## Handoff summaries

**CDF projects:** The final dataset contains 44 announcement records, with zero duplicate rows removed. Thirty-three funding amounts and two locations remain blank because the sources do not establish unambiguous values; four missing statuses are now `unspecified`. No IQR outliers were flagged and no amounts were altered. Distinct projects sharing an article and updates on different dates are retained; original descriptions accompany `description_clean`.

**CDF source posts:** The final dataset contains 29 source articles, with zero duplicates removed and no missing original fields. Dates were standardized and `body_text_clean` was added while retaining the full original text. Numeric IQR analysis does not apply to this evidence table. Both exports were reloaded to verify column names, row counts and pipe-delimited format.

Running the scraper or review builder replaces project data with pre-cleaning outputs; rerun this cleaning script to restore the cleaned snapshot. To clean a genuinely new collection, deliberately archive/replace the input snapshot first; do not assume replaying an old snapshot incorporates new articles.
