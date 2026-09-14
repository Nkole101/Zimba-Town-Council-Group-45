"""Combine the three dataset notebooks, preserving every source cell.

Run from the repository root. Add --execute to validate all code cells in one
shared Python namespace and refresh their saved outputs before writing.
"""
import argparse
import contextlib
import copy
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("CDF projects and source posts", "cdf_cleaning.ipynb"),
    ("Council administration", "council_admin_cleaning.ipynb"),
    ("District profile", "district_profile_cleaning.ipynb"),
]


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    cells = [markdown("""# Zimba Town Council: master cleaning notebook

CSC 4792 - Group 45

This notebook combines all content from the three individual cleaning notebooks,
in the order below. Original markdown and code cells are retained, including
dataset-specific Detect -> Judge -> Act decisions and handoff summaries.

1. [CDF projects and source posts](#cdf-section)
2. [Council administration](#admin-section)
3. [District profile](#district-section)

Run from the repository root with pandas installed (`python -m pip install -r
requirements.txt`). Run cells in order. The export cells write the cleaned CSVs
in `data/`; each section documents its preserved input snapshot. No network
access is needed. Variables may be reused between sections, so run each section
from its setup cell when working on it independently.

Scope: this combines the existing cleaning notebooks; it does not add scraping
code, a data-description paper, or other material absent from those notebooks.
""")]
    source_count = 0
    metadata = None
    for (title, filename), anchor in zip(SOURCES, ["cdf-section", "admin-section", "district-section"]):
        source = json.loads((ROOT / filename).read_text(encoding="utf-8"))
        if metadata is None:
            metadata = copy.deepcopy(source.get("metadata", {}))
        cells.append(markdown(f'<a id="{anchor}"></a>\n\n# {title}\n\nSource: `{filename}`\n'))
        for index, original in enumerate(source["cells"]):
            cell = copy.deepcopy(original)
            cell.pop("id", None)
            cell.setdefault("metadata", {})["master_source"] = {"notebook": filename, "cell_index": index}
            cells.append(cell)
            source_count += 1
    namespace = {"__name__": "__main__"}
    code_count = 0
    if args.execute and Path.cwd().resolve() != ROOT:
        raise RuntimeError("Run from the repository root")
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        code_count += 1
        if args.execute:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exec(compile("".join(cell["source"]), f"master-cell-{code_count}", "exec"), namespace)
            cell["execution_count"] = code_count
            cell["outputs"] = [{"output_type": "stream", "name": "stdout", "text": output.getvalue().splitlines(True)}]
    result = {"cells": cells, "metadata": metadata, "nbformat": 4, "nbformat_minor": 4}
    target = ROOT / "master_cleaning.ipynb"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {target.name}: {source_count} source cells, {code_count} code cells; executed={args.execute}")


if __name__ == "__main__":
    main()
