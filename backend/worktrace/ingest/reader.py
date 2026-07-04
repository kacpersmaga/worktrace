"""Reading CSV exports without trusting them.

Exports from task-mining tools are not clean tables: they come in different
encodings, may be gzipped, carry multi-line OCR text inside quotes and end with a
block of "Applied filters" lines that look like data rows to a naive reader.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

ENCODINGS = ("utf-8-sig", "cp1250", "latin-1")
CHUNK_ROWS = 250_000


@dataclass
class RawExport:
    """Column names plus a way to stream the rows, so a 160 MB file never sits in memory twice."""

    path: Path
    encoding: str
    columns: list[str]
    metadata: dict[str, str] = field(default_factory=dict)
    footer_rows: int = 0

    def chunks(self, usecols: list[str] | None = None) -> Iterator[pd.DataFrame]:
        reader = pd.read_csv(
            self.path,
            dtype=str,
            keep_default_na=False,
            encoding=self.encoding,
            encoding_errors="replace",
            usecols=usecols,
            chunksize=CHUNK_ROWS,
            on_bad_lines="skip",
        )
        for chunk in reader:
            yield self._without_footer(chunk)

    def _without_footer(self, chunk: pd.DataFrame) -> pd.DataFrame:
        first = chunk.columns[0]
        rest = chunk.drop(columns=first)
        footer = rest.eq("").all(axis=1) & chunk[first].str.contains(":", regex=False)
        for line in chunk.loc[footer, first]:
            key, _, value = line.partition(":")
            if value.strip():
                self.metadata[key.strip()] = value.strip()
        self.footer_rows += int(footer.sum())
        return chunk.loc[~footer]


def open_export(path: str | Path) -> RawExport:
    """Detect the encoding and header of a CSV (plain or .gz) without loading it."""
    path = Path(path)
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            header = pd.read_csv(path, dtype=str, nrows=200, encoding=encoding, keep_default_na=False)
        except UnicodeDecodeError as error:
            last_error = error
            continue
        except pd.errors.EmptyDataError as error:
            raise ValueError("The file is empty.") from error
        columns = [str(column).strip() for column in header.columns]
        return RawExport(path=path, encoding=encoding, columns=columns)
    raise ValueError(f"Could not decode {path.name}: {last_error}")
