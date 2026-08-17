# Backend Requirements — Dental Clinic Management App

## 1. Project Overview

This is a **fully local, single-user desktop application** for managing a solo dentist's clinic.

- **Backend**: FastAPI (this document covers backend only)
- **Frontend**: Flutter Desktop (built separately, in a different session — not covered here)
- **Database**: SQLite (single local file)
- **Deployment**: Runs entirely on `localhost` on the dentist's own machine. No internet exposure, no remote server, no multi-device sync.
- **Users**: One dentist only. No multi-user roles, no complex authentication needed in this phase.

The backend must be built as a **complete, standalone, testable API** — it should be fully verifiable through FastAPI's built-in Swagger UI (`/docs`) without needing the frontend to exist yet.

---

## 2. Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn (ASGI server)
- SQLAlchemy (ORM)
- Pydantic (request/response validation schemas)
- SQLite (database file, e.g. `clinic.db`)

---

## 3. Recommended Project Structure

```
backend/
├── main.py                # FastAPI app entry point, router registration, CORS setup
├── database.py             # SQLite connection + SQLAlchemy session
├── models.py                # SQLAlchemy ORM models (mirrors schema below)
├── schemas.py                # Pydantic request/response schemas
├── routers/
│   ├── patients.py
│   ├── appointments.py
│   ├── treatments.py
│   ├── invoices.py
│   └── settings.py
├── requirements.txt
└── clinic.db                 # generated SQLite database file
```

---

## 4. Naming & Language Conventions

- **All code identifiers** (table names, column names, variable names, function names, endpoint paths) must be in **English**. This is a coding standard, independent of the app's display language.
- **All clinic-facing data content** (e.g. treatment type names) must be in **French**, since the app's UI and business use are in French.
- API JSON field names stay in English (e.g. `"full_name": "Karim Benali"`), but string *values* representing clinic content (treatment names, etc.) are French.

---

## 5. Database Schema (SQLite)

Use this schema exactly. Create it via SQLAlchemy models that mirror this structure (or run this SQL directly to bootstrap the database).

```sql
PRAGMA foreign_keys = ON;

-- 1. Clinic settings (single row)
CREATE TABLE clinic_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    clinic_name TEXT NOT NULL,
    doctor_name TEXT,
    phone TEXT,
    address TEXT,
    logo_path TEXT,
    daily_patient_limit INTEGER DEFAULT 30
);

-- 2. Patients
CREATE TABLE patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT,
    birth_date DATE,
    gender TEXT CHECK (gender IN ('male', 'female')),
    address TEXT,
    medical_history TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_patients_name ON patients(full_name);
CREATE INDEX idx_patients_phone ON patients(phone);

-- 3. Appointments (simplified day-based booking — see section 6.2)
CREATE TABLE appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_date DATE NOT NULL,
    status TEXT DEFAULT 'booked'
        CHECK (status IN ('booked', 'completed', 'no_show')),
    reason TEXT,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_appointments_date ON appointments(appointment_date);
CREATE INDEX idx_appointments_patient ON appointments(patient_id);

-- 4. Treatment types catalog (French labels)
CREATE TABLE treatment_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    default_price DECIMAL(10,2) DEFAULT 0,
    description TEXT
);

-- 5. Treatments (core of the dental chart / odontogram)
CREATE TABLE treatments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
    treatment_type_id INTEGER NOT NULL REFERENCES treatment_types(id),
    tooth_number INTEGER,  -- FDI notation (11-48), NULL for general treatment
    status TEXT DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed')),
    price DECIMAL(10,2) NOT NULL,
    treatment_date DATE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_treatments_patient ON treatments(patient_id);
CREATE INDEX idx_treatments_tooth ON treatments(patient_id, tooth_number);

-- 6. Invoices
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    invoice_number TEXT UNIQUE,
    invoice_date DATE DEFAULT CURRENT_DATE,
    total_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    paid_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'unpaid'
        CHECK (status IN ('unpaid', 'partially_paid', 'paid')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_invoices_patient ON invoices(patient_id);

-- 7. Invoice line items
CREATE TABLE invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    treatment_id INTEGER REFERENCES treatments(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL
);
CREATE INDEX idx_invoice_items_invoice ON invoice_items(invoice_id);

-- 8. Payments
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_date DATE DEFAULT CURRENT_DATE,
    payment_method TEXT DEFAULT 'cash'
        CHECK (payment_method IN ('cash', 'card', 'transfer', 'other')),
    notes TEXT
);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);

-- Seed data: common treatment types (French)
INSERT INTO treatment_types (name, default_price) VALUES
    ('Consultation', 1000),
    ('Détartrage', 2000),
    ('Plombage', 3000),
    ('Extraction', 2500),
    ('Traitement de canal', 8000),
    ('Couronne dentaire', 15000),
    ('Blanchiment dentaire', 6000);
```

