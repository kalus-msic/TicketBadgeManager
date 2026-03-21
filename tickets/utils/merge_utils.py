import io
import pandas as pd
import csv


def find_header_row(rows):
    """Return index of first row with >= 4 non-empty, non-nan string cells.

    GoOut metadata rows have at most 2 real string cells.
    The actual data header row always has 4+ column names.
    """
    _EMPTY = {'nan', 'None', 'none', ''}

    for idx, row in enumerate(rows):
        string_cells = sum(
            1 for v in row
            if isinstance(v, str) and v.strip() and v.strip() not in _EMPTY
        )
        if string_cells >= 4:
            return idx

    raise ValueError(
        "Could not detect table header. Expected GoOut CSV or XLSX format "
        "(first row with 4 or more non-empty text columns)."
    )


def read_file_to_dataframe(file_bytes, filename):
    """Parse a CSV or XLSX file into a DataFrame, skipping GoOut metadata rows.

    Uses dtype=str throughout to prevent integer order numbers being coerced
    to floats (e.g. 34302271 becoming '34302271.0').

    Args:
        file_bytes: raw bytes of the file
        filename: original filename (used to detect extension)

    Returns:
        pd.DataFrame with correct column names and data rows only
    """
    if filename.lower().endswith('.xlsx'):
        raw = pd.read_excel(
            io.BytesIO(file_bytes), header=None, engine='openpyxl', dtype=str
        )
        header_idx = find_header_row(raw.values.tolist())
        return pd.read_excel(
            io.BytesIO(file_bytes), header=header_idx, engine='openpyxl', dtype=str
        )
    else:
        content = file_bytes.decode('utf-8-sig')

        # Try semicolon first (GoOut default), fall back to comma
        delimiter = ';'

        # Parse with csv module to handle variable column counts
        lines = list(csv.reader(io.StringIO(content), delimiter=delimiter))
        raw = pd.DataFrame(lines)

        if len(raw.columns) == 1:
            delimiter = ','
            lines = list(csv.reader(io.StringIO(content), delimiter=delimiter))
            raw = pd.DataFrame(lines)

        # Convert to string dtype to match pandas behavior
        raw = raw.astype(str)

        header_idx = find_header_row(raw.values.tolist())
        return pd.read_csv(
            io.StringIO(content), delimiter=delimiter, header=header_idx, dtype=str
        )
