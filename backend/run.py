import sys
import os
from pathlib import Path

# Packaged mode: add _internal/backend to path
if hasattr(sys, 'MEIPASS'):
    _internal = Path(sys.executable).parent / '_internal'
    sys.path.insert(0, str(_internal / 'backend'))
    os.chdir(_internal)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
