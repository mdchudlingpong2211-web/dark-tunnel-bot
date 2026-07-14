"""Process entrypoint.

Runs the Telegram bot with an outer auto-restart loop: if the Pyrogram
client crashes or loses connection unexpectedly, the process logs the
failure and restarts the client with a short backoff instead of exiting.
Combine this with a process manager / platform restart policy (see
README.md) for full resilience.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.bot import create_bot
from app.config import ConfigError, configure_logging, validate

logger = logging.getLogger(__name__)

MAX_BACKOFF_SECONDS = 60
INITIAL_BACKOFF_SECONDS = 3


def start_health_server() -> None:
    """Run a tiny HTTP server so uptime monitors can keep this Repl awake."""
    port = int(os.environ.get("PORT", 8082))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):  # silence access logs
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health server listening on port %s", port)


def main() -> None:
    configure_logging()
    try:
        validate()
    except ConfigError as exc:
        logger.critical("Configuration error: %s", exc)
        raise SystemExit(1) from exc

    start_health_server()

    backoff = INITIAL_BACKOFF_SECONDS
    while True:
        try:
            logger.info("Starting bot...")
            bot = create_bot()
            bot.run()
            # bot.run() returning normally means a clean shutdown was requested.
            logger.info("Bot stopped cleanly.")
            break
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user.")
            break
        except Exception:  # noqa: BLE001 - top-level auto-restart guard
            logger.exception("Bot crashed. Restarting in %s seconds...", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF_SECONDS)
        else:
            backoff = INITIAL_BACKOFF_SECONDS


if __name__ == "__main__":
    main()
