# SCL Automation – Network Asset Reconciliation System

**An automated web application for reconciling network assets by comparing TXT source binding files against Excel inventory records — with categorized unmatched reports, user name enrichment, date-based filtering, and automated IP/MAC exclusions.**

Developed as part of internship work at SCL to automate asset verification, reduce manual reconciliation efforts, and deliver professional, downloadable Excel reports through a modern dark-themed web UI.

---

## Overview

SCL Automation is a full-stack network asset reconciliation tool built with **Python**, **FastAPI**, and **Polars**. It accepts up to four input files via a drag-and-drop web interface:

1. **TXT File** (and optional **2nd TXT File**) — Network source binding export (IP + MAC address per line). Multiple files are automatically merged.
2. **Excel Inventory File** — Internal asset inventory with IP, MAC, Computer Name, and last agent communication dates
3. **User Mapping File** — Maps IP addresses to human-readable user/device names

The system reconciles records using exact **IP + MAC address matching**, applies a configurable **date filter**, automatically **filters out specific IPs and MACs**, and generates **6 categorized downloadable Excel reports** with professional formatting.

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
    │  (Regex)     │  (Calamine/Rust) │  Parser           │
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
      ┌─────────┐  ┌─────────┐ ┌─────────┐      │
      │ Matched │  │Category │ │Category │      │
      │ Records │  │A (Inv.) │ │B (Net.) │      │
      └────┬────┘  └────┬────┘ └────┬────┘      │
           │            │           │           │
           └────────────┴───────────┴─────┬─────┘
                                          ▼
                               ┌──────────────────────┐
                               │  Date Filter         │
                               │  (1 / 2 / 3 / 6 mo.) │
                               └──────────┬───────────┘
                                          │
                               ┌──────────▼───────────┐
                               │  IP/MAC Exclusion    │
                               │  Filter              │
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
                               │  (6 XLSX outputs)    │
                               └──────────────────────┘
```

### Report Outputs

| File | Description |
|------|-------------|
| `matched.xlsx` | Records where IP + MAC matched exactly between TXT and Inventory |
| `unmatched_combined.xlsx` | Combined view of all unmatched records (Category A + B) |
| `data_match.xlsx` | **Category A** — Inventory assets NOT seen on the network (TXT) |
| `data_unmatched.xlsx` | **Category B** — Network assets (TXT) NOT found in inventory |
| `filtered_out.xlsx` | Records removed from the unmatched reports due to IP/MAC exclusion rules |
| `summary.xlsx` | Statistics: total records, match counts, match percentage, excluded counts |

---

## Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/RavikantBedi/SCL_v26_2.git
cd SCL_v26_2

# 2. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux/macOS

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
6. Download any of the **6 generated reports**

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
After reconciliation, all records are filtered by the `Last AgentCom` date column. Records older than the selected lookback period are excluded from **all** output files. 

### IP/MAC Exclusion Filtering
Before generating Unmatched reports, records matching predefined criteria (e.g., IPs starting with `192.168.0.`, or MACs starting with `7cd30a`) are removed from the Unmatched and Category A/B lists, and placed securely into a dedicated `filtered_out.xlsx` file. Matched records are never filtered out.

### User Name Enrichment
For every record in every report:
1. Lookup the IP in the **User Mapping file** → use `Name` if found (last listed priority on duplicates)
2. If not found or blank → use `CompName` from Inventory as fallback
3. If no `CompName` either → value is `"Unknown"`

---

## Key Features & Recent Updates

- ✅ **Calamine / FastExcel Integration** — Excel files are now read using Rust-backed fastexcel/calamine, dropping large file parse times by up to 90%. Includes automatic pandas/openpyxl fallback for corrupted files.
- ✅ **Null-Safe Dark UI** — Fully responsive web interface with robust cache-busting headers to prevent stale JavaScript logic, and safe wrappers that ensure metrics never break into "undefined" statuses.
- ✅ **Automated IP/MAC Exclusions** — Built-in filtering engine auto-diverts ignored IP/MAC ranges into the new `filtered_out.xlsx` report.
- ✅ **Multi-File Merging** — Upload a second TXT file to combine multiple network exports automatically.
- ✅ **Accurate Match Rate Logic** — Match rates dynamically calculate matched proportions *before* the date filter drops records, providing mathematically sound stats.
- ✅ **Fault Tolerant TXT Parsing** — Gracefully handles completely empty or missing column TXT datasets without crashing the reconciliation engine.
- ✅ **Professional Excel Output** — Formatted headers, borders, frozen rows, auto column widths natively applied to all 6 outputs.

---

## Author

**Ravikant Bedi** — SCL Internship Project  
GitHub: [https://github.com/RavikantBedi/SCL_v26_2](https://github.com/RavikantBedi/SCL_v26_2)
