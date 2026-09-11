# Council Administration Cleaning Report

## Detect

- Input rows: 2
- Exact duplicate rows detected: 0
- Duplicate `source_url` values detected: 0
- Missing values were counted after standardizing blank cells to empty strings.

## Judge

- `source_url` is the traceability field. A row without it would not be auditable and is removed.
- `name`, `role_title`, `department`, `office_address`, `phone`, and `email` are supporting fields. Blanks are retained because the source did not publish those values clearly; no values were invented.
- The two records have different source URLs, so both represent distinct source pages and are retained.
- HTML entities in page titles were decoded, repeated whitespace was collapsed, phone values were normalized, and emails were lowercased.

## Act

- Rows removed for duplicate `source_url`: 0
- Rows removed for missing `source_url`: 0
- Final rows: 2

### Blank counts in the final file

- `record_id`: 0
- `name`: 2
- `role_title`: 2
- `department`: 2
- `phone`: 1
- `email`: 0
- `office_address`: 2
- `source_page`: 0
- `source_url`: 0
