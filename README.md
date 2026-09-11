# Zimba Town Council Group 45

## CDF projects dataset

The CDF scraper covers CDF project announcements only. Install the shared requirements using the setup below, then run:

```powershell
.\.venv\Scripts\python.exe scripts\cdf_scraper.py
python -m unittest discover -s tests -p test_cdf_parser.py -v
```

The reviewed CSV at `data/db-unza26-csc4792-zimba_town_council_cdf_projects.csv` contains 44 project/announcement records from 19 source posts. Source evidence is in `raw/cdf_projects/` and the cleaned source-post table is in `data/cdf_source_posts.csv`. Reproduce the reviewed snapshot with `python scripts/build_cdf_reviewed.py`; running the scraper alone produces unreviewed candidates. See [CDF collection and review instructions](docs/cdf_projects.md) and [handoff status](docs/cdf_handoff.md).


## Council administration dataset

### Setup in PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run

```powershell
.\.venv\Scripts\python.exe scripts\council_admin.py
```

The script uses a real User-Agent and waits one second between requests. If Windows cannot validate the website certificate in the local environment, use the explicit fallback below and document it in the lab paper:

```powershell
.\.venv\Scripts\python.exe scripts\council_admin.py --no-verify-ssl
```

The output is pipe-delimited (`|`). Open the generated CSV in a text editor to confirm. If the page contains named officials that require manual verification, place a pipe-delimited file with the same columns in `data/manual_admin_records.csv` and run:

```powershell
.\.venv\Scripts\python.exe scripts\council_admin.py --manual-records data\manual_admin_records.csv
```
