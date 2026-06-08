"""Build verification script for EUB Changes desktop app.

Run this before building the desktop app to confirm digitone_syx_toolkit
is installed and importable in the current environment.

Usage:
    python scripts/verify_desktop_build.py
"""

import sys


def check_digitone_syx_toolkit() -> bool:
    try:
        import digitone_syx_toolkit
        import digitone_syx_toolkit.events_to_syx as ets
        builder = getattr(ets, "build_syx_from_events", None)
        if builder is None:
            print("FAIL: digitone_syx_toolkit.events_to_syx.build_syx_from_events not found")
            return False
        print(f"OK: digitone_syx_toolkit {getattr(digitone_syx_toolkit, '__version__', '(no version)')} — build_syx_from_events available")
        return True
    except ImportError as exc:
        print(f"FAIL: digitone_syx_toolkit import failed: {exc}")
        print("Install with: pip install '.[sysex]'")
        return False


if __name__ == "__main__":
    ok = check_digitone_syx_toolkit()
    sys.exit(0 if ok else 1)
