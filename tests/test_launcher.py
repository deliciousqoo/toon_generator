import json
import unittest
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

from backend.__main__ import main


class LauncherTests(unittest.TestCase):
    def test_http_error_is_not_mistaken_for_closed_service(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.HTTPError("http://127.0.0.1:8765/api/health", 403, "blocked", {}, None)
        with patch("sys.argv", ["toon", "--stop"]), patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(RuntimeError):
                main()

    def test_stop_when_service_absent_is_safe(self):
        opener = MagicMock()
        opener.open.side_effect = urllib.error.URLError("connection refused")
        with patch("sys.argv", ["toon", "--stop"]), patch("urllib.request.build_opener", return_value=opener), patch("backend.__main__.create_app") as create:
            main()
            create.assert_not_called()

    def test_existing_other_app_is_never_stopped(self):
        opener = MagicMock()
        opener.open.return_value = BytesIO(json.dumps({"app": "other-service"}).encode())
        with patch("sys.argv", ["toon", "--stop"]), patch("urllib.request.build_opener", return_value=opener):
            with self.assertRaises(RuntimeError):
                main()
        self.assertEqual(opener.open.call_count, 1)

    def test_stop_sends_token_only_as_local_header(self):
        opener = MagicMock()
        opener.open.side_effect = [BytesIO(b'{"app":"toon-studio","mode":"platform_build"}'), BytesIO(b'{"csrf_token":"synthetic-test-token"}'), BytesIO(b'{}')]
        with patch("sys.argv", ["toon", "--stop", "--port", "8876"]), patch("urllib.request.build_opener", return_value=opener):
            main()
        request = opener.open.call_args_list[-1].args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8876/api/shutdown")
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("X-csrf-token"), "synthetic-test-token")
        self.assertEqual(request.data, b"")
