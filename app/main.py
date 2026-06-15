from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.parsers.txt_parser import TxtParser
from app.parsers.excel_reader import ExcelReader

from app.filters.column_filter import ColumnFilter
from app.filters.date_filter import DateFilter

from app.utils.mac_utils import MacCleaner

from app.comparators.reconciliation_engine import ReconciliationEngine
from app.reports.excel_reporter import ExcelReporter


# ==================================================
# APP
# ==================================================

app = FastAPI(
    title="Network Asset Reconciliation",
    version="1.0.0"
)


# ==================================================
# DIRECTORIES
# ==================================================

UPLOAD_DIR = Path("input/uploads")

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_DIR = Path("output/reports")

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

STATIC_DIR = Path("app/static")


# ==================================================
# STATIC FILES
# ==================================================

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# ==================================================
# HELPER — LATEST REPORT FILE
# ==================================================

def _latest_report(prefix: str) -> Path | None:
    """
    Return the most recently modified file in REPORT_DIR
    whose name starts with *prefix* and ends with .xlsx.
    Returns None if no such file exists.
    """
    candidates = sorted(
        REPORT_DIR.glob(f"{prefix}_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return candidates[0] if candidates else None


# ==================================================
# UI — SERVE FRONTEND
# ==================================================

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    html_path = STATIC_DIR / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="UI not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


# ==================================================
# HEALTH CHECK
# ==================================================

@app.get("/health")
def health():
    return {
        "application": "Network Asset Reconciliation",
        "status": "running",
        "version": "1.0.0"
    }


# ==================================================
# UPLOAD + PROCESS
# ==================================================

@app.post("/upload")
async def upload_files(
    txt_file: UploadFile = File(...),
    excel_file: UploadFile = File(...)
):

    try:

        # ---------------------------------
        # SAVE UPLOADED FILES
        # ---------------------------------

        txt_path   = UPLOAD_DIR / txt_file.filename
        excel_path = UPLOAD_DIR / excel_file.filename

        with open(txt_path, "wb") as f:
            shutil.copyfileobj(txt_file.file, f)

        with open(excel_path, "wb") as f:
            shutil.copyfileobj(excel_file.file, f)

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

        inventory_df = DateFilter().filter_by_months(inventory_df, months=6)

        # ---------------------------------
        # COMPARE
        # ---------------------------------

        engine = ReconciliationEngine()

        matched, unmatched = engine.compare(txt_df, inventory_df)

        # ---------------------------------
        # REPORTS
        # ---------------------------------

        reporter = ExcelReporter()

        reporter.generate_reports(
            matched=matched,
            unmatched=unmatched,
            txt_count=txt_df.height
        )

        # ---------------------------------
        # RESPONSE
        # ---------------------------------

        return {
            "status": "success",
            "txt_records": txt_df.height,
            "inventory_records": inventory_df.height,
            "matched": matched.height,
            "unmatched": unmatched.height,
            "reports": {
                "matched":   "/download/matched",
                "unmatched": "/download/unmatched",
                "summary":   "/download/summary"
            }
        }

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


# ==================================================
# DOWNLOAD MATCHED
# ==================================================

@app.get("/download/matched")
def download_matched():

    latest = _latest_report("matched")

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No matched report found. Please run reconciliation first."
        )

    return FileResponse(
        str(latest),
        filename="matched.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ==================================================
# DOWNLOAD UNMATCHED
# ==================================================

@app.get("/download/unmatched")
def download_unmatched():

    latest = _latest_report("unmatched")

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No unmatched report found. Please run reconciliation first."
        )

    return FileResponse(
        str(latest),
        filename="unmatched.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ==================================================
# DOWNLOAD SUMMARY
# ==================================================

@app.get("/download/summary")
def download_summary():

    latest = _latest_report("summary")

    if not latest:
        raise HTTPException(
            status_code=404,
            detail="No summary report found. Please run reconciliation first."
        )

    return FileResponse(
        str(latest),
        filename="summary.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )