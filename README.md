# SCL Automation – Network Asset Reconciliation System

**An automated web application for reconciling network assets by comparing TXT source binding files against Excel inventory records — with categorized unmatched reports, user name enrichment, and date-based filtering.**

Developed as part of internship work at SCL to automate asset verification, reduce manual reconciliation efforts, and deliver professional, downloadable Excel reports through a modern dark-themed web UI.

---

## Overview

SCL Automation is a full-stack network asset reconciliation tool built with **Python**, **FastAPI**, and **Polars**. It accepts up to four input files via a drag-and-drop web interface:

1. **TXT File** (and optional **2nd TXT File**) — Network source binding export (IP + MAC address per line). Multiple files are automatically merged.
2. **Excel Inventory File** — Internal asset inventory with IP, MAC, Computer Name, and last agent communication dates
3. **User Mapping File** — Maps IP addresses to human-readable user/device names

The system reconciles records using exact **IP + MAC address matching**, applies a configurable **date filter**, and generates **5 categorized downloadable Excel reports** with professional formatting.

---

## System Architecture

### Data Processing Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                          INPUT LAYER                             │
├──────────────────┬──────────────────┬────────────────────────────┤
│  TXT Files (1-2) │  Excel Inventory │  User Mapping File         │
│  (ip-address     │  (IP, MAC,       │  (IP Address → Name)       │
│   mac-address)   │   CompName, Date)│                            │
└────────┬─────────┴────────┬─────────┴──────────┬─────────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
    ┌──────────────┬──────────────────┬───────────────────┐
    │  TXT Parser  │  Excel Reader    │  User Mapping     │
    │  (Regex)     │  (Polars)        │  Parser           │
    └──────┬───────┴────────┬─────────┴─────────┬─────────┘
           │                │                   │
           ▼                ▼                   │
    ┌──────────────┬──────────────────┐         │
    │ MAC Normalize│  Column Filter   │         │
    │ (hex-only,   │  (IP, MAC,       │         │
    │  lowercase)  │   Date, Name)    │         │
    └──────┬───────┴────────┬─────────┘         │
           │                │                   │
           └────────────┬───┘                   │
                        ▼                       │
             ┌──────────────────────┐           │
             │  Reconciliation      │           │
             │  Engine              │           │
             │  (IP + MAC Matching) │           │
             └──────────┬───────────┘           │
                        │                       │
           ┌────────────┼───────────┐           │
           ▼            ▼           ▼           │
      ┌─────────┐  ┌─────────┐ ┌─────────┐     │
      │ Matched │  │Category │ │Category │     │
      │ Records │  │A (Inv.) │ │B (Net.) │     │
      └────┬────┘  └────┬────┘ └────┬────┘     │
           │            │           │           │
           └────────────┴───────────┴─────┬─────┘
                                          ▼
                               ┌──────────────────────┐
                               │  Date Filter         │
                               │  (1 / 2 / 3 / 6 mo.) │
                               └──────────┬───────────┘
                                          │
                               ┌──────────▼───────────┐
                               │  User Name Enrichment│
                               │  (IP → Name lookup,  │
                               │   CompName fallback) │
                               └──────────┬───────────┘
                                          │
                               ┌──────────▼───────────┐
                               │  Excel Reporter      │
                               │  (5 XLSX outputs)    │
                               └──────────────────────┘
