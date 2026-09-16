from __future__ import annotations

import sys
from pathlib import Path


ML_ENGINE_ROOT = Path(__file__).resolve().parents[1]
if str(ML_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ENGINE_ROOT))
