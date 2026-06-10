"""Build verification script for EUB Changes desktop app.

Run this before building the desktop app to confirm digitone_syx_toolkit
is installed and importable in the current environment.

Usage:
    python scripts/verify_desktop_build.py
"""

import sys
from pathlib import Path


def check_bundled_ireal_tools() -> bool:
    """Desktop builds bundle the iReal converter; staging must exist before build.

    CI unit tests do not require these files — only the desktop build does.
    """
    repo_root = Path(__file__).resolve().parent.parent
    required = [
        repo_root / "THIRD_PARTY_NOTICES.md",
        repo_root / "tools" / "eub-ireal-wrapper.mjs",
        repo_root / "tools" / "bundled" / "ireal-musicxml" / "build" / "ireal-musicxml.mjs",
        repo_root / "tools" / "bundled" / "node" / "node.exe",
        repo_root / "tools" / "bundled" / "node" / "LICENSE",
    ]
    missing = [p for p in required if not p.is_file()]
    if missing:
        for p in missing:
            print(f"FAIL: required build file missing: {p}")
        print("Stage with: .\\scripts\\PrepareBundledIRealMusicXML.ps1 -IncludeNode")
        return False
    print("OK: THIRD_PARTY_NOTICES.md, bundled ireal-musicxml, node.exe, and node/LICENSE staged")
    return True


def check_digitone_syx_toolkit() -> bool:
    try:
        import digitone_syx_toolkit
        import digitone_syx_toolkit.events_to_syx as ets
        builder = getattr(ets, "build_syx_from_events", None)
        if builder is None:
            print("FAIL: digitone_syx_toolkit.events_to_syx.build_syx_from_events not found")
            return False
        # ASCII only: this runs in consoles that may use cp932, where em-dash fails to encode.
        print(f"OK: digitone_syx_toolkit {getattr(digitone_syx_toolkit, '__version__', '(no version)')} - build_syx_from_events available")
        return True
    except ImportError as exc:
        print(f"FAIL: digitone_syx_toolkit import failed: {exc}")
        print("Install with: pip install '.[sysex]'")
        return False


if __name__ == "__main__":
    ok = check_digitone_syx_toolkit()
    ok = check_bundled_ireal_tools() and ok
    sys.exit(0 if ok else 1)
