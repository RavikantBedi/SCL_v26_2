# SCL Automation – Network Asset Reconciliation System

**An automated solution for reconciling network assets by comparing TXT source binding files with Excel inventory records.**

Developed as part of internship work to automate asset verification, reduce manual reconciliation efforts, and provide professional Excel reports for network asset management.

---

## 🎯 Overview

SCL Automation is a Python-based system that:

✅ **Monitors** incoming TXT and Excel files automatically  
✅ **Parses** source binding TXT files (IP Address, MAC Address)  
✅ **Normalizes** MAC addresses into a standard format  
✅ **Filters** outdated inventory records (configurable date range)  
✅ **Reconciles** records by matching IP and MAC addresses  
✅ **Generates** professional Excel reports (matched, unmatched, summary)  
✅ **Archives** processed files for auditing  
✅ **Logs** all operations for troubleshooting  
✅ **Deploys** via Docker for consistent environments  

---

## 🏗️ System Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  TXT File       │         │  Excel File      │
│  (Source        │         │  (Inventory      │
│   Binding)      │         │   Records)       │
└────────┬────────┘         └────────┬─────────┘
         │                            │
         ▼                            ▼
    ┌────────────┐            ┌─────────────┐
    │ TXT Parser │            │Excel Reader │
    └────┬───────┘            └──────┬──────┘
         │                            │
         ▼                            ▼
   ┌──────────────┐          ┌─────────────────┐
   │ MAC          │          │ Date Filter     │
   │ Normalization│          │ (6 months)      │
   └──────┬───────┘          └────────┬────────┘
          │                           │
          │     ┌─────────────────────┘
          │     │
          ▼     ▼
    ┌──────────────────────┐
    │ Reconciliation Engine│
    │ (IP + MAC Match)     │
    └──────────┬───────────┘
               │
         ┌─────┴──────┐
         ▼            ▼
    ┌─────────┐  ┌────────────┐
    │ Matched │  │ Unmatched  │
    │ Records │  │ Records    │
    └────┬────┘  └──────┬─────┘
         │              │
         │     ┌────────┘
         │     │
         ▼     ▼
    ┌──────────────────────┐
    │ Excel Reporter       │
    │ (Professional Format)│
    └──────────┬───────────┘
               │
         ┌─────┴──────────────┐
         ▼                    ▼
    ┌─────────────┐    ┌────────────────┐
    │ Reports     │    │ Archive &      │
    │ (XLSX)      │    │ Logs           │
    └─────────────┘    └────────────────┘
```

---

## 📁 Project Structure

```
SCL_AUTOMATION/
│
├── 📂 app/                               # Main application
│   ├── main.py                          # FastAPI entry point
│   ├── watcher/                         # File system monitoring
│   │   └── folder_watcher.py            # Watches input/incoming/
│   ├── parsers/                         # File parsing
│   │   ├── txt_parser.py                # Extracts IP + MAC from TXT
│   │   └── excel_reader.py              # Reads Excel inventory
│   ├── filters/                         # Data processing
│   │   ├── date_filter.py               # Removes old records
│   │   └── column_filter.py             # Column selection
│   ├── comparators/                     # Reconciliation logic
│   │   └── reconciliation_engine.py     # IP + MAC matching
│   ├── reports/                         # Report generation
│   │   └── excel_reporter.py            # Creates XLSX with formatting
│   ├── utils/                           # Helpers
│   │   ├── mac_utils.py                 # MAC address normalization
│   │   ├── file_utils.py                # File operations
│   │   ├── archive_manager.py           # File archiving
│   │   └── date_utils.py                # Date operations
│   └── core/                            # Core utilities
│       └── logger.py                    # Logging
│
├── 📂 config/                           # Configuration files
│   ├── settings.yaml                    # App settings
│   ├── mappings.yaml                    # Field mappings
│   └── logging.yaml                     # Log configuration
│
├── 📂 input/                            # Input directories
│   └── incoming/                        # Files to process (watched)
│
├── 📂 output/                           # Generated reports
│   └── reports/                         # timestamped XLSX files
│
├── 📂 archive/                          # Processed files
│   ├── txt/                             # Archived TXT files
│   └── excel/                           # Archived Excel files
│
├── 📂 logs/                             # Application logs
│
├── 📂 tests/                            # Unit tests
│   ├── test_parser.py                   # Parser tests
│   ├── test_compare.py                  # Comparison tests
│   └── ...                              # Other tests
│
├── 📂 docker/                           # Docker files
│   ├── Dockerfile                       # Container image
│   └── docker-compose.yml               # Container orchestration
│
├── requirements.txt                     # Python dependencies
├── pytest.ini                           # Pytest configuration
└── README.md                            # This file
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **pip** package manager

