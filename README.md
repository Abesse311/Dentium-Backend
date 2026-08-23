# 🦷 Dental Clinic Management System — Backend

A local FastAPI backend with SQLite database designed to power a Flutter Desktop dental clinic management application.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Run Backend API Server
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Open Interactive Swagger UI
Open your browser at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to explore and execute all endpoints.

### 4. Run Test Suite
```bash
py run_tests.py
```

---

## 📁 Project Structure
```
backend/
├── main.py                     # App entry point, CORS middleware, router registration
├── database.py                 # SQLite engine, sessions, foreign keys, table bootstrap
├── models.py                   # SQLAlchemy ORM models (8 interconnected tables)
├── schemas.py                  # Pydantic v2 validation schemas
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, ReportLab, etc.)
├── README.md                   # Detailed API endpoint specifications
├── clinic.db                   # SQLite database file
├── services/
│   └── pdf_service.py          # In-memory invoice PDF generation (ReportLab)
└── routers/
    ├── dashboard.py            # Real-time KPIs & daily schedule agenda
    ├── patients.py             # Full patient CRUD, search, and medical history
    ├── appointments.py         # Day-based bookings, week calendar & capacity limit
    ├── treatments.py           # Dental treatments (FDI 11-48) & French procedure catalog
    ├── invoices.py             # Invoicing from treatments, payments, & PDF export
    ├── reports.py              # Financial analytics & reports ("Analyses & Revenus")
    └── settings.py             # Clinic profile configuration & database backup download
```

See [backend/README.md](file:///c:/Users/abess/OneDrive/Desktop/programmation/python/fastapi/backend/README.md) for full endpoint specifications.
