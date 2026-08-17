"""
run.py — Backend server launcher.

Initialises the SQLite database, seeds demo data on first launch,
and starts the FastAPI/Uvicorn server.
"""
import os
import sys
import uvicorn

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config import HOST, PORT, API_BASE_URL, APP_NAME, APP_VERSION
from backend.database import engine, Base, SessionLocal
from backend.services.seed_data import seed_initial_data

# ---------------------------------------------------------------------------
# ANSI color helpers (gracefully disabled on non-ANSI terminals)
# ---------------------------------------------------------------------------
_ANSI = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _ANSI else text

OK   = lambda t: _c("32;1", t)   # bold green
WARN = lambda t: _c("33;1", t)   # bold yellow
ERR  = lambda t: _c("31;1", t)   # bold red
DIM  = lambda t: _c("90",   t)   # dark grey
BOLD = lambda t: _c("1",    t)   # bold

# ---------------------------------------------------------------------------


def main() -> None:
    _sep = "─" * 56
    print(_c("36;1", f"\n  {APP_NAME}"))
    print(DIM(f"  v{APP_VERSION}  •  FastAPI Backend"))
    print(DIM(_sep))

    # 1. Init database
    print(f"  {BOLD('[1/3]')} Initialising SQLite database schema…")
    Base.metadata.create_all(bind=engine)

    # 2. Seed demo data
    print(f"  {BOLD('[2/3]')} Checking demo dataset…")
    db = SessionLocal()
    try:
        result = seed_initial_data(db, force=False)
        if result.get("status") == "success":
            print(f"         {OK('✔')} {result['message']}")
        else:
            print(f"         {DIM('↷')} {result['message']}")
    except Exception as exc:
        print(f"         {WARN('⚠')} Seed check warning: {exc}")
    finally:
        db.close()

    # 3. Start FastAPI backend
    print(f"  {BOLD('[3/3]')} Starting FastAPI backend on {DIM(API_BASE_URL)}…")
    print(DIM(f"         Swagger UI → {API_BASE_URL}/docs"))
    print(DIM(f"         ReDoc      → {API_BASE_URL}/redoc"))
    print(DIM(_sep) + "\n")

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