```

### Report Outputs

| File | Description |
|------|-------------|
| `matched.xlsx` | Records where IP + MAC matched exactly between TXT and Inventory |
| `unmatched.xlsx` | Combined view of all unmatched records (Category A + B) |
| `data_match.xlsx` | **Category A** — Inventory assets NOT seen on the network (TXT) |
| `data_unmatched.xlsx` | **Category B** — Network assets (TXT) NOT found in inventory (excluding `Last AgentCom` column) |
| `summary.xlsx` | Statistics: total records, match counts, match percentage, date filter used |

---

## Project Structure

```
SCL_2026/
├── app/                          # Main application package
│   ├── main.py                   # FastAPI app: routes, session management, download endpoints
│   ├── static/
│   │   └── index.html            # Full-featured dark-mode web UI
│   ├── parsers/
│   │   ├── txt_parser.py         # Regex-based TXT source binding parser
│   │   └── excel_reader.py       # Multi-strategy Excel reader (Polars)
│   ├── filters/
│   │   ├── date_filter.py        # Filter records by N-month lookback window
│   │   └── column_filter.py      # Extract/normalize required inventory columns
│   ├── comparators/
│   │   └── reconciliation_engine.py  # IP+MAC matching; returns matched, Category A, Category B
│   ├── reports/
│   │   └── excel_reporter.py     # Generate 5 formatted XLSX files per session
│   ├── utils/
│   │   ├── mac_utils.py          # MAC address normalization (strip separators, lowercase)
│   │   ├── archive_manager.py    # Processed file archiving
│   │   └── file_logger.py        # File-based operation logging
│   ├── watcher/
│   │   └── folder_watcher.py     # Watchdog-based automatic file pair processing
│   └── core/
│       └── logger.py             # Centralized Loguru logger setup
│
├── config/                       # YAML configuration files
│   ├── settings.yaml
│   ├── mappings.yaml
│   └── logging.yaml
│
├── input/uploads/                # Per-session uploaded file storage (auto-cleaned)
├── output/reports/               # Per-session generated Excel reports (auto-cleaned)
├── logs/                         # Application logs
├── tests/                        # Pytest unit tests
├── docker/                       # Docker configuration
├── requirements.txt
└── README.md
```

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/RavikantBedi/SCL_24.git
cd SCL_24

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open your browser at: **http://localhost:8000**

---

## Running the Application

### Web UI (Recommended)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Navigate to **http://localhost:8000** and use the drag-and-drop interface to:
1. Upload your **TXT network file** (and optionally a **2nd TXT file**)
2. Upload your **Excel inventory file**
3. Upload your **User Mapping Excel file**
4. Select a **date filter** (1, 2, 3, or 6 months)
5. Click **Run Reconciliation**
6. Download any of the **5 generated reports**

### Folder Watcher (Automatic / Batch)

Automatically processes TXT + Excel file pairs placed in the watch folder:

```bash
python -m app.watcher.folder_watcher
```

### Docker

```bash
docker compose -f docker/docker-compose.yml up --build
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/` | Serve the web UI |
| `GET`  | `/health` | Health check |
| `POST` | `/upload` | Upload 3-4 files + months filter, returns session ID and stats |
| `GET`  | `/download/{session_id}/matched` | Download `matched.xlsx` |
| `GET`  | `/download/{session_id}/unmatched` | Download `unmatched.xlsx` (combined) |
| `GET`  | `/download/{session_id}/inv_unmatched` | Download `data_match.xlsx` (Category A) |
| `GET`  | `/download/{session_id}/txt_unmatched` | Download `data_unmatched.xlsx` (Category B) |
| `GET`  | `/download/{session_id}/summary` | Download `summary.xlsx` |

> Each upload creates a unique **UUID session**. Downloads are session-scoped — two concurrent users never see each other's reports.

---

## Input File Formats

### TXT File (Source Binding Export)
Each line must contain an IP address and MAC address in any common format:
```
ip-address 192.168.1.10 mac-address A4:64:A9:13:ED:2C
ip-address 10.143.12.36 mac-address a464-a913-ed45
```

Supported separators: `:`, `-`, `.`, spaces, or none.

### Excel Inventory File
Must contain (column names are flexible — auto-detected):
- `IP Address` / `IPAdd` / `IP`
- `MAC Address` / `Mac Address`
- `Last AgentCom` / `Last Agent Communication` (date column for filtering)
- `CompName` (computer/device name — used as User Name fallback)

### User Mapping File
Must contain two columns:
- `IP Address` / `IP`
- `Name` / `User Name`

This file maps IP addresses to human-readable names. If an IP has no mapping, the system automatically falls back to `CompName` from inventory.

---

## Reconciliation Logic

### Matching Strategy
Records are matched using **exact IP + MAC address comparison**:
- MAC addresses are normalized: all separators removed, converted to lowercase hex
- IP addresses are whitespace-stripped
- A record is **matched** only when **both** IP and MAC agree between TXT and Inventory

### Unmatched Categories

| Category | Description |
|----------|-------------|
| **Category A** (`data_match.xlsx`) | Assets in your Inventory file that were NOT found on the network (TXT). These are devices registered in your system but not seen actively on the network. |
| **Category B** (`data_unmatched.xlsx`) | Assets on the network (TXT) that were NOT found in your Inventory. These are devices active on the network but not registered in your system. |

### Date Filtering
After reconciliation, all records are filtered by the `Last AgentCom` date column. Records older than the selected lookback period are excluded from **all** 5 output files:

| Option | Keeps records with agent comm in last... |
|--------|------------------------------------------|
| 1 Month | 30 days |
| 2 Months | 60 days |
| 3 Months | 90 days |
| 6 Months | 180 days |

### User Name Enrichment
For every record in every report:
1. Lookup the IP in the **User Mapping file** → use `Name` if found
2. If not found → use `CompName` from Inventory as fallback
3. If no `CompName` either → value is `"Unknown"`

---

## Session Management & Auto-Cleanup

Each upload gets an isolated UUID-based session:
- Uploaded files → `input/uploads/<session_id>/`
- Generated reports → `output/reports/<session_id>/`
- Sessions older than **15 days** are automatically deleted by a background cleanup task that runs every 24 hours

This ensures:
- No file conflicts between concurrent users
- Automatic disk space management
- Download links remain valid for 15 days

---

## Output Report Format

All generated Excel files include professional formatting applied automatically:

- **Dark blue header row** with white bold text
- **Thin cell borders** on all data cells
- **Center-aligned** content
- **Auto-sized column widths**
- **Frozen header row** (row 1 stays visible when scrolling)
- **Timestamped filenames** (e.g., `matched_20260623_013952.xlsx`)

---

## Key Features

- ✅ **Drag-and-Drop Web UI** — Modern dark-mode interface with animated progress steps
- ✅ **Multi-File Merging** — Optionally upload a second TXT file to combine multiple network exports automatically before processing
- ✅ **IP + MAC Reconciliation** — Exact dual-key matching with MAC normalization
- ✅ **5 Report Downloads** — Matched, combined unmatched, Category A, Category B, Summary
- ✅ **Date Filtering** — Keep only records active in the last 1, 2, 3, or 6 months
- ✅ **User Name Enrichment** — Auto-fills user names via IP lookup with CompName fallback
- ✅ **Session Isolation** — Per-user UUID sessions prevent report cross-contamination
- ✅ **Auto-Cleanup** — Sessions older than 15 days are automatically purged
- ✅ **Flexible Column Detection** — Handles variant column names across different Excel formats
- ✅ **Professional Excel Output** — Formatted headers, borders, frozen rows, auto column widths
- ✅ **Folder Watcher** — Automatic batch processing without the web UI
- ✅ **Docker Support** — Containerized deployment ready

---

## Testing

```bash
pytest tests/                   # Run all tests
pytest tests/ -v                # Verbose output
pytest tests/ --cov=app         # With coverage report
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | REST API framework and web server |
| `uvicorn` | ASGI application server |
| `polars` | High-performance DataFrame processing (primary engine) |
| `openpyxl` | Read/write `.xlsx` files + apply cell formatting |
| `python-multipart` | Multipart form data and file upload handling |
| `loguru` | Advanced logging with rotation and formatting |
| `watchdog` | File system monitoring for folder watcher mode |
| `pyyaml` | YAML configuration file parsing |
| `pyarrow` | Data format interoperability |
| `pytest` | Unit testing framework |

