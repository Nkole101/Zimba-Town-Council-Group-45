# CDF projects

The reviewed handoff CSV is available with 44 announcement records from 19 source posts. See [handoff notes](cdf_handoff.md) for missing values, repeated-project interpretation and review decisions. Reproduce this fixed snapshot with `python scripts/build_cdf_reviewed.py`; a new scraper run produces candidates and must be reviewed separately.

Contribution for CSC 4792 Group 45, scoped to section 3 of the supplied task allocation. Uses requests, regular expressions and pandas. The administration and district profile datasets belong to the other team members.

From the repository root, with Python 3.10 or newer, use the shared requirements:

```powershell
python -m pip install -r requirements.txt
python scripts/cdf_scraper.py --project-dir .
python -m unittest discover -s tests -p test_cdf_parser.py -v
```

The scraper checks robots.txt, identifies itself with a course-specific User-Agent, verifies HTTPS certificates, and pauses at least one second between page requests. If robots.txt cannot be checked, collection stops. WordPress API discovery paginates up to `--max-pages` (default 10); sitemap and HTML listing discovery are fallbacks. Inspect the actual archive and raise the limit if needed: a bounded run does not establish complete archive coverage. Additional listing URLs and exact post URLs can be supplied using repeated `--listing-url` and `--seed-url` options.

For the council's certificate verification issue, explicitly opt out for the run:

```powershell
python scripts/cdf_scraper.py --no-verify-ssl
```

This sets the requests session's `verify` option to `False`, including the robots.txt request. Certificate verification remains enabled by default. Record the option in the collection methodology.

Outputs:

- `raw/cdf_projects/`: fetched source HTML and discovery responses, isolated from the administration scraper's evidence.
- `data/cdf_source_posts.csv`: pipe-delimited title, date, cleaned body and URL evidence table.
- `data/db-unza26-csc4792-zimba_town_council_cdf_projects.csv`: pipe-delimited candidate project records with the ten assigned columns.
- `data/cdf_scrape_failures.csv`: request failures, when present.

Every candidate must be reviewed against its saved source before handoff. Paragraph splitting can repeat one project across rows or combine several projects in one row. Keyword classification is provisional; verify sector, place, funding programme and status. Amounts remain blank when absent or when a paragraph contains several amounts. A blank is not zero. Do not use synthetic test examples as source data.

Use a fresh output folder for each collection run to avoid confusing earlier outputs with a failed run. The process exits nonzero when no candidates are produced or a post fetch fails. Record the actual row count, missing values, archive coverage and inaccessible pages in the handoff summary after review.
