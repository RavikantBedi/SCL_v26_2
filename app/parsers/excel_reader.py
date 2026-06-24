import re
import polars as pl
import pandas as pd
from pathlib import Path
from app.core.logger import get_logger

logger = get_logger()


class ExcelReader:
    """
    Reads .xls and .xlsx files robustly.
    Strategy:
      1. Try polars calamine (fast, handles most files)
      2. Fallback to pandas with proper encoding handling
    """

    # Matches pandas' auto-generated names for blank/merged header cells,
    # e.g. "Unnamed: 8", "Unnamed: 13"
    _UNNAMED_COL_RE = re.compile(r"^unnamed:\s*\d+$", re.IGNORECASE)

    def read(self, file_path: str) -> pl.DataFrame:

        logger.info(f"Reading Excel File: {file_path}")

        ext = Path(file_path).suffix.lower()

        # ── Strategy 1: polars + calamine ─────────────────────────────────
        try:
            df = pl.read_excel(file_path, engine="calamine")
            df = self._drop_unnamed(df)
            logger.info(f"Rows Loaded (calamine): {df.height}")
            logger.info(f"Columns: {df.columns}")
            return self._sanitize_safe(df, file_path)

        except Exception as e:
            logger.warning(f"calamine failed: {e} — trying pandas fallback")

        # ── Strategy 2: pandas fallback ────────────────────────────────────
        try:
            if ext == ".xls":
                pandas_df = pd.read_excel(
                    file_path,
                    engine="xlrd",
                    dtype=str          # read everything as string → no encoding issues
                )
            else:
                pandas_df = pd.read_excel(
                    file_path,
                    engine="openpyxl",
                    dtype=str
                )

            # Clean: strip whitespace from column names, replace NaN with empty string
            pandas_df.columns = [str(c).strip() for c in pandas_df.columns]
            pandas_df = pandas_df.fillna("").astype(str)

            # Drop blank/merged-header columns (pandas names them "Unnamed: N")
            # before they ever reach the rest of the pipeline.
            keep_cols = [
                c for c in pandas_df.columns
                if not self._UNNAMED_COL_RE.match(c)
            ]
            dropped = [c for c in pandas_df.columns if c not in keep_cols]
            if dropped:
                logger.info(f"Dropping blank/unnamed columns: {dropped}")
            pandas_df = pandas_df[keep_cols]

            # Encode/decode every cell to remove problematic unicode chars
            for col in pandas_df.columns:
                pandas_df[col] = pandas_df[col].apply(
                    lambda x: x.encode("utf-8", errors="replace")
                                .decode("utf-8", errors="replace")
                    if isinstance(x, str) else x
                )

            df = pl.from_pandas(pandas_df)
            logger.info(f"Rows Loaded (pandas fallback): {df.height}")
            logger.info(f"Columns: {df.columns}")
            return self._sanitize_safe(df, file_path)

        except Exception as e:
            logger.error(f"All read strategies failed: {e}")
            raise RuntimeError(
                f"Cannot read Excel file '{file_path}': {e}"
            )

    def _drop_unnamed(self, df: pl.DataFrame) -> pl.DataFrame:
        """Drop columns whose header is blank or pandas/calamine-style 'Unnamed: N'."""
        keep = [
            c for c in df.columns
            if c.strip() != "" and not self._UNNAMED_COL_RE.match(c.strip())
        ]
        dropped = [c for c in df.columns if c not in keep]
        if dropped:
            logger.info(f"Dropping blank/unnamed columns: {dropped}")
        return df.select(keep)

    def _sanitize_safe(self, df: pl.DataFrame, file_path: str) -> pl.DataFrame:
        """
        Wraps _sanitize() so that any failure is logged with the
        offending file and re-raised with context, instead of
        propagating silently with no trace in the logs.
        """
        try:
            return self._sanitize(df)
        except Exception as e:
            logger.error(
                f"Sanitize step failed for '{file_path}': {e} "
                f"(columns at failure: {df.columns})"
            )
            raise RuntimeError(
                f"Failed to sanitize Excel data from '{file_path}': {e}"
            )

    def _sanitize(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Cast all columns to Utf8, strip whitespace,
        strip BOM characters, fill nulls with empty string.
        """
        return df.with_columns([
            pl.col(c)
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.strip_chars()
              .str.replace_all(r"\ufeff", "")   # strip BOM
            for c in df.columns
        ])