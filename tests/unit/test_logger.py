import logging

import src.core.logger as logger_module
from src.core.logger import Logger, get_logger, configure_logging
from data.config import LoggingConfig


def test_get_logger_wraps_distinct_named_loggers():
    a = get_logger("alpha")
    b = get_logger("beta")
    assert isinstance(a, Logger)
    assert a._log.name == "alpha"
    assert b._log.name == "beta"
    assert a._log is not b._log


def test_get_logger_same_name_shares_stdlib_logger():
    # stdlib logging.getLogger returns a singleton per name
    assert get_logger("shared")._log is get_logger("shared")._log


def test_facade_forwards_to_stdlib(caplog):
    log = get_logger("facade.test")
    with caplog.at_level(logging.DEBUG, logger="facade.test"):
        log.info("hello %s", "world")
    assert "hello world" in caplog.text


def test_configure_logging_is_idempotent(tmp_path, monkeypatch):
    # Reset module + root state so the test is isolated.
    monkeypatch.setattr(logger_module, "_configured", False)
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    root.handlers.clear()
    try:
        cfg = LoggingConfig(file_path=str(tmp_path / "game.log"))
        configure_logging(cfg)
        count_after_first = len(root.handlers)
        configure_logging(cfg)  # second call must be a no-op
        assert len(root.handlers) == count_after_first
        assert count_after_first == 2  # console + rotating file
    finally:
        root.handlers[:] = original_handlers


def test_configure_logging_writes_to_file(tmp_path, monkeypatch):
    monkeypatch.setattr(logger_module, "_configured", False)
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    root.handlers.clear()
    try:
        log_path = tmp_path / "out.log"
        cfg = LoggingConfig(file_path=str(log_path), file_level="DEBUG", level="DEBUG")
        configure_logging(cfg)

        get_logger("write.test").debug("persisted line")
        for handler in root.handlers:
            handler.flush()

        assert log_path.exists()
        assert "persisted line" in log_path.read_text(encoding="utf-8")
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = original_handlers
        root.setLevel(original_level)
