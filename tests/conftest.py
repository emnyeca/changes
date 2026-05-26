from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

TOOLKIT_SRC = ROOT.parent / "digitone-syx-toolkit" / "src"
if TOOLKIT_SRC.exists() and str(TOOLKIT_SRC) not in sys.path:
    sys.path.insert(0, str(TOOLKIT_SRC))
