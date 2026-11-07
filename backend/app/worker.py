"""Minimal background worker for document processing.

A single daemon thread polls for queued documents. This is deliberate: the architecture doc explains
why a Redis + Celery stack is not justified for a bounded workload (document ingestion only), and the
worker degrades safely if the thread cannot run because uploads also process inline.
"""
from __future__ import annotations

import threading
import time

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.services import ingest

log = get_logger("worker")

_stop = threading.Event()
_thread: threading.Thread | None = None


def run_once() -> int:
    """Process up to a few queued documents. Returns how many were handled."""
    db = SessionLocal()
    handled = 0
    try:
        for document_id in ingest.pending_documents(db, limit=3):
            ingest.process_document(db, document_id)
            handled += 1
    finally:
        db.close()
    return handled


def _loop() -> None:
    log.info("document worker started")
    while not _stop.is_set():
        try:
            handled = run_once()
            if handled == 0:
                _stop.wait(settings.worker_poll_seconds)
        except Exception:  # noqa: BLE001 - worker must not die on a single bad document
            log.exception("worker iteration failed")
            _stop.wait(5.0)
    log.info("document worker stopped")


def start_worker_thread() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="document-worker", daemon=True)
    _thread.start()


def stop_worker_thread() -> None:
    _stop.set()
