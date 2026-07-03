from datetime import datetime, timedelta
import polars as pl
from app.core.logger import get_logger

logger = get_logger()


class DateFilter:
    """
    Filters the inventory DataFrame to only keep rows where
    the last-seen date is within the last N months.

    Supports multiple date formats and gracefully skips filtering
    if the date column is absent or unparseable.
    """

    DATE_COLUMN_CANDIDATES = [
        "Last AgentCom",
        "Last Agent Comm",
        "LastAgentCom",
        "Last Agent Com",
        "Last Seen",
    ]

    # Ordered list of strptime format strings to try.
    # IMPORTANT: %I/%p (12-hour + AM/PM) formats MUST come before any
    # %H-only formats. strptime with strict=False will silently produce
    # nulls for non-matching rows rather than raising, so a format that
    # matches the *date* portion but not the *time* portion (12-hour vs
    # 24-hour) can still report a small number of "valid" parses by luck
    # and get locked in — leaving the rest of the column unparsed and
    # falling through to "no date filter applied" for the whole file.
    #
    # Source format actually seen in this app's data: "1/10/25 9:07:18 AM"
    # i.e. M/D/YY h:mm:ss AM/PM (month-first, 2-digit year, no leading
    # zeros, 12-hour clock). The "IST"/"UTC" suffix is stripped before
    # parsing (see _clean_dates below), so it is NOT part of these formats.
    DATE_FORMATS = [
        "%m/%d/%y %I:%M:%S %p",   # 1/10/25 9:07:18 AM   ← actual data format
        "%m/%d/%Y %I:%M:%S %p",   # 1/10/2025 9:07:18 AM
        "%d/%m/%y %I:%M:%S %p",   # 10/1/25 9:07:18 AM  (day-first variant)
        "%d/%m/%Y %I:%M:%S %p",   # 10/1/2025 9:07:18 AM
        "%m/%d/%y %H:%M:%S",      # 1/10/25 09:07:18  (24-hour, month-first)
        "%d/%m/%y %H:%M:%S",      # 10/1/25 09:07:18  (24-hour, day-first)
        "%d/%m/%Y %H:%M:%S",      # 10/1/2025 09:07:18
        "%Y-%m-%d %H:%M:%S",      # 2026-01-27 09:21:37
        "%Y-%m-%dT%H:%M:%S",      # ISO 8601
        "%d-%m-%Y %H:%M:%S",      # 27-01-2026 09:21:37
        "%m/%d/%Y %H:%M:%S",      # 01/27/2026 09:21:37
        "%d/%m/%y",               # 27/01/26
        "%d/%m/%Y",               # 27/01/2026
        "%Y-%m-%d",               # 2026-01-27
    ]

    @staticmethod
    def _clean_dates(column: pl.Series) -> pl.Series:
        """
        Strip timezone suffixes and normalize whitespace so the
        strptime formats above only need to deal with the actual
        date/time portion of the string.
        """
        return (
            column
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.strip_chars()
              .str.replace(" IST", "", literal=True)
              .str.replace(" UTC", "", literal=True)
              .str.replace(" GMT", "", literal=True)
              .str.replace_all(r"\s+", " ")   # collapse any run of whitespace to one space
        )

    def filter_by_months(
        self,
        df: pl.DataFrame,
        months: int = 1,
        keep_nulls: bool = False
    ) -> pl.DataFrame:
        """Backward compatibility for existing callers."""
        filtered, _ = self.split_by_months(df, months, keep_nulls)
        return filtered

    def split_by_months(
        self,
        df: pl.DataFrame,
        months: int = 1,
        keep_nulls: bool = False
    ) -> tuple[pl.DataFrame, pl.DataFrame]:

        # ── find the date column ──────────────────────────────────────────
        date_column = None
        for col in self.DATE_COLUMN_CANDIDATES:
            if col in df.columns:
                date_column = col
                break

        if date_column is None:
            logger.warning(
                "Date column not found in Excel. "
                f"Columns present: {df.columns}. "
                "Skipping date filter — returning all rows."
            )
            return df, df.clear()

        cutoff = datetime.now() - timedelta(days=months * 30)
        logger.info(
            f"Date filter → column='{date_column}', "
            f"months={months}, cutoff={cutoff.strftime('%Y-%m-%d')}, keep_nulls={keep_nulls}"
        )

        # ── clean the raw string ──────────────────────────────────────────
        cleaned = self._clean_dates(df.get_column(date_column))

        # ── try each format, keep whichever parses the MOST rows ─────────
        # (not just the first format that parses >0 rows — a format that
        # matches the date but not the AM/PM time portion can still get
        # a few accidental matches and would otherwise be locked in,
        # silently leaving most rows unparsed.)
        best_parsed = None
        best_count = 0
        best_fmt = None
        for fmt in self.DATE_FORMATS:
            try:
                attempt = cleaned.str.strptime(pl.Datetime, fmt, strict=False)
                valid_count = attempt.drop_nulls().len()
                if valid_count > best_count:
                    best_parsed = attempt
                    best_count = valid_count
                    best_fmt = fmt
            except Exception:
                continue

        if best_parsed is None or best_count == 0:
            sample = cleaned.drop_nulls().head(5).to_list()
            logger.warning(
                "Could not parse any date values. "
                f"Sample raw values seen: {sample}. "
                "Skipping date filter — returning all rows."
            )
            return df, df.clear()

        parsed = best_parsed
        logger.info(
            f"Date format '{best_fmt}' matched {best_count}/{df.height} rows"
        )

        unparsed_count = df.height - best_count
        if unparsed_count > 0:
            unparsed_sample = (
                df.with_columns(parsed.alias("_parsed_tmp"))
                  .filter(pl.col("_parsed_tmp").is_null())
                  .get_column(date_column)
                  .head(5)
                  .to_list()
            )
            logger.warning(
                f"{unparsed_count} row(s) did not match format '{best_fmt}' "
                f"and will be treated as null dates. Sample unparsed values: {unparsed_sample}"
            )

        # ── apply filter ──────────────────────────────────────────────────
        df = df.with_columns(parsed.alias(date_column))

        before = df.height

        if keep_nulls:
            filtered = df.filter(
                pl.col(date_column).is_null() | (pl.col(date_column) >= cutoff)
            )
            excluded = df.filter(
                pl.col(date_column).is_not_null() & (pl.col(date_column) < cutoff)
            )
        else:
            filtered = df.filter(
                pl.col(date_column).is_not_null() & (pl.col(date_column) >= cutoff)
            )
            excluded = df.filter(
                pl.col(date_column).is_null() | (pl.col(date_column) < cutoff)
            )

        after = filtered.height

        logger.info(
            f"Date filter applied: {before} rows → {after} rows "
            f"(removed {before - after} older than {months} months)"
        )

        # If filter wiped everything, return original (safety net)
        if after == 0:
            logger.warning(
                "Date filter removed ALL rows — "
                "returning unfiltered data as safety fallback."
            )
            return df, df.clear()

        return filtered, excluded