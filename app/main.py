import asyncio
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.parsers.txt_parser import TxtParser
from app.parsers.excel_reader import ExcelReader

from app.filters.column_filter import ColumnFilter
from app.filters.date_filter import DateFilter

from app.utils.mac_utils import MacCleaner

from app.comparators.reconciliation_engine import ReconciliationEngine
from app.reports.excel_reporter import ExcelReporter

from app.core.logger import get_logger

logger = get_logger()


# ==================================================
# APP
# ==================================================

app = FastAPI(
    title="Network Asset Reconciliation",
    version="1.1.0"
)


# ==================================================
# DIRECTORIES
# ==================================================

UPLOAD_DIR = Path("input/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REPORT_DIR = Path("output/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = Path("app/static")


# ==================================================
# RETENTION / CLEANUP CONFIG
# ==================================================

RETENTION_DAYS = 15                       # delete session folders older than this
CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60   # run once every 24 hours


# ==================================================
# STATIC FILES
# ==================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ==================================================
# HELPER — VALIDATE SESSION ID (prevents path traversal)
# ==================================================

def _validate_session_id(session_id: str) -> None:
    """
    UUIDs are safe by construction, but we still validate the format
    defensively since session_id comes from the URL (user-controlled).
    This blocks any attempt to pass '../' or other path-breaking input.
    """
    try:
        uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session ID format.")


# ==================================================
# HELPER — FIND A REPORT WITHIN A SESSION FOLDER
# ==================================================

def _find_report(session_id: str, prefix: str) -> Path | None:
    """
    Look inside output/reports/<session_id>/ for a file
    starting with *prefix* (e.g. 'matched') and ending in .xlsx.
    """
    session_dir = REPORT_DIR / session_id
    if not session_dir.exists():
        return None

    candidates = sorted(
        session_dir.glob(f"{prefix}_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return candidates[0] if candidates else None


# ==================================================
# CLEANUP — DELETE SESSION FOLDERS OLDER THAN RETENTION_DAYS
# ==================================================

def _cleanup_old_sessions() -> None:
    """
    Scans both input/uploads/ and output/reports/ for session-ID
    subfolders whose last-modified time is older than RETENTION_DAYS,
    and deletes them entirely.

    Runs once at startup, then every CLEANUP_INTERVAL_SECONDS afterwards
    via the background task registered in the startup event below.
    """
    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0

    for base_dir in (UPLOAD_DIR, REPORT_DIR):
        if not base_dir.exists():
            continue

        for session_folder in base_dir.iterdir():
            if not session_folder.is_dir():
                continue

            try:
                mtime = datetime.fromtimestamp(session_folder.stat().st_mtime)
            except OSError:
                continue

            if mtime < cutoff:
                try:
                    shutil.rmtree(session_folder)
                    deleted_count += 1
                    logger.info(f"Cleanup: removed old session folder {session_folder}")
                except Exception as e:
                    logger.warning(f"Cleanup: failed to remove {session_folder}: {e}")

    if deleted_count:
        logger.info(f"Cleanup complete — removed {deleted_count} session folder(s).")
    else:
        logger.info("Cleanup complete — nothing to remove.")


async def _cleanup_loop() -> None:
    """
    Background task: runs cleanup immediately on startup, then repeats
    every CLEANUP_INTERVAL_SECONDS for as long as the app process is alive.
    """
    while True:
        try:
            _cleanup_old_sessions()
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")

        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


@app.on_event("startup")
async def start_cleanup_task():
    asyncio.create_task(_cleanup_loop())
    logger.info(
        f"Startup: cleanup scheduler started "
        f"(retention={RETENTION_DAYS} days, interval={CLEANUP_INTERVAL_SECONDS}s)"
    )


# ==================================================
# UI — SERVE FRONTEND
# ==================================================

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return HTMLResponse(
        content=html_path.read_text(encoding="utf-8"),
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
def health():
    return {
        "application": "Network Asset Reconciliation",
        "status": "running",
        "version": "1.1.0",
        "retention_days": RETENTION_DAYS
    }


# ==================================================
# UPLOAD + PROCESS
# ==================================================

ALLOWED_MONTHS = {1, 2, 3, 6}


@app.post("/upload")
async def upload_files(
    txt_file:          UploadFile = File(...),
    excel_file:         UploadFile = File(...),
    user_mapping_file:  UploadFile = File(...),
    months:             int        = Form(1),
    txt_file_2:         UploadFile | None = None
):

    if months not in ALLOWED_MONTHS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid months value '{months}'. Must be one of: 1, 2, 3, 6."
        )

    # ---------------------------------
    # CREATE UNIQUE SESSION FOLDERS
    # ---------------------------------
    # Every upload gets its own UUID. All inputs and outputs for this
    # run live ONLY inside these folders — this is what makes it
    # impossible for one user's download to ever serve another user's
    # report, even if both upload at the exact same time.

    session_id = str(uuid.uuid4())

    session_upload_dir = UPLOAD_DIR / session_id
    session_report_dir = REPORT_DIR / session_id

    session_upload_dir.mkdir(parents=True, exist_ok=True)
    session_report_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"New session started: {session_id}")

    try:

        # ---------------------------------
        # SAVE UPLOADED FILES (into session folder)
        # ---------------------------------

        # Use hardcoded, safe filenames within the isolated session directory
        # to completely eliminate any Path Traversal / Zip Slip risk.
        txt_path          = session_upload_dir / "network_export.txt"
        excel_path        = session_upload_dir / "inventory.xlsx"
        user_mapping_path = session_upload_dir / "user_mapping.xlsx"

        with open(txt_path, "wb") as f:
            shutil.copyfileobj(txt_file.file, f)
            if txt_file_2 and txt_file_2.filename:
                f.write(b"\n")
                shutil.copyfileobj(txt_file_2.file, f)

        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel_file.file, f)

        with open(user_mapping_path, "wb") as f:
            shutil.copyfileobj(user_mapping_file.file, f)

        # ---------------------------------
        # TXT PIPELINE
        # ---------------------------------

        txt_df = TxtParser().parse(str(txt_path))
        txt_df = MacCleaner.normalize(txt_df, "MAC Address")

        # ---------------------------------
        # INVENTORY PIPELINE
        # ---------------------------------

        inventory_df = ExcelReader().read(str(excel_path))
        inventory_df = ColumnFilter().extract(inventory_df)
        inventory_df = MacCleaner.normalize(inventory_df, "MAC Address")

        # ---------------------------------
        # USER MAPPING PIPELINE
        # ---------------------------------
        # Column detection now goes through ColumnFilter.extract_user_mapping(),
        # which uses the same separator-agnostic normalization as the
        # inventory file (handles "IP-Address", "IP_Address", "Mac-Address",
        # extra spaces, etc. with no per-file hardcoding needed). A ValueError
        # here means the file truly has no recognizable IP/Name column and
        # is converted into a clear 422 response.

        user_mapping_df = ExcelReader().read(str(user_mapping_path))

        try:
            user_mapping_df = ColumnFilter().extract_user_mapping(user_mapping_df)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        # ---------------------------------
        # COMPARE  (against full inventory — no date pre-filter)
        # ---------------------------------
        # Unmatched = TXT records whose IP+MAC is not in the Excel at all.
        # Date is NOT a matching criterion.

        engine = ReconciliationEngine()
        matched, txt_unmatched, inv_unmatched = engine.compare(txt_df, inventory_df)
        unmatched = pl.concat([txt_unmatched, inv_unmatched], how="diagonal")

        # ---------------------------------
        # DATE FILTER  (applied to matched AND the combined unmatched pool)
        # ---------------------------------
        # matched: drop rows with no date or a date older than the cutoff.
        # unmatched: keep_nulls=True — TXT-origin rows have no Last AgentCom
        #   date (TXT file only carries IP + MAC), so keep_nulls=False would
        #   silently wipe every TXT-side row and leave category_b always empty.
        #   With keep_nulls=True, only inventory-side rows with a date OLDER
        #   than the cutoff are removed; null-dated TXT rows are preserved.
        #
        # NOTE: the filter runs ONCE on the combined "unmatched" pool so that
        # Category A + Category B always sum to exactly what is in unmatched.
        matched, matched_excluded = DateFilter().split_by_months(matched, months=months, keep_nulls=False)
        excluded_by_date = matched_excluded.height
        unmatched, unmatched_excluded = DateFilter().split_by_months(unmatched, months=months, keep_nulls=True)
        
        excluded_by_date_df = pl.concat([matched_excluded, unmatched_excluded], how="diagonal")

        # ---------------------------------
        # SPLIT THE FILTERED UNMATCHED POOL BACK INTO CATEGORY A / CATEGORY B
        # ---------------------------------
        # Category A -> rows whose IP+MAC is found in the Asset Inventory Excel
        # Category B -> rows whose IP+MAC is found in the TXT network export
        category_a, category_b = engine.split_unmatched(unmatched, txt_df, inventory_df)

        # ---------------------------------
        # REPORTS (written into session folder)
        # ---------------------------------

        reporter = ExcelReporter()
        stats = reporter.generate_reports(
            matched=matched,
            unmatched=unmatched,
            txt_unmatched=category_b,
            inv_unmatched=category_a,
            txt_count=txt_df.height,
            user_mapping=user_mapping_df,
            output_dir=str(session_report_dir),    # ← write into session folder
            excluded_by_date_df=excluded_by_date_df
        )

        # ---------------------------------
        # RESPONSE
        # ---------------------------------

        return {
            "status": "success",
            "session_id": session_id,
            "months_filter": months,
            "txt_records": txt_df.height,
            "inventory_records": inventory_df.height,
            "user_mapping_records": user_mapping_df.height,
            "matched": matched.height,
            "unmatched": stats["unmatched_after_filter"],
            "unmatched_after_filter": stats["unmatched_after_filter"],
            "excluded_by_date_filter": excluded_by_date,
            "filtered_out_count": stats["filtered_out_count"],
            "reports": {
                "matched":   f"/download/{session_id}/matched",
                "unmatched": f"/download/{session_id}/unmatched",
                "txt_unmatched": f"/download/{session_id}/txt_unmatched",
                "inv_unmatched": f"/download/{session_id}/inv_unmatched",
                "summary":   f"/download/{session_id}/summary",
                "filtered_out": f"/download/{session_id}/filtered_out",
                "excluded_by_date": f"/download/{session_id}/excluded_by_date"
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to process session {session_id}: {e}")
        # Cleanup on failure so we don't leak partial data
        if session_upload_dir.exists():
            shutil.rmtree(session_upload_dir, ignore_errors=True)
        if session_report_dir.exists():
            shutil.rmtree(session_report_dir, ignore_errors=True)
            
        # Sanitize error message to prevent Information Disclosure (leaking server paths)
        safe_msg = str(e).replace(str(UPLOAD_DIR), "[SECURE_UPLOAD_DIR]")
        raise HTTPException(status_code=500, detail=safe_msg)


# ==================================================
# DOWNLOAD — MATCHED / UNMATCHED / SUMMARY
# ==================================================
# All three now require the session_id from the upload response,
# so downloads are scoped to exactly the run that produced them.

@app.get("/download/{session_id}/matched")
def download_matched(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "matched")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No matched report found for this session. It may have expired or been removed."
        )

    return FileResponse(
        str(latest),
        filename="matched.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/download/{session_id}/unmatched")
def download_unmatched(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "unmatched_combined")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No unmatched combined report found for this session. It may have expired or been removed."
        )

    return FileResponse(
        str(latest),
        filename="unmatched.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/download/{session_id}/inv_unmatched")
def download_inv_unmatched(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "data_match")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No unmatched inventory report found for this session. It may have expired or been removed."
        )

    return FileResponse(
        str(latest),
        filename="Unmatched_data_match_Excel.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/download/{session_id}/txt_unmatched")
def download_txt_unmatched(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "data_unmatched")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No unmatched network report found for this session. It may have expired or been removed."
        )

    return FileResponse(
        str(latest),
        filename="Unmatched_data_unmatched_Excel.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/download/{session_id}/summary")
def download_summary(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "summary")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No summary report found for this session. It may have expired or been removed."
        )

    return FileResponse(
        str(latest),
        filename="summary.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/download/{session_id}/filtered_out")
def download_filtered_out(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "filtered_out")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No filtered out report found for this session."
        )

    return FileResponse(
        str(latest),
        filename="filtered_out.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.get("/download/{session_id}/excluded_by_date")
def download_excluded_by_date(session_id: str):
    _validate_session_id(session_id)

    latest = _find_report(session_id, "excluded_by_date")
    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No excluded by date report found for this session."
        )

    return FileResponse(
        str(latest),
        filename="excluded_by_date.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )