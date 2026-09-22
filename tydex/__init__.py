from .autocal import AutoCalibrator
from .backends import (
    AnthropicCompatibleBackend,
    Backend,
    LocalOpenAIBackend,
    MockBackend,
    OllamaBackend,
    OpenAIBackend,
    OpenAICompatibleBackend,
)
from .calibrated import CalibratedTydex, CalibrationSystem, IsotonicCalibrator
from .calibration import (
    CalibrationResult,
    Metrics,
    calibrate_temperature,
    tune_temperature,
)
from .core import ChoiceResult, NoulResult, SchemaError, ScoreResult, Tydex
from .feedback import LogEntry, Recorder
from .routing import RequiresHuman, RoutedResult, RoutedTydex, Tier

_SERVER_EXPORTS = {"TydexServer", "RoutedTydexServer", "build_server", "run"}


def __getattr__(name):
    if name in _SERVER_EXPORTS:
        from . import server

        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnthropicCompatibleBackend",
    "AutoCalibrator",
    "Backend",
    "CalibratedTydex",
    "CalibrationResult",
    "CalibrationSystem",
    "ChoiceResult",
    "IsotonicCalibrator",
    "LocalOpenAIBackend",
    "LogEntry",
    "Metrics",
    "MockBackend",
    "NoulResult",
    "OllamaBackend",
    "OpenAIBackend",
    "OpenAICompatibleBackend",
    "Recorder",
    "RequiresHuman",
    "RoutedResult",
    "RoutedTydex",
    "RoutedTydexServer",
    "SchemaError",
    "ScoreResult",
    "Tier",
    "Tydex",
    "TydexServer",
    "build_server",
    "calibrate_temperature",
    "run",
    "tune_temperature",
]