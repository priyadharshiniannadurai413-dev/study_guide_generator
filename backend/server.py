import os
import sys
import subprocess

# Ensure server executes using the project virtual environment where all dependencies are installed
_venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe"))
if os.path.exists(_venv_python) and os.path.abspath(sys.executable).lower() != _venv_python.lower():
    sys.exit(subprocess.call([_venv_python] + sys.argv))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
