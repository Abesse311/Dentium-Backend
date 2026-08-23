"""
Entry point for Dentium Backend server.
Used by PyInstaller to build standalone Windows executable.
"""
import multiprocessing
import os
import sys
import uvicorn

if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Ensure project root is in sys.path
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    from backend.main import app

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        access_log=False,
    )
