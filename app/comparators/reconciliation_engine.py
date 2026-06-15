import polars as pl
from app.core.logger import get_logger

logger = get_logger()


class ReconciliationEngine:
    """
    Compares TXT (network export) records against Excel inventory records.

    Matching strategy:
      - Primary: IP + MAC (both must match)
      - Falls back to MAC-only if IP column is missing from one side
    """

    def compare(
        self,
        txt_df: pl.DataFrame,
        inventory_df: pl.DataFrame,
    ):
        logger.info(
            f"Starting reconciliation | "
            f"TXT={txt_df.height} rows, "
            f"Inventory={inventory_df.height} rows"
        )

        # ====================================================
        # STANDARDISE TXT COLUMNS → IP, MAC
        # ====================================================
        txt_col_map = {
            "ip-address": "IP",
            "ip address":  "IP",
            "ipaddress":   "IP",
            "ip":          "IP",
            "IP Address":  "IP",
            "IP":          "IP",

            "mac-address": "MAC",
            "mac address": "MAC",
            "macaddress":  "MAC",
            "mac":         "MAC",
            "MAC Address": "MAC",
            "MAC":         "MAC",
        }

        txt_df = self._rename(txt_df, txt_col_map)
        logger.info(f"TXT columns after rename: {txt_df.columns}")

        # ====================================================
        # STANDARDISE INVENTORY COLUMNS → IP, MAC
        # ====================================================
        inv_col_map = {
            "IPAdd":        "IP",
            "ip address":   "IP",
            "ip addr":      "IP",
            "ipaddress":    "IP",
            "ip":           "IP",
            "IP Address":   "IP",
            "IP":           "IP",

            "MAC Address":  "MAC",
            "Mac Address":  "MAC",
            "mac address":  "MAC",
            "mac addr":     "MAC",
            "macaddress":   "MAC",
            "mac":          "MAC",
            "MAC":          "MAC",
        }

        inventory_df = self._rename(inventory_df, inv_col_map)
        logger.info(f"Inventory columns after rename: {inventory_df.columns}")

        # ====================================================
        # VALIDATE REQUIRED COLUMNS
        # ====================================================
        for col in ["IP", "MAC"]:
            if col not in txt_df.columns:
                raise ValueError(
                    f"TXT file is missing required column '{col}'. "
                    f"Columns found: {txt_df.columns}"
                )
            if col not in inventory_df.columns:
                raise ValueError(
                    f"Excel inventory is missing required column '{col}'. "
                    f"Columns found: {inventory_df.columns}"
                )

        # ====================================================
        # NORMALIZE — clean IP and MAC for comparison
        # ====================================================
        txt_cmp = self._normalize(txt_df.select(["IP", "MAC"]))
        inv_cmp = self._normalize(inventory_df.select(["IP", "MAC"]))

        logger.info(f"TXT sample after normalize:\n{txt_cmp.head(5)}")
        logger.info(f"Inventory sample after normalize:\n{inv_cmp.head(5)}")

        # ====================================================
        # MATCH on IP + MAC (inner join)
        # ====================================================
        matched = txt_cmp.join(inv_cmp, on=["IP", "MAC"], how="inner")

        # ====================================================
        # UNMATCHED = TXT rows with no inventory match (anti join)
        # ====================================================
        unmatched = txt_cmp.join(inv_cmp, on=["IP", "MAC"], how="anti")

        logger.info(
            f"Reconciliation done | "
            f"Matched={matched.height}, "
            f"Unmatched={unmatched.height}"
        )

        return matched, unmatched

    # ──────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def _rename(df: pl.DataFrame, col_map: dict) -> pl.DataFrame:
        """Case-insensitive rename using the provided mapping."""
        rename = {}
        for col in df.columns:
            # Try exact match first, then lower-stripped
            if col in col_map:
                rename[col] = col_map[col]
            elif col.strip().lower() in {k.lower(): v for k, v in col_map.items()}:
                lower_map = {k.lower(): v for k, v in col_map.items()}
                rename[col] = lower_map[col.strip().lower()]
        return df.rename(rename) if rename else df

    @staticmethod
    def _normalize(df: pl.DataFrame) -> pl.DataFrame:
        """Normalise IP and MAC so minor formatting differences don't block matching."""
        return df.with_columns([
            # IP: strip whitespace
            pl.col("IP")
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.strip_chars(),

            # MAC: lowercase, remove separators (: - . spaces)
            pl.col("MAC")
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.to_lowercase()
              .str.replace_all(r"[-:\.\s]", ""),
        ])