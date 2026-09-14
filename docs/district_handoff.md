# District-profile cleaning handoff

The district-profile cleaning workflow is implemented in `data/Cleaning.ipynb`. The final cleaned file is `data/db-unza26-csc4792-zimba_town_council_district_profile.csv`.

## Final dataset

The final pipe-delimited CSV contains 4 rows and 15 columns. The original scraper schema contributes 14 columns; the cleaning stage adds `notes_clean` while preserving the original `notes` column.

Rows represent:

- Zimba district population observation for 2010.
- Zimba district population observation for 2018.
- Zimba district population observation for 2022.
- Mapatizya constituency record, with population-related fields blank where the source does not publish values.

## Duplicate handling

Potential duplicates were detected with pandas `duplicated()` using repeated `name` and `level` values. This identified the three Zimba district records as repeated administrative entities for review.

During judgement, `population_year` was considered. The 2010, 2018, and 2022 Zimba rows are distinct observations rather than duplicate copies. The final logical duplicate key was `name`, `level`, and `population_year`.

The action used pandas `drop_duplicates()` with that three-field key and `keep="first"`. The current dataset contained 0 genuine duplicates, so 0 rows were removed. All four records were retained.

## Missing values

Missing values were detected with `district.isnull().sum()`. The notebook then copied the data without dropping rows or inventing replacements.

Population and area are target-like measures for the district profile, while population year, demographic breakdowns, households, neighbouring districts, and source URLs provide supporting or evidential information. Mapatizya has legitimate blanks for population, population year, area, households, demographic breakdowns, and neighbouring districts because those values are not published for the constituency record. Blank `secondary_source_url` values indicate that no secondary source was needed for those records.

These blanks were preserved rather than replaced with zeroes, estimates, or guesses. The source-supported missingness means the Mapatizya row remains useful and auditable.

## Outlier handling

The notebook checked `population` and `area_km2` using the interquartile range method. For each available variable, it calculated:

- Lower bound = Q1 - 1.5 x IQR
- Upper bound = Q3 + 1.5 x IQR

No population or area rows were flagged. No values were corrected or removed. An IQR result was treated as a prompt for source review rather than automatic proof of an error.

## Text preprocessing

The original `notes` column was preserved. A new `notes_clean` column was created from it using the notebook's `clean_text()` function.

The applied steps were:

- Convert missing notes to an empty string.
- Remove HTML tags.
- Apply case folding by converting text to lowercase.
- Remove punctuation.
- Tokenise with NLTK `word_tokenize()`.
- Remove English stop words.
- Join the remaining tokens into cleaned text.

No stemming, lemmatisation, spelling correction, or other text-processing method was applied.

## Other preprocessing and export

The notebook converted `population` and `area_km2` to numeric values with `pd.to_numeric(..., errors="coerce")`. Available categorical values were standardised by converting them to strings, stripping surrounding whitespace, and converting them to lowercase. In this district file, this applies to the available `level` field.

The cleaned data was exported with:

```python
district_clean.to_csv(output_path, sep="|", index=False)
```

The exported file was reopened with the pipe separator to verify the delimiter, schema, and absence of an unnamed index column.

## Outcome and limitation

The final handoff result is:

- Final shape: 4 rows x 15 columns.
- Genuine duplicate rows removed: 0.
- Outliers corrected or removed: 0.
- Legitimate source-supported blanks retained, especially for the Mapatizya constituency record.

The three Zimba district rows are time-specific observations and should not be collapsed merely because they share the same `name` and `level`. The district dataset is also limited to the records and values supported by the available council and cross-checked sources; unavailable constituency-level values remain blank rather than being estimated.
