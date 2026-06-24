from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATEFMT = "%H:%M:%S"
_configured = False


class Logger:
    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def debug(self, msg: str, *args) -> None:
        self._log.debug(msg, *args)

    def info(self, msg: str, *args) -> None:
        self._log.info(msg, *args)

    def warning(self, msg: str, *args) -> None:
        self._log.warning(msg, *args)

    warn = warning

    def error(self, msg: str, *args) -> None:
        self._log.error(msg, *args)

    def exception(self, msg: str, *args) -> None:
        self._log.exception(msg, *args)


def get_logger(name: str) -> Logger:
    return Logger(name)


def configure_logging(cfg) -> None:
    """Install console + rotating-file handlers on the root logger. Idempotent."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    root.setLevel(getattr(logging, cfg.level))
    fmt = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler()
    console.setLevel(getattr(logging, cfg.console_level))
    console.setFormatter(fmt)
    root.addHandler(console)

    Path(cfg.file_path).parent.mkdir(parents=True, exist_ok=True)
    file = RotatingFileHandler(
        cfg.file_path,
        maxBytes=cfg.max_bytes,
        backupCount=cfg.backup_count,
        encoding="utf-8",
    )
    file.setLevel(getattr(logging, cfg.file_level))
    file.setFormatter(fmt)
    root.addHandler(file)
    _configured = True
