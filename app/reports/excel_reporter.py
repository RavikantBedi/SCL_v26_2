# from pathlib import Path
# from datetime import datetime

# import polars as pl

# from openpyxl import load_workbook
# from openpyxl.styles import (
#     Font,
#     PatternFill,
#     Border,
#     Side,
#     Alignment
# )


# class ExcelReporter:

#     HEADER_FILL = PatternFill(
#         fill_type="solid",
#         fgColor="1F4E78"
#     )

#     HEADER_FONT = Font(
#         color="FFFFFF",
#         bold=True
#     )

#     THIN_BORDER = Border(
#         left=Side(style="thin"),
#         right=Side(style="thin"),
#         top=Side(style="thin"),
#         bottom=Side(style="thin")
#     )

#     CENTER_ALIGN = Alignment(
#         horizontal="center",
#         vertical="center"
#     )

#     # =====================================
#     # DIRECTORY HANDLING
#     # =====================================

#     def _ensure_dir(self, path: str):
#         Path(path).parent.mkdir(
#             parents=True,
#             exist_ok=True
#         )

#     # =====================================
#     # EXCEL FORMATTING
#     # =====================================

#     def _format_excel(self, file_path: str, sheet_name: str):

#         wb = load_workbook(file_path)
#         ws = wb.active
#         ws.title = sheet_name

#         # Header formatting
#         for cell in ws[1]:
#             cell.fill = self.HEADER_FILL
#             cell.font = self.HEADER_FONT
#             cell.border = self.THIN_BORDER
#             cell.alignment = self.CENTER_ALIGN

#         # Data formatting
#         for row in ws.iter_rows(min_row=2):
#             for cell in row:
#                 cell.border = self.THIN_BORDER
#                 cell.alignment = self.CENTER_ALIGN

#         # Auto column width
#         for column in ws.columns:
#             max_length = 0
#             column_letter = column[0].column_letter

#             for cell in column:
#                 if cell.value is not None:
#                     max_length = max(max_length, len(str(cell.value)))

#             ws.column_dimensions[column_letter].width = max_length + 5

#         # Freeze header
#         ws.freeze_panes = "A2"

#         wb.save(file_path)

#     # =====================================
#     # SAVE EXCEL FILE
#     # =====================================

#     def save_excel(self, df: pl.DataFrame, file_path: str, sheet_name: str):

#         self._ensure_dir(file_path)

#         # IMPORTANT: avoid schema issues
#         df = df.with_columns(pl.all().cast(pl.Utf8))

#         df.write_excel(file_path)

#         self._format_excel(file_path, sheet_name)

#     # =====================================
#     # USER NAME MAPPING
#     # =====================================

#     def _attach_user_name(
#         self,
#         df: pl.DataFrame,
#         user_mapping: pl.DataFrame | None
#     ) -> pl.DataFrame:
#         """
#         Left-joins 'Name' onto df using IP as the key.
#         If user_mapping is None, or the IP has no match,
#         'User Name' is filled with 'Unknown'.

#         Expects:
#           - df has a column called 'IP' (normalized: stripped)
#           - user_mapping has columns 'IP Address' and 'Name'
#             (raw, as read from the 3rd Excel file)
#         """

#         if user_mapping is None or user_mapping.height == 0:
#             return df.with_columns(
#                 pl.lit("Unknown").alias("User Name")
#             )

#         mapping_cmp = user_mapping.select([
#             pl.col("IP Address")
#               .cast(pl.Utf8, strict=False)
#               .fill_null("")
#               .str.strip_chars()
#               .alias("IP"),

#             pl.col("Name")
#               .cast(pl.Utf8, strict=False)
#               .fill_null("Unknown")
#               .str.strip_chars()
#               .alias("User Name"),
#         ])

#         # Drop duplicate IPs in mapping file (keep first occurrence)
#         mapping_cmp = mapping_cmp.unique(subset=["IP"], keep="first")

#         # Drop existing 'User Name' if it exists so we don't get duplicates
#         if "User Name" in df.columns:
#             df = df.drop("User Name")

#         # Left join — preserves all rows of df, adds User Name where found
#         joined = df.join(mapping_cmp, on="IP", how="left")

#         # Fill any unmatched IPs with "Unknown"
#         joined = joined.with_columns(
#             pl.col("User Name").fill_null("Unknown")
#         )

