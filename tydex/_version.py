from importlib.metadata import PackageNotFoundError, version


def _dist_version() -> str:
    try:
        return version("tydex")
    except PackageNotFoundError:
        return "0.0.0"


__version__ = _dist_version()