Install all:
```bash
pip install -r requirements.txt
```

---

## System Requirements

| Spec | Minimum | Recommended |
|------|---------|-------------|
| OS | Windows / Linux / macOS | Windows 10+ / Ubuntu 22.04+ |
| Python | 3.10 | 3.11+ |
| RAM | 2 GB | 4 GB+ (for large datasets) |
| Disk | 500 MB | 2 GB+ (logs + session data) |
| Docker | 20.10+ | Latest |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv: `.\.venv\Scripts\activate` then `pip install -r requirements.txt` |
| Port 8000 in use | Use `--port 8001` |
| Upload returns 422 | Check that User Mapping file has `IP Address` and `Name` columns |
| All reports are empty | Date filter may be too strict — try 6 months |
| MAC addresses not matching | Verify both files use the same physical MAC addresses |
| Reports expire / 404 on download | Sessions expire after 15 days — re-upload your files |
| `pl is not defined` error | Ensure `import polars as pl` is at top of `main.py` |

Check `logs/app.log` for detailed operation history.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2024-12-01 | Initial release — FastAPI UI, folder watcher, Excel reporting |
| 1.1.0 | 2024-12-15 | Added user mapping enrichment, improved Excel handling |
| 1.2.0 | 2025-01-10 | Enhanced error handling, comprehensive logging, Docker support |
| 2.0.0 | 2026-06-23 | Session isolation, 5-report split, Category A/B unmatched, date filtering on all reports, CompName fallback, auto-cleanup, UI overhaul |
| 2.1.0 | 2026-06-25 | Added support for uploading and merging a second optional TXT network file |

---

## Author

**Ravikant Bedi** — SCL Internship Project  
GitHub: [https://github.com/RavikantBedi/SCL_24](https://github.com/RavikantBedi/SCL_24)

---

## License

[Your License Here]

---

## Acknowledgments

- Built with **FastAPI** for clean, async REST API design
- **Polars** for blazing-fast DataFrame operations
- **OpenPyXL** for professional Excel formatting
- **Loguru** for structured, human-readable logging
- Thanks to the open-source community for all dependencies
