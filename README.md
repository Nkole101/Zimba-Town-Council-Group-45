# Zimba Town Council Group 45

## Bwalya administration dataset

This project contains the Bwalya scraper for the CSC 4792 data-mining lab. It collects contact points from the Zimba Town Council home and organizational pages, saves raw HTML evidence in `raw/`, and writes the required pipe-delimited file to `data/db-unza26-csc4792-zimba_town_council_admin.csv`.

### Setup in PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run

```powershell
.\.venv\Scripts\python.exe scripts\bwalya_admin_scraper.py
```

The script uses a real User-Agent and waits one second between requests. If Windows cannot validate the website certificate in the local environment, use the explicit fallback below and document it in the lab paper:

```powershell
.\.venv\Scripts\python.exe scripts\bwalya_admin_scraper.py --no-verify-ssl
```

The output is pipe-delimited (`|`). Open the generated CSV in a text editor to confirm. If the page contains named officials that require manual verification, place a pipe-delimited file with the same columns in `data/manual_admin_records.csv` and run:

```powershell
.\.venv\Scripts\python.exe scripts\bwalya_admin_scraper.py --manual-records data\manual_admin_records.csv
```
