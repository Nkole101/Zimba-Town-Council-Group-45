# Administration and district cleaning notebooks

Open `council_admin_cleaning.ipynb` or `district_profile_cleaning.ipynb` from the repository root and run cells in order with a Python environment containing pandas. The committed notebook outputs show a completed run. Reproduce both with:

```powershell
python scripts/create_admin_district_notebooks.py
```

Both notebooks implement Detect -> Judge -> Act with explicit pandas cells, preserve initial inputs in `raw/before_cleaning/`, and export to the existing pipe-delimited CSV paths. Subsequent runs replay those snapshots; archive/replace the snapshots deliberately before processing newly collected data. Original schemas remain unchanged.

The district notebook keeps four rows and 14 columns. Zimba's 2010 census, 2018 projection and 2022 census are separate observations, so name/level-only deduplication is inappropriate. Numeric columns use nullable numeric types; missing figures are not estimated. IQR analysis is separated by administrative level, flags no values in this small snapshot, and must not be interpreted as strong evidence of accuracy. Census sex totals are checked where all three values exist.

The administration notebook keeps two rows and nine columns. It preserves phone prefixes and missing supporting fields, normalizes email case and whitespace, and checks for conflicting same-URL records before deduplication. Phone numbers are identifiers, so numerical outlier analysis is not applied. No true duplicates are removed in either notebook.

Exports are reloaded and compared field by field. The CDF data and existing CDF notebook are not changed by this workflow. The district and administration notebooks use no web requests and do not claim new secondary-source verification.