#         # Fallback: if user name is "Unknown" and CompName exists, use CompName instead
#         if "CompName" in joined.columns:
#             joined = joined.with_columns(
#                 pl.when(pl.col("User Name") == "Unknown")
#                 .then(pl.col("CompName").fill_null("Unknown"))
#                 .otherwise(pl.col("User Name"))
#                 .alias("User Name")
#             )

#         return joined

#     # =====================================
#     # REPORT GENERATION
#     # =====================================

#     def generate_reports(
#         self,
#         matched: pl.DataFrame,
#         unmatched: pl.DataFrame,
#         txt_unmatched: pl.DataFrame,
#         inv_unmatched: pl.DataFrame,
#         txt_count: int,
#         user_mapping: pl.DataFrame | None = None,
#         output_dir: str = "output/reports"      # ← NEW: defaults to old behavior
#     ):
#         """
#         output_dir lets the caller (main.py) direct reports into a
#         per-session folder, e.g. output/reports/<session_id>/, so that
#         concurrent users never share or overwrite each other's files.

#         If output_dir is not provided, falls back to the original
#         'output/reports' location for backward compatibility.
#         """

#         base_path = output_dir.rstrip("/") + "/"
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

#         matched_file = f"{base_path}matched_{timestamp}.xlsx"
#         unmatched_file = f"{base_path}unmatched_combined_{timestamp}.xlsx"
#         txt_unmatched_file = f"{base_path}data_unmatched_{timestamp}.xlsx"
#         inv_unmatched_file = f"{base_path}data_match_{timestamp}.xlsx"
#         summary_file = f"{base_path}summary_{timestamp}.xlsx"

#         # ---------------- ATTACH USER NAME ----------------
#         matched = self._attach_user_name(matched, user_mapping)
#         unmatched = self._attach_user_name(unmatched, user_mapping)
#         txt_unmatched = self._attach_user_name(txt_unmatched, user_mapping)
#         inv_unmatched = self._attach_user_name(inv_unmatched, user_mapping)

#         # ---------------- ALIGN COLUMNS ----------------
#         if "System Model" in matched.columns:
#             matched = matched.drop("System Model")
            
#         if "CompName" in matched.columns:
#             matched = matched.drop("CompName")

#         target_cols = matched.columns
#         for col in target_cols:
#             if col not in unmatched.columns:
#                 unmatched = unmatched.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))
#             if col not in txt_unmatched.columns:
#                 txt_unmatched = txt_unmatched.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))
#             if col not in inv_unmatched.columns:
#                 inv_unmatched = inv_unmatched.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))
        
#         unmatched = unmatched.select(target_cols)
#         txt_unmatched = txt_unmatched.select(target_cols)
#         inv_unmatched = inv_unmatched.select(target_cols)

#         # ---------------- MATCHED ----------------
#         self.save_excel(matched, matched_file, "Matched Assets")

#         # ---------------- UNMATCHED ----------------
#         self.save_excel(unmatched, unmatched_file, "Unmatched Combined")
#         self.save_excel(inv_unmatched, inv_unmatched_file, "Unmatched Category A")
#         self.save_excel(txt_unmatched, txt_unmatched_file, "Unmatched Category B")

#         # ---------------- SUMMARY ----------------
#         match_percentage = (
#             round((matched.height / txt_count) * 100, 2)
#             if txt_count > 0
#             else 0
#         )

#         summary = pl.DataFrame({
#             "Metric": [
#                 "Generated On",
#                 "Total TXT Records",
#                 "Matched Records",
#                 "Unmatched Inventory Records",
#                 "Unmatched Network Records",
#                 "Match Percentage"
#             ],
#             "Value": [
#                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 str(txt_count),
#                 str(matched.height),
#                 str(inv_unmatched.height),
#                 str(txt_unmatched.height),
#                 f"{match_percentage}%"
#             ]
#         })

#         self.save_excel(summary, summary_file, "Summary")

#         print("\nReports Generated:")
#         print(matched_file)
#         print(inv_unmatched_file)
#         print(txt_unmatched_file)
#         print(summary_file)





from pathlib import Path
from datetime import datetime

import polars as pl

from app.core.logger import get_logger

logger = get_logger()

from openpyxl import load_workbook
from openpyxl.styles import (
    Font,
    PatternFill,
    Border,
    Side,
    Alignment
)


