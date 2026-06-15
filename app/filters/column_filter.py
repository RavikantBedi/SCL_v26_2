import polars as pl
from app.core.logger import get_logger

logger = get_logger()


class ColumnFilter:
    """
    Renames raw Excel column headers to standardised names,
    then selects only the columns the pipeline needs.

    Matching is case-insensitive and strips surrounding whitespace
    so slight header variations in the source file are handled.
    """

    # All known aliases → canonical name
    COLUMN_MAPPING = {
        # IP address
        "ipadd":            "IPAdd",
        "ip address":       "IPAdd",
        "ipaddress":        "IPAdd",
        "ip":               "IPAdd",

        # MAC address
        "mac address":      "MAC Address",
        "mac addr":         "MAC Address",
        "macaddress":       "MAC Address",
        "mac":              "MAC Address",

        # Computer / host name
        "compname":         "CompName",
        "computer name":    "CompName",
        "computername":     "CompName",
        "hostname":         "CompName",

        # User
        "user name":        "User Name",
        "username":         "User Name",
        "user":             "User Name",

        # Model
        "system model":     "System Model",
        "systemmodel":      "System Model",
        "model":            "System Model",

        # Last agent communication
        "last agentcom":    "Last AgentCom",
        "last agent comm":  "Last AgentCom",
        "last agent com":   "Last AgentCom",
        "lastagentcom":     "Last AgentCom",
        "last seen":        "Last AgentCom",
    }

    REQUIRED_COLUMNS = [
        "IPAdd",
        "MAC Address",
        "CompName",
        "User Name",
        "System Model",
        "Last AgentCom",
    ]

    def extract(self, df: pl.DataFrame) -> pl.DataFrame:

        # Build rename map using lower-stripped keys for case-insensitive match
        rename_map = {}
        for col in df.columns:
            key = col.strip().lower()
            if key in self.COLUMN_MAPPING:
                rename_map[col] = self.COLUMN_MAPPING[key]

        if rename_map:
            logger.info(f"Renaming columns: {rename_map}")
            df = df.rename(rename_map)
        else:
            logger.warning(
                f"No columns matched the known mapping! "
                f"Excel columns found: {df.columns}"
            )

        # Keep only the columns that are present
        available = [c for c in self.REQUIRED_COLUMNS if c in df.columns]

        if not available:
            raise ValueError(
                f"None of the required columns found in Excel file. "
                f"Columns present: {df.columns}"
            )

        logger.info(f"Extracted columns: {available}")
        return df.select(available)