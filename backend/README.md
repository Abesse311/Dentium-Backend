# 🦷 Dental Clinic Management System — Backend API

A complete, standalone, production-ready **FastAPI local backend** with **SQLite** for the Dental Clinic Management Desktop Application.

---

## 📋 Table of Contents
- [Tech Stack](#-tech-stack)
- [Project Architecture & Structure](#-project-architecture--structure)
- [Quick Start](#-quick-start)
- [Interactive API Documentation](#-interactive-api-documentation)
- [REST API Endpoints Inventory](#-rest-api-endpoints-inventory)
- [Database Schema](#-database-schema)
- [Running Automated Tests](#-running-automated-tests)

---

## 🛠 Tech Stack
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
- **ORM**: [SQLAlchemy 2.0](https://www.sqlalchemy.org/)
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
- **Database**: SQLite 3 (`clinic.db`) with active Foreign Keys (`PRAGMA foreign_keys = ON`)
- **CORS**: Fully configured for cross-origin Flutter Desktop client connectivity

---

## 🏗 Project Architecture & Structure

```
backend/
├── __init__.py
├── main.py                     # FastAPI app, lifespan setup, router mounting, CORS middleware
├── database.py                  # SQLite engine, sessionmaker, Base, foreign key listener, init_db()
├── models.py                   # SQLAlchemy ORM models (all 8 tables)
├── schemas.py                  # Pydantic v2 request/response schemas
├── requirements.txt            # Python dependencies
├── README.md                   # Backend documentation
├── clinic.db                   # Generated SQLite database file
└── routers/
    ├── __init__.py
    ├── dashboard.py            # Daily KPIs, income, pending treatments follow-up
    ├── patients.py             # Patient CRUD, partial search, treatment/invoice history
    ├── appointments.py         # Day-based bookings, week calendar, capacity fill ratios
    ├── treatments.py           # Treatments CRUD (FDI notation 11-48) & Treatment Types catalog
    ├── invoices.py             # Invoicing from treatments, partial/full payment lifecycle
    └── settings.py             # Clinic profile, capacity limits, database backup download
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.11 or later

### 2. Installation
Create and activate a virtual environment, then install dependencies:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt
```

### 3. Run the Server
From the workspace root:
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Or from inside `backend/`:
```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

---

## 📖 Interactive API Documentation
Once the server is running, navigate in your browser to:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 🔌 REST API Endpoints Inventory

### 📊 Dashboard
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard/today` | Real-time KPIs for today: booked, completed, no-show, revenue, pending treatments, and agenda |

### 👤 Patients
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/patients` | Create a new patient record |
| `GET` | `/api/patients` | List/search patients (supports `?search=...`, pagination) |
| `GET` | `/api/patients/{id}` | Get full patient profile and medical history |
| `PUT`/`PATCH` | `/api/patients/{id}` | Update patient details |
| `DELETE` | `/api/patients/{id}` | Delete patient (cascades to appointments, treatments, invoices) |
| `GET` | `/api/patients/{id}/treatments` | Get patient's full chronological treatment history |
| `GET` | `/api/patients/{id}/invoices` | Get patient's full invoice and payment history |

### 📅 Appointments (Day-Based Booking)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/appointments` | Book an appointment for a specific date (advisory capacity warning) |
| `GET` | `/api/appointments` | List appointments (filter by `?date=`, `?patient_id=`, `?status=`) |
| `GET` | `/api/appointments/week` | Retrieve all bookings across a 7-day window from `?start=` |
| `GET` | `/api/appointments/capacity` | Get daily booked counts, limits, and fill ratios for frontend color coding |
| `GET` | `/api/appointments/{id}` | Get single appointment details |
| `PATCH`/`PUT` | `/api/appointments/{id}` | Update status (`booked`, `completed`, `no_show`) or reschedule date |
| `DELETE` | `/api/appointments/{id}` | Cancel/delete an appointment booking |

### 🦷 Treatments & Odontogram
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/treatments` | Record a clinical treatment (FDI tooth notation 11–48 or general) |
| `GET` | `/api/treatments` | List treatments (filter by `?status=planned`, `?patient_id=`, `?tooth_number=`) |
| `GET` | `/api/treatments/{id}` | Get single treatment details |
| `PATCH`/`PUT` | `/api/treatments/{id}` | Update status (`planned`, `in_progress`, `completed`), tooth, or price |
| `DELETE` | `/api/treatments/{id}` | Delete a treatment record |

### 🏷 Treatment Types (French Catalog: Général / Par dent)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/treatment-types` | List procedure types in the catalog (filter by `?category=general` or `?category=per_tooth`) |
| `POST` | `/api/treatment-types` | Add a new procedure type (requires `category`: `'general'` or `'per_tooth'`) |
| `GET` | `/api/treatment-types/{id}` | Get procedure type details |
| `PUT`/`PATCH` | `/api/treatment-types/{id}` | Update procedure category, name, default price, or description |
| `DELETE` | `/api/treatment-types/{id}` | Delete procedure type (protected against in-use procedures) |

### 💳 Invoices & Payments
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/invoices` | Generate invoice from completed treatments |
| `GET` | `/api/invoices` | List invoices (filter by `?status=`, `?patient_id=`, date ranges) |
| `GET` | `/api/invoices/{id}` | Get full invoice with line items and registered payments |
| `DELETE` | `/api/invoices/{id}` | Delete an invoice |
| `POST` | `/api/invoices/{id}/payments` | Register payment against invoice (auto-updates `unpaid` → `partially_paid` → `paid`) |
| `GET` | `/api/invoices/{id}/payments` | List all payments for an invoice |
| `DELETE` | `/api/payments/{id}` | Delete payment (auto-recalculates invoice balance and rolls back status) |

### ⚙ Settings & System
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/settings` | Retrieve clinic profile and daily patient limit |
| `PUT`/`PATCH` | `/api/settings` | Update clinic profile and daily limit |
| `GET` | `/api/settings/backup` | Download raw `clinic.db` file backup |
| `GET` | `/api/health` | System health check and database connectivity verification |

---

## 🗄 Database Schema

The SQLite schema consists of 8 interconnected tables with enforced foreign keys:
1. `clinic_settings` — Single-row (`id = 1`) clinic profile and capacity preferences.
2. `patients` — Patient records with search indexes on name and phone.
3. `appointments` — Day-based bookings with status (`booked`, `completed`, `no_show`).
4. `treatment_types` — French procedure catalog with default DZD pricing.
5. `treatments` — Clinical dental records linked to FDI tooth numbers (11–48) and status (`planned`, `in_progress`, `completed`).
6. `invoices` — Billing records with auto-calculated `total_amount`, `paid_amount`, and status (`unpaid`, `partially_paid`, `paid`).
7. `invoice_items` — Line items linked to treatments.
8. `payments` — Payment records linked to invoices.

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
py run_tests.py
```