### Installation

**1. Clone/Navigate to project:**
```bash
cd d:\INTERNSHIP_SCL_2\SCL_AUTOMATION
```

**2. Create virtual environment:**
```bash
python -m venv .venv
.\.venv\Scripts\activate      # Windows
# source .venv/bin/activate   # Linux/macOS
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Application

### Option 1: **Folder Watcher** (Recommended - Automatic Processing)

Monitors `input/incoming/` folder for new files and processes them automatically.

```bash
python -m app.watcher.folder_watcher
```

**Workflow:**
1. Place TXT file and Excel file in `input/incoming/`
2. System automatically detects them
3. Files are processed
4. Reports generated in `output/reports/`
5. Files archived in `archive/`

---

### Option 2: **FastAPI Server & Web UI** (Interactive Processing)

Runs the HTTP server providing both a REST API and a modern web interface.

```bash
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Access:**
- 🖥️ **Web UI:** http://localhost:8000/ (Drag-and-drop interface with progress tracking)
- 🌐 Interactive API Docs: http://localhost:8000/docs
- 📖 Alternative Docs: http://localhost:8000/redoc

**Web UI Features:**
- Interactive drag-and-drop zones for TXT and Excel files
- Real-time processing progress bar
- Instant download buttons for matched, unmatched, and summary reports
- Modern, animated design

**Example API Call:**
```bash
curl -X POST http://localhost:8000/upload ^
  -F "txt_file=@input/incoming/binding.txt" ^
  -F "excel_file=@input/incoming/inventory.xlsx"
```

---

### Option 3: **Docker Deployment**

Run the entire system in a containerized environment.

**Build & Run:**
```bash
docker compose -f docker/docker-compose.yml up --build
```

**Background Execution:**
```bash
docker compose -f docker/docker-compose.yml up -d
docker compose -f docker/docker-compose.yml logs -f          # View logs
docker compose -f docker/docker-compose.yml down             # Stop
```

**Benefits:**
- Consistent environment across machines
- No local Python/dependency conflicts
- Easy scaling and deployment

---

## 📊 Processing Workflow

### Input Files Required

**TXT File Format (Source Binding):**
```
ip-address 192.168.1.10 mac-address 00-1A-2B-3C-4D-5E
ip-address 192.168.1.11 mac-address 00-1A-2B-3C-4D-5F
```

**Excel File Format (Inventory):**
| IP Address | MAC Address | Device Name | Last Agent Comm |
|-----------|-------------|-------------|-----------------|
| 192.168.1.10 | 00:1A:2B:3C:4D:5E | DEVICE-01 | 2024-12-01 |
| 192.168.1.15 | 00:1A:2B:3C:4D:6F | DEVICE-02 | 2024-11-15 |

### Processing Steps

1. **Parse TXT** → Extract IP + MAC addresses
2. **Parse Excel** → Read inventory records
3. **Normalize MAC** → Convert to standard format (no separators, lowercase)
4. **Filter by Date** → Keep records from last 6 months (configurable)
5. **Reconcile** → Match records using IP + MAC
6. **Generate Reports** → Create Excel files with formatting
7. **Archive Files** → Move processed files to archive/
8. **Log Everything** → Write operation logs

### Generated Reports

