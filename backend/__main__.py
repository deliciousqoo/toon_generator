"""Desktop launcher target; browser UI and service share a loopback origin."""
import argparse
import json
import threading
import urllib.error
import urllib.request
import webbrowser

import uvicorn

from .app import create_app


def main():
    parser = argparse.ArgumentParser(description="Toon Studio synthetic-only local MVP")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--stop", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a port between 1024 and 65535.")
    url = f"http://127.0.0.1:{args.port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url + "/api/health", timeout=2) as response:
            health = json.load(response)
        if health.get("app") != "toon-studio" or health.get("mode") != "platform_build":
            raise RuntimeError("The port belongs to another application.")
        if args.stop:
            with opener.open(url + "/api/bootstrap", timeout=2) as response:
                token = json.load(response)["csrf_token"]
            request = urllib.request.Request(url + "/api/shutdown", method="POST", data=b"", headers={"X-CSRF-Token": token})
            with opener.open(request, timeout=5):
                pass
        elif not args.no_browser:
            webbrowser.open(url)
        return
    except urllib.error.HTTPError:
        raise RuntimeError("The existing local service rejected the launch or stop request.") from None
    except (urllib.error.URLError, TimeoutError):
        if args.stop:
            return
    app = create_app(args.data_root, port=args.port, dev=args.dev)
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=args.port, access_log=False, proxy_headers=False, log_level="warning"))
    app.state.shutdown_callback = lambda: setattr(server, "should_exit", True)
    if not args.no_browser:
        def ready():
            import time
            for _ in range(100):
                if server.started:
                    webbrowser.open(url)
                    return
                if server.should_exit:
                    return
                time.sleep(0.1)
        threading.Thread(target=ready, daemon=True).start()
    server.run()


if __name__ == "__main__":
    main()
