# Logger Facade (`src/core/logger.py`) — Report & Guide

## 1. What it is

`logger.py` is a small **facade over the stdlib `logging` module**. It exists so the rest of the code never touches `logging` directly: modules call `get_logger(__name__)` to get a logger, and `main.py` calls `configure_logging(...)` once at boot to install the handlers. That keeps logging setup in one place and gives every module a uniform, swappable logging surface.

It replaced the old habit of bare `except Exception: pass` swallowing errors silently — now failures go through a logger and land in a rotating file (see `save_manager_report.md`, which logs on save failure).

Three public names:
- **`Logger`** — the wrapper class (`debug/info/warning/error/exception`, `warn` alias).
- **`get_logger(name)`** — factory returning a `Logger`.
- **`configure_logging(cfg)`** — one-time handler install on the root logger.

---

## 2. How it's written

### The wrapper (`Logger`)
```python
class Logger:
    def __init__(self, name: str) -> None:
        self._log = logging.getLogger(name)

    def debug(self, msg, *args):     self._log.debug(msg, *args)
    def info(self, msg, *args):      self._log.info(msg, *args)
    def warning(self, msg, *args):   self._log.warning(msg, *args)
    warn = warning
    def error(self, msg, *args):     self._log.error(msg, *args)
    def exception(self, msg, *args): self._log.exception(msg, *args)
```
- Wraps a stdlib logger named after the module (`logging.getLogger(name)`). Standard `logging` hierarchy still applies — names like `src.core.save_manager` roll up to the root.
- `*args` are **lazy `%`-style format args**, passed straight through: `log.warning("Failed '%s': %s", path, e)` — the string is only formatted if the level is enabled.
- `exception()` is for inside an `except` block — it logs at ERROR **with the traceback**.
- `warn = warning` is a convenience alias.

### Boot config (`configure_logging`)
```python
def configure_logging(cfg) -> None:
    """Install console + rotating-file handlers on the root logger. Idempotent."""
    global _configured
    if _configured:
        return
    root = logging.getLogger()
    root.setLevel(getattr(logging, cfg.level))         # gate for the whole tree
    fmt = logging.Formatter(_FORMAT, _DATEFMT)

    console = logging.StreamHandler()                  # → stderr
    console.setLevel(getattr(logging, cfg.console_level))
    console.setFormatter(fmt); root.addHandler(console)

    Path(cfg.file_path).parent.mkdir(parents=True, exist_ok=True)
    file = RotatingFileHandler(cfg.file_path, maxBytes=cfg.max_bytes,
                               backupCount=cfg.backup_count, encoding="utf-8")
    file.setLevel(getattr(logging, cfg.file_level))
    file.setFormatter(fmt); root.addHandler(file)
    _configured = True
```
- **Two handlers, two thresholds.** Console (stderr) and a `RotatingFileHandler`. Each has its own level *on top of* the root's `cfg.level` gate — a record must pass the root level **and** the handler level to show.
- **Idempotent.** The module-global `_configured` flag means a second call is a no-op (no duplicate handlers / double-printed lines).
- **Creates the log dir.** `Path(cfg.file_path).parent.mkdir(parents=True, exist_ok=True)`.
- **Format:** `"%(asctime)s %(levelname)-7s %(name)s: %(message)s"`, time as `%H:%M:%S` —   e.g. `19:42:07 WARNING src.core.save_manager: Failed to load save '...': ...`.

---

## 3. Configuration

Driven by the pydantic `LoggingConfig` (`data/config.py`), loaded from `data/config.json` under `"logging"`:

| Field | Default | Meaning |
|---|---|---|
| `level` | `INFO` | Root gate — the lowest level that reaches *any* handler |
| `console_level` | `WARNING` | Threshold for the stderr handler |
| `file_level` | `DEBUG` | Threshold for the rotating file |
| `file_path` | `logs/game.log` | Log file (dir auto-created) |
| `max_bytes` | `1_000_000` (~1 MB) | Rotate when the file hits this size |
| `backup_count` | `3` | Keep this many rotated files (`game.log.1` … `.3`) |

Each level is a `Literal["DEBUG","INFO","WARNING","ERROR"]`, so a bad value fails validation at load. Net effect of the defaults: **console is quiet** (warnings+), the **file is verbose** (everything from DEBUG up to the root `INFO` gate — so effectively INFO+ unless `level` is lowered to `DEBUG`).

---

## 4. How it connects

```
   main.py
     CONFIG = Config.load()            # pydantic, reads data/config.json
     configure_logging(CONFIG.logging) # once, before the window opens
            │ installs handlers on root logger
            ▼
   logging root ──► StreamHandler (stderr)  +  RotatingFileHandler (logs/game.log)
            ▲
            │ records bubble up
   module loggers:  get_logger(__name__) ──► Logger ──► logging.getLogger(name)
```

- **Boot:** `main.py` calls `configure_logging(CONFIG.logging)` immediately after loading config, before `GameDirector`/window — so handlers exist before anything logs.
- **Per-module:** at module top, `log = get_logger(__name__)`. Current users:   `src/core/save_manager.py`, `src/core/message_service.py`, `src/states/map_loader.py`, `src/systems/dialog_manager.py`. (More to come — the readability plan wants the remaining silent `except` blocks routed through it.)
- **Decoupling:** modules depend only on `get_logger`; they don't know about handlers, files, or rotation. Swapping the logging backend is a one-file change.

---

## 5. How to use it

### In a module
```python
from src.core.logger import get_logger

log = get_logger(__name__)        # name = "src.core.my_module"

log.info("loaded %d pokemon", count)          # lazy %-format args
log.warning("missing move '%s'; using default", name)

try:
    risky()
except Exception:
    log.exception("risky() failed")           # ERROR + full traceback
```

### Rules of thumb
- **One logger per module**, named `__name__` — gives you the source in every line.
- **Pass args, don't f-string:** `log.debug("hp=%s", hp)` not `log.debug(f"hp={hp}")` — the former skips formatting when DEBUG is off.
- **`exception()` only inside `except`** (it reads the live traceback); use `error()` elsewhere.
- **Don't call `configure_logging` again** — it's already done in `main.py` and is a no-op after.
- **To see more output**, lower `logging.level` (and/or the handler levels) in `data/config.json`.

---

## 6. Gotchas & rough edges

- **Root level gates everything.** A handler's lower level can't show records the root already dropped. Tune `level` first.
- **`configure_logging` is global + idempotent via a module flag.** Fine for the single-process game; in tests it persists across cases (call once, or not at all — tests don't configure logging).
- **`cfg` is duck-typed** (`def configure_logging(cfg)`), not annotated as `LoggingConfig`. It just needs the right attributes; pydantic guarantees them in practice.
- **No structured logging / context.** Plain string messages only — fine for this project's scale.

---

## 7. One-paragraph summary

`src/core/logger.py` is a façade over stdlib `logging`: `get_logger(__name__)` hands each module a thin `Logger` wrapper, and `configure_logging(CONFIG.logging)` — called once in `main.py` — installs a quiet stderr handler plus a verbose rotating file (`logs/game.log`), each with its own level beneath the root gate, all driven by the pydantic `LoggingConfig`. Modules log through `info/warning/exception/…` with lazy `%`-args and never touch handlers or files directly; it's the project's single, swappable seam for "stop swallowing errors."
