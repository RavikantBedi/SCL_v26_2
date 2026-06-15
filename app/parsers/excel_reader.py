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

    def read(self, file_path: str) -> pl.DataFrame:

        logger.info(f"Reading Excel File: {file_path}")

        ext = Path(file_path).suffix.lower()

        # ── Strategy 1: polars + calamine ─────────────────────────────────
        try:
            df = pl.read_excel(file_path, engine="calamine")
            logger.info(f"Rows Loaded (calamine): {df.height}")
            logger.info(f"Columns: {df.columns}")
            return self._sanitize(df)

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
            return self._sanitize(df)

        except Exception as e:
            logger.error(f"All read strategies failed: {e}")
            raise RuntimeError(
                f"Cannot read Excel file '{file_path}': {e}"
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