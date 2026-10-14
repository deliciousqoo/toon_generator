import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.native_save import save_backup_file


class NativeSaveTests(unittest.TestCase):
    def test_cancel_does_not_write(self):
        with patch("backend.native_save.choose_backup_path", return_value=None):
            self.assertEqual(save_backup_file(b"synthetic", "sample.toonbackup", False), {"saved": False, "cancelled": True})

    def test_only_native_selected_path_is_written_atomically(self):
        root = Path(__file__).resolve().parent.parent / ".test-data"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            target = Path(folder) / "selected.toonbackup"
            target.write_bytes(b"previous-backup")
            with patch("backend.native_save.choose_backup_path", return_value=target):
                result = save_backup_file(b"synthetic-complete-package", "suggestion.toonbackup", False)
            self.assertTrue(result["saved"])
            self.assertEqual(target.read_bytes(), b"synthetic-complete-package")
            self.assertEqual(list(Path(folder).iterdir()), [target])

    def test_interrupted_write_keeps_existing_backup(self):
        root = Path(__file__).resolve().parent.parent / ".test-data"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            target = Path(folder) / "selected.toonbackup"
            target.write_bytes(b"original")
            with patch("backend.native_save.choose_backup_path", return_value=target), patch("backend.native_save.os.replace", side_effect=OSError("synthetic failure")):
                with self.assertRaises(ValueError):
                    save_backup_file(b"new-package", "suggestion.toonbackup", False)
            self.assertEqual(target.read_bytes(), b"original")
            self.assertEqual(list(Path(folder).iterdir()), [target])