---

## 6. Functional Requirements by Module

### 6.1 Patients
- Full CRUD (create, read, update, delete)
- Search endpoint by name and/or phone (partial match)
- Get a patient's full treatment history
- Get a patient's full invoice/payment history
- `medical_history` is a free-text field but must always be visible/returned prominently since it can contain critical info (allergies, chronic conditions)

### 6.2 Appointments — Simplified Day-Based Booking

This is intentionally **not** a time-slot system. Real clinic workflows are informal; patients are not booked into precise time slots.

- Booking a patient means linking them to a **date only** (no time field exists in the schema — `appointment_date` is `DATE`, not `DATETIME`).
- There is no arrival queue, no check-in status, no ordering logic. The order in which patients are seen on a given day is handled verbally/manually by the dentist — the app does not manage it.
- Each appointment has exactly three possible statuses:
  - `booked` (default, set at creation)
  - `completed` (patient came and was treated)
  - `no_show` (patient did not come)
- Status is updated manually, either right after seeing each patient or in a batch at the end of the day.
- **Endpoints needed**:
  - `GET /appointments?date=YYYY-MM-DD` — list all appointments for a given day
  - `GET /appointments/week?start=YYYY-MM-DD` — list appointments across a week (for the day-picker view, see 6.2.1)
  - `POST /appointments` — create a booking (patient_id + date + optional reason/notes)
  - `PATCH /appointments/{id}` — update status (`completed` / `no_show`) or reschedule the date
  - `DELETE /appointments/{id}` — cancel a booking

#### 6.2.1 Daily Patient Limit (capacity indicator)

- `clinic_settings.daily_patient_limit` holds a configurable soft cap (default 30), editable by the dentist at any time via the settings endpoint.
- When fetching appointment counts per day (e.g. for a week view used during booking), the API must return, for each date: the number of patients already booked and the configured limit, so the frontend can compute a fill ratio and color-code it (green / yellow / red — this logic lives in the frontend, the backend just needs to expose the raw counts and the limit).
- **This limit is advisory only — it must never block a booking.** `POST /appointments` must always succeed regardless of how many patients are already booked that day. The API may optionally return a `warning: true` flag in the response if the day is at or above the limit, so the frontend can show a confirmation dialog, but this must not prevent the write.
- Suggested endpoint: `GET /appointments/capacity?start=YYYY-MM-DD&days=7` → returns per-day `{date, booked_count, limit}` for a week range.

