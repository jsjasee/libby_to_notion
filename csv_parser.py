from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"chapter", "quote"}


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
    for row in dataframe.iloc[::-1].itertuples(index=False):
        chapter = str(getattr(row, "chapter", "")).strip()
        quote = str(getattr(row, "quote", "")).strip()
        if not quote:
            continue
        grouped_chapters.setdefault(chapter, []).append(quote)
        # chapter will be the key to that dictionary, if chapter is not a key, then grouped_chapters[chapter] = []
        # if there's a value for that chapter key, then we will just append that quote to the list
        # TLDR: The setdefault() method returns the value of the item with the specified key but it will insert the value for that key if key does not exist.

    return {
        "total_rows": len(dataframe.index),
        "total_chapters": len(grouped_chapters),
        "total_quotes": sum(len(quotes) for quotes in grouped_chapters.values()),
        "grouped_chapters": grouped_chapters,
    }