All reports are timestamped and saved in `output/reports/`:

**matched_YYYYMMDD_HHMMSS.xlsx**
- Records that matched (found in both TXT and Excel)
- Includes: IP, MAC, Device Name, Last Agent Comm

**unmatched_YYYYMMDD_HHMMSS.xlsx**
- Records that didn't match
- Helps identify missing or changed assets

**summary_YYYYMMDD_HHMMSS.xlsx**
- Statistics and summary report
- Total records, matched count, unmatched count
- Useful for management reporting

**Report Features:**
- 🎨 Professional formatting (blue headers, borders)
- 📐 Auto-sized columns
- ❄️ Frozen header rows
- 🎯 Centered alignment

---

## 🧪 Testing

Run the test suite to verify functionality:

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_parser.py

# Run with coverage report
pytest tests/ --cov=app --cov-report=html
```

---

## 📝 Configuration

### settings.yaml
```yaml
# Customize application behavior
date_filter_months: 6          # How many months to keep
watch_folder: input/incoming   # Folder to monitor
process_delay: 5               # Seconds to wait before processing
```

### logging.yaml
```yaml
# Configure logging levels and output
version: 1
handlers:
  file:
    filename: logs/app.log
  console:
    level: INFO
```

---

## 📋 Key Features

### MAC Address Normalization
- Removes hyphens, colons, dots, spaces
- Converts to lowercase
- Ensures consistent matching

### Flexible Column Mapping
- Automatically detects column names
- Supports variations (MAC Address, MAC, mac-address, etc.)
- Easy to extend for new formats

### Professional Excel Reports
- Blue headers with white text
- Cell borders and alignment
- Auto-sized columns for readability
- Frozen header rows for easy scrolling

### Automatic Archiving
- Processed files moved to `archive/` folder
- Organized by type (TXT/Excel)
- Preserves original files for audit trail

### Comprehensive Logging
- Operation timestamps
- Record counts
- Error details
- Useful for troubleshooting

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Activate venv: `.\.venv\Scripts\activate` then reinstall: `pip install -r requirements.txt` |
| `Port 8000 already in use` | Kill process or use different port: `--port 8001` |
| `Files not detected` | Check `input/incoming/` folder exists and has read permissions |
| `No reports generated` | Check `output/` folder exists; verify TXT format has IP + MAC patterns |
| `Docker build fails` | Ensure Docker Desktop is running; try `docker system prune` |

---

## 📚 Dependencies

| Package | Purpose |
|---------|---------|
| `polars` | Fast DataFrame processing |
| `pandas` | Alternative data processing |
| `pyarrow` | Memory and data interoperability |
| `duckdb` | In-memory SQL analytics |
| `openpyxl` | Read/write Excel files |
| `xlsxwriter` | Excel formatting |
| `xlrd` | Read legacy Excel files |
| `watchdog` | File system monitoring |
| `fastapi` | REST API framework and Web UI |
| `uvicorn` | ASGI server |
| `python-multipart` | Handle file uploads in FastAPI |
| `loguru` | Advanced logging |
| `pyyaml` | Configuration parsing |
| `python-dotenv` | Environment variable management |
| `pytest` | Testing framework |

---

## 🔧 Technologies

- **Language:** Python 3.10
- **Data Processing:** Polars (high-performance DataFrames)
- **Excel:** OpenPyXL, XlsxWriter
- **File Monitoring:** Watchdog
- **Web Framework:** FastAPI + Uvicorn
- **Containerization:** Docker + Docker Compose
- **Testing:** Pytest

---

## 📞 Support & Documentation

- **Architecture:** See `docs/architecture.md`
- **API Guide:** See `docs/api_docs.md`
- **User Guide:** See `docs/user_guide.md`
- **Logs:** Check `logs/` folder for operation details

---

## 👨‍💼 Author

Developed by: **SCL Internship Team**

Developed as part of internship work to automate network asset reconciliation and inventory validation.

---

## 📄 License

[Your License Here]
