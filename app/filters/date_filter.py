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

    # Ordered list of strptime format strings to try
    DATE_FORMATS = [
        "%d/%m/%y %H:%M:%S",   # 27/01/26 09:21:37
        "%d/%m/%Y %H:%M:%S",   # 27/01/2026 09:21:37
        "%Y-%m-%d %H:%M:%S",   # 2026-01-27 09:21:37
        "%Y-%m-%dT%H:%M:%S",   # ISO 8601
        "%d-%m-%Y %H:%M:%S",   # 27-01-2026 09:21:37
        "%m/%d/%Y %H:%M:%S",   # 01/27/2026 09:21:37
        "%d/%m/%y",            # 27/01/26
        "%d/%m/%Y",            # 27/01/2026
        "%Y-%m-%d",            # 2026-01-27
    ]

    def filter_by_months(
        self,
        df: pl.DataFrame,
        months: int = 6
    ) -> pl.DataFrame:

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
            return df

        cutoff = datetime.now() - timedelta(days=months * 30)
        logger.info(
            f"Date filter → column='{date_column}', "
            f"months={months}, cutoff={cutoff.strftime('%Y-%m-%d')}"
        )

        # ── clean the raw string ──────────────────────────────────────────
        cleaned = (
            df.get_column(date_column)
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.strip_chars()
              .str.replace(" IST", "", literal=True)
              .str.replace(" UTC", "", literal=True)
              .str.replace("  ", " ", literal=True)
        )

        # ── try each format until one works ──────────────────────────────
        parsed = None
        for fmt in self.DATE_FORMATS:
            try:
                attempt = cleaned.str.strptime(
                    pl.Datetime, fmt, strict=False
                )
                # count how many non-null values we got
                valid_count = attempt.drop_nulls().len()
                if valid_count > 0:
                    parsed = attempt
                    logger.info(
                        f"Date format '{fmt}' matched "
                        f"{valid_count}/{df.height} rows"
                    )
                    break
            except Exception:
                continue

        if parsed is None:
            logger.warning(
                "Could not parse any date values. "
                "Skipping date filter — returning all rows."
            )
            return df

        # ── apply filter ──────────────────────────────────────────────────
        df = df.with_columns(parsed.alias(date_column))

        before = df.height
        filtered = df.filter(
            pl.col(date_column).is_not_null()
            & (pl.col(date_column) >= cutoff)
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
            return df

        return filtered