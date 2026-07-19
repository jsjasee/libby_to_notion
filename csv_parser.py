from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"chapter", "quote"}


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def parse_libby_csv(csv_path: str) -> dict:
    """Read a Libby CSV and return grouped chapter data for import.

    Args:
        csv_path: Path to a single Libby CSV export file.

    Returns:
        A dict with row totals plus grouped quotes keyed by chapter.

    Raises:
        ValueError: If the file path is missing or required columns are absent.
    """
    if not csv_path:
        raise ValueError("Please upload a Libby CSV file.")

    dataframe = pd.read_csv(Path(csv_path))
    missing_columns = REQUIRED_COLUMNS.difference(dataframe.columns)
    if missing_columns:
        missing_list = ", ".join(sorted(missing_columns))
        raise ValueError(f"CSV is missing required columns: {missing_list}")

    grouped_chapters = {}
    has_note_column = "note" in dataframe.columns
    total_notes = 0

    for row in dataframe.iloc[::-1].itertuples(index=False):
        chapter = str(getattr(row, "chapter", "")).strip()
        quote = str(getattr(row, "quote", "")).strip()
        if not quote:
            continue

        if has_note_column:
            note = _clean_cell(getattr(row, "note", "")) # checks if that row has a value in the note column
            if note:
                total_notes += 1
            grouped_chapters.setdefault(chapter, []).append({"quote": quote, "note": note})
        else:
            grouped_chapters.setdefault(chapter, []).append(quote)

    return {
        "total_rows": len(dataframe.index),
        "total_chapters": len(grouped_chapters),
        "total_quotes": sum(len(quotes) for quotes in grouped_chapters.values()),
        "has_note_column": has_note_column,
        "total_notes": total_notes,
        "grouped_chapters": grouped_chapters,
    }
