"""APART provisionally protected evaluation; no import performs inference."""
from pathlib import Path
import sys
_simulator = str(Path(__file__).resolve().parents[1] / 'simulator')
if _simulator not in sys.path:
    sys.path.insert(0, _simulator)
