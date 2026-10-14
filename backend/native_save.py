"""Native save-location selection for browsers without File System Access API."""
import ctypes
import os
import tempfile
from pathlib import Path


def choose_backup_path(suggested_name, encrypted):
    if os.name != "nt":
        raise ValueError("이 브라우저에서는 Windows 저장 창 또는 파일 저장 API를 지원하는 브라우저를 사용해주세요.")
    from ctypes import wintypes

    class OpenFileName(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD), ("hwndOwner", wintypes.HWND), ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR), ("lpstrCustomFilter", wintypes.LPWSTR), ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD), ("lpstrFile", wintypes.LPWSTR), ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR), ("nMaxFileTitle", wintypes.DWORD), ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR), ("Flags", wintypes.DWORD), ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD), ("lpstrDefExt", wintypes.LPCWSTR), ("lCustData", ctypes.c_ssize_t),
            ("lpfnHook", ctypes.c_void_p), ("lpTemplateName", wintypes.LPCWSTR), ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD), ("FlagsEx", wintypes.DWORD),
        ]
    filename = ctypes.create_unicode_buffer(suggested_name, 32768)
    options = OpenFileName()
    options.lStructSize = ctypes.sizeof(OpenFileName)
    options.lpstrFile = ctypes.cast(filename, wintypes.LPWSTR)
    options.nMaxFile = len(filename)
    options.nFilterIndex = 1
    options.lpstrFilter = "Toon Studio encrypted backup\0*.toonbackup.age\0\0" if encrypted else "Toon Studio project backup\0*.toonbackup\0\0"
    options.lpstrDefExt = "toonbackup.age" if encrypted else "toonbackup"
    options.lpstrTitle = "Toon Studio · 백업 저장 위치"
    options.Flags = 0x00000002 | 0x00000008 | 0x00000800 | 0x00080000  # overwrite confirmation, no cwd change, existing parent, Explorer
    dialog = ctypes.windll.comdlg32
    dialog.GetSaveFileNameW.argtypes = [ctypes.POINTER(OpenFileName)]
    dialog.GetSaveFileNameW.restype = wintypes.BOOL
    if not dialog.GetSaveFileNameW(ctypes.byref(options)):
        if dialog.CommDlgExtendedError() != 0:
            raise ValueError("저장 창을 열지 못했습니다. 파일 저장 API를 지원하는 브라우저에서 다시 시도해주세요.")
        return None
    return Path(filename.value)


def save_backup_file(data, filename, encrypted):
    """Only the native user-selected path is writable; browsers cannot supply it."""
    selected = choose_backup_path(filename, encrypted)
    if selected is None:
        return {"saved": False, "cancelled": True}
    selected = selected.resolve()
    if not selected.parent.is_dir():
        raise ValueError("선택한 저장 폴더를 찾을 수 없습니다.")
    if os.name == "nt" and not str(selected).startswith("\\\\?\\"):
        selected = Path("\\\\?\\UNC\\" + str(selected)[2:]) if str(selected).startswith("\\\\") else Path("\\\\?\\" + str(selected))
    descriptor, temporary = tempfile.mkstemp(prefix=".toon-backup-", suffix=".tmp", dir=selected.parent)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, selected)
    except OSError:
        raise ValueError("백업 파일을 저장하지 못했습니다. 기존 파일은 보존하고 다시 내보내주세요.") from None
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"saved": True, "cancelled": False, "filename": selected.name}
