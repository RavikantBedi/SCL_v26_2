import re
import polars as pl
from app.core.logger import get_logger

logger = get_logger()


class ColumnFilter:
    """
    Renames raw Excel column headers to standardised names,
    then selects only the columns the pipeline needs.

    Matching is case-insensitive and ignores spaces, hyphens,
    underscores, and dots in the header, so variants like
    "IP-Address", "ip_address", "IP. Address" or "IP  Address"
    all resolve to the same canonical column without needing
    a new dictionary entry for every punctuation style.
    """

    # All known aliases → canonical name.
    # Keys here MUST already be in normalized form (lowercase,
    # no spaces/hyphens/underscores/dots) — see _normalize().
    COLUMN_MAPPING = {
        # IP address
        "ipadd":            "IPAdd",
        "ipaddress":        "IPAdd",
        "ip":               "IPAdd",

        # MAC address
        "macaddress":       "MAC Address",
        "macaddr":          "MAC Address",
        "mac":              "MAC Address",

        # Computer / host name
        "compname":         "CompName",
        "computername":     "CompName",
        "hostname":         "CompName",

        # User
        "username":         "User Name",
        "user":             "User Name",

        # Model
        "systemmodel":      "System Model",
        "model":            "System Model",

        # Last agent communication
        "lastagentcom":     "Last AgentCom",
        "lastagentcomm":    "Last AgentCom",
        "lastagentcommunication": "Last AgentCom",
        "lastseen":         "Last AgentCom",
    }

    REQUIRED_COLUMNS = [
        "IPAdd",
        "MAC Address",
        "CompName",
        "User Name",
        "System Model",
        "Last AgentCom",
    ]

    # Aliases specific to the User Mapping file (IP -> human-readable Name).
    # Kept separate from COLUMN_MAPPING above because the mapping file's
    # canonical names ("IP Address", "Name") differ from the inventory
    # file's canonical names ("IPAdd", "User Name").
    USER_MAPPING_COLUMN_MAPPING = {
        "ipadd":      "IP Address",
        "ipaddress":  "IP Address",
        "ip":         "IP Address",

        "name":       "Name",
        "username":   "Name",
        "usersname":  "Name",
        "user":       "Name",
    }

    USER_MAPPING_REQUIRED_COLUMNS = ["IP Address", "Name"]

    @staticmethod
    def _normalize(header: str) -> str:
        """
        Collapse a raw header into a comparable key:
        lowercase, strip whitespace, remove spaces/hyphens/
        underscores/dots/periods so punctuation/spacing style
        never causes a missed match.
        """
        key = header.strip().lower()
        key = re.sub(r"[\s\-_./]+", "", key)
        return key

    def extract(self, df: pl.DataFrame) -> pl.DataFrame:

        # Build rename map using normalized keys for matching
        rename_map = {}
        for col in df.columns:
            key = self._normalize(col)
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

    def extract_user_mapping(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Same normalize-and-rename approach as extract(), but for the
        User Mapping file, whose canonical columns are "IP Address"
        and "Name" rather than the inventory file's column set.

        Raises ValueError (caught by the caller and converted to an
        HTTP 422) if either required column is still missing after
        normalization — e.g. if the file truly has no IP or Name-like
        column at all.
        """
        rename_map = {}
        for col in df.columns:
            key = self._normalize(col)
            if key in self.USER_MAPPING_COLUMN_MAPPING:
                rename_map[col] = self.USER_MAPPING_COLUMN_MAPPING[key]

        if rename_map:
            logger.info(f"Renaming user mapping columns: {rename_map}")
            df = df.rename(rename_map)
        else:
            logger.warning(
                f"No columns matched the user mapping aliases! "
                f"Excel columns found: {df.columns}"
            )

        missing = [c for c in self.USER_MAPPING_REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ValueError(
                f"User mapping Excel is missing required column(s): "
                f"{', '.join(missing)}. Columns found: {df.columns}"
            )

        logger.info(f"Extracted user mapping columns: {self.USER_MAPPING_REQUIRED_COLUMNS}")
        return df.select(self.USER_MAPPING_REQUIRED_COLUMNS)