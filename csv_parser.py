from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"chapter", "quote", "percent", "timestamp"}


def _clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _sort_highlights(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Sort Libby highlights by reading position, then highlight timestamp.

    Args:
        dataframe: Raw Libby CSV rows with percent and timestamp columns.

    Returns:
        The same rows sorted from earliest reading position to latest.

    Raises:
        ValueError: If percent or timestamp values cannot be parsed.
    """
    sortable = dataframe.copy()
    sortable["_percent_sort"] = pd.to_numeric(
        sortable["percent"].astype(str).str.strip().str.rstrip("%"), # rstrip removes % from the RIGHT SIDE only
        errors="coerce", # this means that values that cannot be converted is turned to 'NaN'
    )
    sortable["_timestamp_sort"] = pd.to_datetime(
        sortable["timestamp"],
        format="%B %d, %Y %H:%M",
        errors="coerce",
    )
    if sortable[["_percent_sort", "_timestamp_sort"]].isna().any().any(): # this line catches all the 'NaN' values that failed to parse
        # sortable[["_percent_sort", "_timestamp_sort"]].isna() first returns a table of true / false. the first .any() checks if there's NaN values for each of the column
        # eg. _percent_sort True, _timestamp_sort False
        # the second any() checks if there are ANY COLUMNS with the true value, which means they have NaN values in there.
        raise ValueError("CSV has invalid percent or timestamp values.")

    return sortable.sort_values(
        ["_percent_sort", "_timestamp_sort"],
        kind="mergesort",
    ).drop(columns=["_percent_sort", "_timestamp_sort"])


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

    dataframe = _sort_highlights(dataframe)

    # grouped_chapters shape: chapter -> [{"quote": "...", "note": "..."}]
    grouped_chapters = {}
    has_note_column = "note" in dataframe.columns
    total_notes = 0

    for row in dataframe.itertuples(index=False):
        chapter = _clean_cell(getattr(row, "chapter", ""))
        quote = _clean_cell(getattr(row, "quote", ""))
        if not quote:
            continue

        if has_note_column:
            note = _clean_cell(getattr(row, "note", ""))
            if note:
                total_notes += 1
        else:
            note = ""
        grouped_chapters.setdefault(chapter, []).append({"quote": quote, "note": note}) # all quotes get a "note" value regardless of whether there's a note or not.

    return {
        "total_rows": len(dataframe.index),
        "total_chapters": len(grouped_chapters),
        "total_quotes": sum(len(quotes) for quotes in grouped_chapters.values()),
        "has_note_column": has_note_column,
        "total_notes": total_notes,
        "grouped_chapters": grouped_chapters,
    }
