import os
import sys
import subprocess

# Ensure working directory is set to backend directory
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.exists(_backend_dir):
    os.chdir(_backend_dir)
    if _backend_dir not in sys.path:
        sys.path.insert(0, _backend_dir)

# Explicitly load .env from backend directory before running uvicorn
from dotenv import load_dotenv
_env_file = os.path.join(_backend_dir, ".env")
if os.path.exists(_env_file):
    load_dotenv(_env_file)

# Ensure server executes using the project virtual environment where all dependencies are installed
_venv_python = os.path.abspath(os.path.join(_backend_dir, "venv", "Scripts", "python.exe"))
if os.path.exists(_venv_python) and os.path.abspath(sys.executable).lower() != _venv_python.lower():
    sys.exit(subprocess.call([_venv_python] + sys.argv))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if (os.environ.get("PORT") or os.environ.get("RENDER")) else "127.0.0.1"
    uvicorn.run("app.main:app", host=host, port=port, reload=(not os.environ.get("RENDER")))

