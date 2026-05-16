"""
ModelRegistry — zero-downtime replacement of ForecasterEnsemble.

Principle:
  - _active  — current ensemble, used for predictions (readonly).
  - _staging — new ensemble, created in the background during retraining.
  - promote() — atomically replace _active with _staging using asyncio.Lock.

Predictions (predict) take _active without blocking - readonly operation is safe with concurrent queries because Python GIL and reference immutability guarantee consistency of ensemble image during the call.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.ml.models.forecaster_ensemble import ForecasterEnsemble

logger = logging.getLogger(__name__)


class ModelRegistry:
    def __init__(self) -> None:
        self._active: Optional[ForecasterEnsemble] = None
        self._staging: Optional[ForecasterEnsemble] = None
        self._lock: asyncio.Lock = asyncio.Lock()
        self._version: str = "none"
        self._retraining: bool = False

    # ── Read (non blocking) ─────────────────────────────────────────────
    @property
    def active(self) -> Optional[ForecasterEnsemble]:
        return self._active

    @property
    def version(self) -> str:
        return self._version

    @property
    def retraining(self) -> bool:
        return self._retraining

    def is_ready(self) -> bool:
        return self._active is not None

    # ── Init at start ────────────────────────────────────────────
    async def load_from_disk(self, path: str) -> None:
        """Загрузить сохранённый ансамбль при старте контейнера."""
        ensemble = ForecasterEnsemble.load(path)  # см. 3.5
        async with self._lock:
            self._active = ensemble
            self._version = self._read_version(path)
        logger.info("Model loaded from %s (version=%s)", path, self._version)

    # ── Переобучение и атомарная подмена ───────────────────────────────────
    async def begin_retraining(self) -> bool:
        """Returns False if retraining has already begun."""
        async with self._lock:
            if self._retraining:
                return False
            self._retraining = True
        return True

    def set_staging(self, ensemble: ForecasterEnsemble) -> None:
        """Called from the training thread (executor) — without await."""
        self._staging = ensemble

    async def promote(self, version: str) -> None:
        """Atomically replace _active with _staging."""
        async with self._lock:
            if self._staging is None:
                raise RuntimeError("No staging model to promote")
            self._active = self._staging
            self._staging = None
            self._version = version
            self._retraining = False
        logger.info("Model promoted to version=%s", version)

    async def abort_retraining(self) -> None:
        async with self._lock:
            self._staging = None
            self._retraining = False

    @staticmethod
    def _read_version(path: str) -> str:
        import os, json

        meta = os.path.join(path, "meta.json")
        if os.path.exists(meta):
            with open(meta) as f:
                return json.load(f).get("version", "unknown")
        return datetime.utcnow().strftime("%Y%m%dT%H%M%S")