### 6.3 Treatments (Odontogram)
- Full CRUD for treatments
- Each treatment is linked to a patient, optionally a tooth number (FDI notation 11–48, nullable for general/non-tooth-specific treatments), a treatment type, a status (`planned` / `in_progress` / `completed`), a price, and a date
- `GET /patients/{id}/treatments` — full treatment history for a patient, useful to reconstruct their odontogram state (latest status per tooth)
- `GET /treatments?status=planned` — list all treatments still pending across all patients (used for the dashboard's "pending treatments" count)
- Treatment type catalog (`treatment_types`) needs its own CRUD endpoints (`/treatment-types`) so the dentist can add/edit/remove types and adjust default prices from a settings screen. Seed data must be in French (see schema above).

### 6.4 Invoices & Payments
- `POST /invoices` — create an invoice from one or more completed treatments for a patient (the endpoint should accept a list of `treatment_id`s, pull their prices, create `invoice_items`, and compute `total_amount`)
- `POST /invoices/{id}/payments` — register a payment (full or partial) against an invoice; must update `paid_amount` and recompute `status` (`unpaid` / `partially_paid` / `paid`) automatically
- `GET /patients/{id}/invoices` — full invoice/payment history for a patient
- `GET /invoices/{id}` — full invoice detail with line items and payments
- **Out of scope for this phase**: PDF generation/export. Do not build this now — it is planned for a later phase. However, structure the invoice data endpoints cleanly (return complete, well-structured invoice objects) so a future PDF export feature can reuse them without rework.

### 6.5 Dashboard
A single endpoint (or a small set) providing at-a-glance daily stats:
- `GET /dashboard/today` → returns: number of patients booked today, number completed, number no-show, today's total income (sum of payments made today), count of treatments with status `planned` that have no future appointment linked yet (pending follow-ups needing scheduling)

### 6.6 Settings
- `GET /settings` / `PUT /settings` — clinic info (name, doctor name, phone, address, logo path) and `daily_patient_limit`
- `treatment_types` CRUD as described in 6.3

### 6.7 Backup
- Not a full automated system in this phase. It is enough to ensure the SQLite database lives at a clearly documented, predictable file path so the dentist (or a simple future script) can copy it manually for backup purposes. No dedicated endpoint required unless trivial to add (e.g. an optional `GET /backup` that returns the raw `.db` file as a download).

---

## 7. API Design Guidelines

- Follow REST conventions consistently across all routers (see the patterns above for each module).
- Use Pydantic schemas for all request bodies and response models — do not return raw SQLAlchemy objects directly.
- Validate foreign keys exist before insert (e.g. reject creating an appointment for a non-existent `patient_id` with a clear 404/400 error).
- Return `404` for missing records, `400` for invalid input (e.g. invalid status value), with clear JSON error messages (`{"detail": "..."}`).
- No authentication is required in this phase (local single-user app). Leave the code structured so an auth layer could be added later without a major rewrite, but do not implement it now.

---

## 8. CORS Configuration (mandatory, from the very first commit)

Even though both frontend and backend run on the same machine, they run on different origins (different ports), so CORS must be enabled from the start — otherwise Flutter Desktop will be unable to reach the API at all, and this is a common source of confusing early-stage errors.

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # safe here: app is localhost-only, never exposed externally
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 9. Explicitly Out of Scope for This Phase

Do not build any of the following now — they are planned for a later phase:
- PDF invoice export
- Inventory management
- Notifications / reminders
- Multi-user authentication / roles
- Advanced analytics or charts beyond the basic dashboard endpoint
- Automated/scheduled backups

---

## 10. Deliverable Expectations

- A fully working FastAPI backend, runnable via `uvicorn main:app --reload`
- SQLite database created automatically from the schema on first run (via SQLAlchemy `create_all()` or an init script), including the seed data for `treatment_types` and a default row in `clinic_settings`
- Every endpoint testable and working through Swagger UI (`http://localhost:8000/docs`)
- Basic, consistent error handling across all routers
- A short `README.md` inside `backend/` explaining how to install dependencies and run the server

---

## 11. Build Phases

This backend must be built **incrementally, one phase at a time**, not all at once. After finishing each phase, stop and wait for explicit confirmation before starting the next one — do not proceed automatically even if the next phase seems obvious.

1. **Project Setup** — folder structure (section 3), database connection, table creation from the schema (section 5) including seed data, CORS middleware (section 8)
2. **Patients module** — models, schemas, full CRUD + search endpoints
3. **Appointments module** — day-based booking logic, status updates, capacity/limit endpoints (section 6.2)
4. **Treatments module** — treatment CRUD, tooth-linked records, treatment_types catalog CRUD (section 6.3)
5. **Invoices & Payments module** — invoice creation from treatments, payment registration, status computation (section 6.4)
6. **Dashboard & Settings module** — dashboard endpoint (section 6.5), clinic settings CRUD (section 6.6)
7. **Final review** — consistent error handling across all routers, README.md, full manual test pass via `/docs`

Each phase should build only on what already exists from previous phases — do not implement functionality belonging to a later phase early.