class ExcelReporter:

    HEADER_FILL = PatternFill(
        fill_type="solid",
        fgColor="1F4E78"
    )

    HEADER_FONT = Font(
        color="FFFFFF",
        bold=True
    )

    THIN_BORDER = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    CENTER_ALIGN = Alignment(
        horizontal="center",
        vertical="center"
    )

    # =====================================
    # DIRECTORY HANDLING
    # =====================================

    def _ensure_dir(self, path: str):
        Path(path).parent.mkdir(
            parents=True,
            exist_ok=True
        )

    # =====================================
    # EXCEL FORMATTING
    # =====================================

    def _format_excel(self, file_path: str, sheet_name: str):

        wb = load_workbook(file_path)
        ws = wb.active
        ws.title = sheet_name

        # Header formatting
        for cell in ws[1]:
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.border = self.THIN_BORDER
            cell.alignment = self.CENTER_ALIGN

        # Data formatting
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.border = self.THIN_BORDER
                cell.alignment = self.CENTER_ALIGN

        # Auto column width
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                if cell.value is not None:
                    max_length = max(max_length, len(str(cell.value)))

            ws.column_dimensions[column_letter].width = max_length + 5

        # Freeze header
        ws.freeze_panes = "A2"

        wb.save(file_path)

    # =====================================
    # SAVE EXCEL FILE
    # =====================================

    def save_excel(self, df: pl.DataFrame, file_path: str, sheet_name: str):

        self._ensure_dir(file_path)

        # IMPORTANT: avoid schema issues
        df = df.with_columns(pl.all().cast(pl.Utf8))

        df.write_excel(file_path)

        self._format_excel(file_path, sheet_name)

    # =====================================
    # USER NAME MAPPING
    # =====================================

    def _attach_user_name(
        self,
        df: pl.DataFrame,
        user_mapping: pl.DataFrame | None
    ) -> pl.DataFrame:
        """
        Left-joins 'Name' onto df using IP as the key.
        If user_mapping is None, or the IP has no match,
        'User Name' is filled with 'Unknown'.

        Expects:
          - df has a column called 'IP' (normalized: stripped)
          - user_mapping has columns 'IP Address' and 'Name'
            (raw, as read from the 3rd Excel file)
        """

        if user_mapping is None or user_mapping.height == 0:
            return df.with_columns(
                pl.lit("Unknown").alias("User Name")
            )

        mapping_cmp = user_mapping.select([
            pl.col("IP Address")
              .cast(pl.Utf8, strict=False)
              .fill_null("")
              .str.strip_chars()
              .alias("IP"),

            pl.col("Name")
              .cast(pl.Utf8, strict=False)
              .fill_null("Unknown")
              .str.strip_chars()
              .alias("User Name"),
        ])

        # Drop duplicate IPs in mapping file (keep first occurrence)
        mapping_cmp = mapping_cmp.unique(subset=["IP"], keep="first")

        # Drop existing 'User Name' if it exists so we don't get duplicates
        if "User Name" in df.columns:
            df = df.drop("User Name")

        # Left join — preserves all rows of df, adds User Name where found
        joined = df.join(mapping_cmp, on="IP", how="left")

        # Fill any unmatched IPs with "Unknown"
        joined = joined.with_columns(
            pl.col("User Name").fill_null("Unknown")
        )

        # Fallback: if User Name is blank/null/whitespace-only, use CompName instead.
        # (Previously this only checked for the literal string "Unknown", so a
        # genuinely blank or whitespace-only name coming from the mapping file
        # slipped through without ever falling back to CompName.)
        if "CompName" in joined.columns:
            is_blank_name = (
                pl.col("User Name").is_null()
                | (pl.col("User Name").str.strip_chars() == "")
                | (pl.col("User Name") == "Unknown")
            )
            joined = joined.with_columns(
                pl.when(is_blank_name)
                .then(
                    pl.col("CompName")
                      .cast(pl.Utf8, strict=False)
                      .fill_null("")
                      .str.strip_chars()
                )
                .otherwise(pl.col("User Name"))
                .alias("User Name")
            )
            # If CompName was also blank/null, fall back to "Unknown" as the final default
            joined = joined.with_columns(
                pl.when(pl.col("User Name").str.strip_chars() == "")
                .then(pl.lit("Unknown"))
                .otherwise(pl.col("User Name"))
                .alias("User Name")
            )

        return joined

    # =====================================
    # REPORT GENERATION
    # =====================================

    def generate_reports(
        self,
        matched: pl.DataFrame,
        unmatched: pl.DataFrame,
        txt_unmatched: pl.DataFrame,
        inv_unmatched: pl.DataFrame,
        txt_count: int,
        user_mapping: pl.DataFrame | None = None,
        output_dir: str = "output/reports"      # ← NEW: defaults to old behavior
    ):
        """
        output_dir lets the caller (main.py) direct reports into a
        per-session folder, e.g. output/reports/<session_id>/, so that
        concurrent users never share or overwrite each other's files.

        If output_dir is not provided, falls back to the original
        'output/reports' location for backward compatibility.
        """

        base_path = output_dir.rstrip("/") + "/"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        matched_file = f"{base_path}matched_{timestamp}.xlsx"
        unmatched_file = f"{base_path}unmatched_combined_{timestamp}.xlsx"
        txt_unmatched_file = f"{base_path}data_unmatched_{timestamp}.xlsx"
        inv_unmatched_file = f"{base_path}data_match_{timestamp}.xlsx"
        summary_file = f"{base_path}summary_{timestamp}.xlsx"

        # ---------------- DIAGNOSTIC COUNTS (before processing) ----------------
        logger.info(
            f"generate_reports received | "
            f"matched={matched.height}, unmatched={unmatched.height}, "
            f"category_b(txt_unmatched)={txt_unmatched.height}, "
            f"category_a(inv_unmatched)={inv_unmatched.height}"
        )

        # ---------------- ATTACH USER NAME ----------------
        matched = self._attach_user_name(matched, user_mapping)
        unmatched = self._attach_user_name(unmatched, user_mapping)
        txt_unmatched = self._attach_user_name(txt_unmatched, user_mapping)
        inv_unmatched = self._attach_user_name(inv_unmatched, user_mapping)

        # ---------------- ALIGN COLUMNS ----------------
        # matched: drop internal-only columns before saving
        if "System Model" in matched.columns:
            matched = matched.drop("System Model")

        if "CompName" in matched.columns:
            matched = matched.drop("CompName")

        # ── unmatched_combined: union of all cols across the four DataFrames ──
        # Category A (inv_unmatched) and Category B (txt_unmatched) come from
        # the combined unmatched pool and may have different column sets from
        # each other and from matched. We deliberately do NOT force them onto
        # matched's schema — each file is saved with its own natural columns so
        # no data is silently dropped.

        def _drop_internal(df: pl.DataFrame) -> pl.DataFrame:
            """Remove pipeline-only columns that should never appear in output."""
            for col in ("System Model", "CompName"):
                if col in df.columns:
                    df = df.drop(col)
            return df

        inv_unmatched = _drop_internal(inv_unmatched)
        txt_unmatched = _drop_internal(txt_unmatched)
        unmatched     = _drop_internal(unmatched)

        # For the combined file: build a stable column order (union of all cols,
        # matched schema first, then any extra cols only in the unmatched pool).
        target_cols = matched.columns
        extra_cols = [c for c in unmatched.columns if c not in target_cols]
        combined_cols = target_cols + extra_cols

        for col in combined_cols:
            if col not in unmatched.columns:
                unmatched = unmatched.with_columns(pl.lit(None).cast(pl.Utf8).alias(col))

        unmatched = unmatched.select(combined_cols)

        # ---------------- MATCHED ----------------
        self.save_excel(matched, matched_file, "Matched Assets")

        # ---------------- UNMATCHED ----------------
        self.save_excel(unmatched, unmatched_file, "Unmatched Combined")
        self.save_excel(inv_unmatched, inv_unmatched_file, "Unmatched Category A")
        
        if "Last AgentCom" in txt_unmatched.columns:
            txt_unmatched = txt_unmatched.drop("Last AgentCom")
            
        self.save_excel(txt_unmatched, txt_unmatched_file, "Unmatched Category B")

        # ---------------- SUMMARY ----------------
        match_percentage = (
            round((matched.height / txt_count) * 100, 2)
            if txt_count > 0
            else 0
        )

        summary = pl.DataFrame({
            "Metric": [
                "Generated On",
                "Total TXT Records",
                "Matched Records",
                "Unmatched Inventory Records",
                "Unmatched Network Records",
                "Match Percentage"
            ],
            "Value": [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                str(txt_count),
                str(matched.height),
                str(inv_unmatched.height),
                str(txt_unmatched.height),
                f"{match_percentage}%"
            ]
        })

        self.save_excel(summary, summary_file, "Summary")

        print("\nReports Generated:")
        print(matched_file)
        print(inv_unmatched_file)
        print(txt_unmatched_file)
        print(summary_file)
