# 🦷 Dental Clinic Management System — Backend API

A **FastAPI backend** for dental clinic management. Designed to be consumed by a Flutter Desktop frontend via REST API.

![Tech Stack](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Dashboard** | Live KPI stats (patients, appointments, upcoming) |
| **Patients** | Full CRUD with search by name/phone |
| **Appointments** | Filterable by date, status, and procedure type; schedule / edit / cancel |
| **Today's Schedule** | Appointments for the current day with status management |
| **Patient Chart** | Demographics, appointment history, and clinical notes |
| **Medical Notes** | Create and retrieve clinical notes per patient |
| **Seed Data** | Demo dataset for development and testing |

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────┐
│  Flutter Desktop UI  (separate project)            │
├────────────────────────────────────────────────────┤
│  HTTP / REST  (JSON)                               │
├────────────────────────────────────────────────────┤
│  FastAPI Backend  (ASGI / Uvicorn)                 │
│  backend/                                          │
│    ├── routers/    (patients, appointments, notes)  │
│    ├── services/   (business logic)                │
│    ├── models/     (SQLAlchemy ORM)                │
│    └── schemas/    (Pydantic v2)                   │
├────────────────────────────────────────────────────┤
│  SQLite database  (data/clinic.db)                 │
└────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or later

### Installation

```bash
# Clone or download the project
cd dental-clinic

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Run

```bash
python run.py
```

The launcher will:
1. Create the SQLite database schema
2. Seed demo data on first launch
3. Start the FastAPI backend on `http://127.0.0.1:8000`

### API Documentation

While the server is running, open your browser at:
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

---

## 📁 Project Structure

```
.
├── run.py                          # Backend launcher
├── requirements.txt
├── test_backend.py                 # Integration tests
├── data/
│   └── clinic.db                   # SQLite database (auto-created)
└── backend/
    ├── config.py
    ├── database.py
    ├── main.py                     # FastAPI app
    ├── models/
    │   ├── patient.py
    │   ├── appointment.py
    │   ├── medical_note.py
    │   └── enums.py
    ├── schemas/schemas.py
    ├── routers/
    │   ├── patients.py
    │   ├── appointments.py
    │   ├── medical_notes.py
    │   └── dashboard.py
    └── services/
        ├── patient_service.py
        ├── appointment_service.py
        └── seed_data.py
```

---

## 🔌 API Endpoints

```
GET    /api/health                          Health check
GET    /api/version                         App version & build info
POST   /api/seed?force=false                Seed demo data

GET    /api/patients?search=...             List / search patients
GET    /api/patients/{id}                   Patient detail with chart
POST   /api/patients                        Create patient
PUT    /api/patients/{id}                   Update patient
DELETE /api/patients/{id}                   Delete patient

GET    /api/appointments?date=&status=&type=  List appointments
GET    /api/appointments/today              Today's appointments
POST   /api/appointments                    Create appointment
PUT    /api/appointments/{id}               Update appointment
DELETE /api/appointments/{id}               Delete appointment

GET    /api/patients/{id}/medical-notes     Patient's medical notes
POST   /api/patients/{id}/medical-notes     Add medical note

GET    /api/dashboard/stats                 Dashboard statistics
```

---

## 🧪 Running Tests

```bash
python test_backend.py
```

All 5 integration tests cover: seeding, dashboard stats, patient CRUD, medical notes, and appointment lifecycle.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| HTTP API | [FastAPI](https://fastapi.tiangolo.com) 0.115+ |
| ASGI server | Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Validation | Pydantic v2 |
| Database | SQLite 3 |
| HTTP client | requests (tests) |

---

## 📄 License

MIT — free to use and modify for personal or commercial purposes.
