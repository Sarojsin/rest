"""FCM outbox worker — drains outbox_events and sends push notifications.

Run as a standalone process:

    backend\\venv\\Scripts\\python.exe backend\\run_fcm_worker.py

Options:
    --poll-interval  Seconds between polls (default: 5)
    --batch-size     Max events per poll (default: 100)

The worker keeps running until it receives SIGINT/SIGTERM. It uses the same
SQLAlchemy session factory as the API, so no extra database setup is needed.
"""

from __future__ import annotations

import argparse
import logging
import signal
import threading
import time

from app.core.config import settings
from app.db.session import SessionLocal
from app.modules.notifications.services.fcm import process_outbox

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 100


class FCMOutboxWorker:
    """Polls outbox_events and delivers them as FCM notifications."""

    def __init__(self, poll_interval: int = POLL_INTERVAL_SECONDS,
                 batch_size: int = BATCH_SIZE) -> None:
        self.poll_interval = poll_interval
        self.batch_size = batch_size
        self._running = False

    def stop(self) -> None:
        self._running = False

    def run_once(self) -> None:
        """Process one batch of outbox events."""
        db = SessionLocal()
        try:
            processed = process_outbox(db, limit=self.batch_size)
            if processed:
                logger.info("Processed %d outbox events", processed)
        finally:
            db.close()

    def run(self) -> None:
        """Run the polling loop until stopped."""
        self._running = True
        logger.info(
            "FCM outbox worker starting (poll_interval=%ds, batch_size=%d)",
            self.poll_interval,
            self.batch_size,
        )

        # Signal handlers only work in the main thread. When run as a daemon
        # thread inside the API process, skip them (the process handles
        # shutdown signals itself).
        if threading.current_thread() is threading.main_thread():
            def handle_signal(signum, frame) -> None:
                logger.info("Received signal %s, shutting down...", signum)
                self.stop()

            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)

        while self._running:
            try:
                self.run_once()
            except Exception:  # noqa: BLE001 — keep polling on transient errors
                logger.exception("Worker loop iteration failed")
            time.sleep(self.poll_interval)

        logger.info("FCM outbox worker stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="FCM outbox worker")
    parser.add_argument("--poll-interval", type=int, default=POLL_INTERVAL_SECONDS,
                        help="Seconds between polls (default: 5)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                        help="Max events per poll (default: 100)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    worker = FCMOutboxWorker(
        poll_interval=args.poll_interval,
        batch_size=args.batch_size,
    )
    worker.run()


if __name__ == "__main__":
    main()
