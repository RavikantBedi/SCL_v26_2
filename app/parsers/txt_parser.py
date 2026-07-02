"""Text file parser."""

import re
import polars as pl

from app.core.logger import get_logger

logger = get_logger()


class TxtParser:

    def __init__(self):

        self.ip_pattern = (
            r'ip-address\s+([\d\.]+)'
        )

        self.mac_pattern = (
            r'mac-address\s+([0-9A-Fa-f:\-\.]+)'
        )

    def parse(
        self,
        file_path: str
    ) -> pl.DataFrame:

        records = []

        logger.info(
            f"Reading TXT File : {file_path}"
        )

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:

            for line_no, line in enumerate(
                file,
                start=1
            ):

                ip_match = re.search(
                    self.ip_pattern,
                    line,
                    re.IGNORECASE
                )

                mac_match = re.search(
                    self.mac_pattern,
                    line,
                    re.IGNORECASE
                )

                if ip_match:

                    ip = ip_match.group(1)

                    mac = ""

                    if mac_match:

                        mac = (
                            mac_match
                            .group(1)
                            .lower()
                            .replace("-", "")
                            .replace(":", "")
                            .replace(".", "")
                            .replace(" ", "")
                        )

                    records.append({

                        "IP Address": ip,

                        "MAC Address": mac

                    })

        if not records:
            df = pl.DataFrame({"IP Address": [], "MAC Address": []})
        else:
            df = pl.DataFrame(records)

        logger.info(
            f"Parsed {len(records)} records"
        )

        logger.info(f"TXT PARSED: {df.height} rows | columns: {df.columns}")

        return df