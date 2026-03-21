import io
import pandas as pd


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
        lines = content.strip().split('\n')

        # Detect delimiter by checking which produces more columns in some row
        # Try semicolon first (GoOut default)
        semicolon_max = max((len(line.split(';')) for line in lines), default=0)
        comma_max = max((len(line.split(',')) for line in lines), default=0)

        delimiter = ';' if semicolon_max >= comma_max else ','

        # Parse manually to preserve all rows regardless of column count
        rows = []
        for line in lines:
            row = line.split(delimiter)
            rows.append(row)

        header_idx = find_header_row(rows)

        # Now read with pandas using the detected delimiter and header
        return pd.read_csv(
            io.StringIO(content), delimiter=delimiter, header=header_idx, dtype=str
        )
