"""Windowless desktop entry point for Toon Studio's loopback-only service."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _dialog(message: str) -> None:
    # MessageBox requires no additional dependency, console, or running Tk loop.
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "Toon Studio", 0x10)
    except (AttributeError, OSError):
        try:
            import tkinter
            from tkinter import messagebox
            window = tkinter.Tk()
            window.withdraw()
            messagebox.showerror("Toon Studio", message, parent=window)
            window.destroy()
        except Exception:
            pass


def main() -> int:
    source_root = Path(__file__).resolve().parent
    os.chdir(source_root)
    sys.path.insert(0, str(source_root))
    # Uvicorn checks standard streams during logger initialization. pythonw has
    # none; discard service output rather than creating logs with user inputs.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    try:
        if "--stop" not in sys.argv and not (source_root / "frontend" / "dist" / "index.html").is_file():
            _dialog("The Toon Studio browser interface has not been built.\n\nRun scripts/Install-ToonStudio.ps1, then open Toon Studio again.")
            return 1
        from backend.__main__ import main as run_service
        run_service()
        return 0
    except ImportError:
        _dialog("Toon Studio dependencies are missing.\n\nRun scripts/Install-ToonStudio.ps1, then open Toon Studio again.")
        return 1
    except SystemExit as error:
        if error.code not in (None, 0):
            _dialog("Toon Studio could not start. Check that its port is free and the launch arguments are valid.\n\nThe default address is http://127.0.0.1:8765.")
            return 1
        return 0
    except Exception:
        _dialog("Toon Studio could not start.\n\nCheck that the local data folder is accessible and port 8765 is free. If dependencies were changed, run scripts/Install-ToonStudio.ps1 again.\n\nNo project files were deleted.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
