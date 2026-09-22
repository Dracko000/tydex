from __future__ import annotations

import os
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .calibrated import CalibratedTydex, CalibrationSystem
from .core import Tydex
from .feedback import Recorder


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AutoCalibrator:
    def __init__(
        self,
        recorder: Recorder | None = None,
        *,
        refit_every: int = 100,
        refit_every_seconds: float | None = None,
        min_samples: int = 8,
        min_ref: int = 30,
        recency_half_life_days: float | None = None,
        on_refit: Callable[[AutoCalibrator], None] | None = None,
        config_path: str = "tydex-calibration.json",
    ) -> None:
        self.system = CalibrationSystem(
            recorder or Recorder(),
            min_samples=min_samples,
            min_ref=min_ref,
            recency_half_life_days=recency_half_life_days,
        )
        self.refit_every = max(1, refit_every)
        self.refit_every_seconds = refit_every_seconds
        self.on_refit = on_refit
        self.config_path = config_path
        self._lock = threading.RLock()
        self.last_refit_ts: str | None = None
        self._baseline = len(self.system.recorder.labeled())
        self.history: list[dict[str, Any]] = []
        self._load_or_initial_fit()

    def _load_or_initial_fit(self) -> None:
        if os.path.exists(self.config_path):
            try:
                self.system.load(self.config_path)
            except (OSError, ValueError, KeyError):
                self._refit()
            return
        if self.system.recorder.labeled():
            self._refit()

    @property
    def recorder(self) -> Recorder:
        return self.system.recorder

    @property
    def pending(self) -> int:
        return len(self.system.recorder.labeled()) - self._baseline

    def label(self, entry_id: str, label: str) -> None:
        self.system.recorder.label(entry_id, label)

    def maybe_refit(self) -> bool:
        with self._lock:
            pending = self.pending
            due_by_count = pending >= self.refit_every
            due_by_time = False
            if self.refit_every_seconds and self.last_refit_ts:
                try:
                    last = datetime.fromisoformat(self.last_refit_ts)
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=timezone.utc)
                    due_by_time = (datetime.now(timezone.utc) - last).total_seconds() >= self.refit_every_seconds
                except ValueError:
                    due_by_time = False

            # Drift detection
            drift_detected = False
            for prim in ("choice", "score", "noul"):
                if self.recorder.monitor_drift(prim):
                    drift_detected = True
                    break

            if not (due_by_count or due_by_time or drift_detected):
                return False
            self._refit()
            return True

    def force_refit(self) -> None:
        with self._lock:
            self._refit()

    def refit(self) -> bool:
        with self._lock:
            if not self.system.recorder.labeled():
                return False
            self._refit()
            return True

    def _refit(self) -> None:
        self.system.fit()
        self.system.save(self.config_path)
        self._baseline = len(self.system.recorder.labeled())
        self.last_refit_ts = _now()
        self.history.append(
            {
                "ts": self.last_refit_ts,
                "labeled": self._baseline,
                "meta": {prim: dict(meta) for prim, meta in self.system.meta.items()},
            }
        )
        if self.on_refit:
            self.on_refit(self)

    def apply_to(self, tdex: Tydex) -> CalibratedTydex:
        return CalibratedTydex(tdex, self.system)

    def status(self) -> dict[str, Any]:
        return {
            "pending": self.pending,
            "refit_every": self.refit_every,
            "last_refit_ts": self.last_refit_ts,
            "labeled_total": len(self.system.recorder.labeled()),
            "temperatures": self.system.temperatures,
            "meta": self.system.meta,
            "history": self.history,
        }