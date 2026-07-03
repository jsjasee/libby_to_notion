from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"chapter", "quote"}


def parse_libby_csv(csv_path: str) -> dict:
    """Read a Libby CSV and return the normalized rows needed by the app.

    Args:
        csv_path: Path to a single Libby CSV export file.

    Returns:
        A dict with total row count and cleaned rows containing chapter and quote.

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

    cleaned_rows = []
    # dataframe.iloc[::-1] -> returns all the rows in reverse order
    # .itertuples() -> loops the rows as tuple-like objects, index=False means don't include the number (which is the index) in the tuple
    for row in dataframe.iloc[::-1].itertuples(index=False):
        # print(row)
        chapter = str(getattr(row, "chapter", "")).strip()
        quote = str(getattr(row, "quote", "")).strip()
        if not quote:
            continue
        cleaned_rows.append({"chapter": chapter, "quote": quote})

    return {
        "total_rows": len(dataframe.index),
        "total_quotes": len(cleaned_rows),
        "rows": cleaned_rows,
    }
