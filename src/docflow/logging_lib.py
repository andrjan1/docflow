from rich.logging import RichHandler
import logging
from pathlib import Path
import json
from datetime import datetime, timezone
import os


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        if ts.endswith('+00:00'):
            ts = ts.replace('+00:00', 'Z')
        base = {
            'timestamp': ts,
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
        }
        extras = {}
        for k, v in record.__dict__.items():
            if k not in (
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 'module',
                'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 'created', 'msecs',
                'relativeCreated', 'thread', 'threadName', 'processName', 'process'
            ):
                extras[k] = v
        if extras:
            base['extra'] = extras
        return json.dumps(base)


def _coerce_level(level: str | int | None) -> int:
    if level is None:
        return logging.INFO
    if isinstance(level, int):
        return level
    return getattr(logging, str(level).upper(), logging.INFO)


def setup_logger(name: str = 'docflow', json_file: str | None = None, level: str | int | None = None):
    """Return a configured logger.

    Priority order for level:
      1. explicit level arg
      2. env DOCFLOW_LOG_LEVEL
      3. existing logger level (if handlers already present)
      4. default INFO
    """
    env_level = os.getenv('DOCFLOW_LOG_LEVEL')
    resolved_level = _coerce_level(level or env_level)
    logger = logging.getLogger(name)
    # if no handlers yet, attach rich + optional json file
    if not logger.handlers:
        handler = RichHandler()
        logger.addHandler(handler)
        if json_file:
            p = Path(json_file)
            p.parent.mkdir(parents=True, exist_ok=True)
            fh = logging.FileHandler(str(p))
            fh.setFormatter(JsonLineFormatter())
            logger.addHandler(fh)
    # always update level to resolved one
    logger.setLevel(resolved_level)
    return logger


def reconfigure_log_level(level: str | int):
    lvl = _coerce_level(level)
    root = logging.getLogger('docflow')
    root.setLevel(lvl)
    # propagate to children (simple approach)
    mgr = logging.Logger.manager
    for name, logger in mgr.loggerDict.items():  # type: ignore[attr-defined]
        if isinstance(logger, logging.Logger) and name.startswith('docflow'):
            logger.setLevel(lvl)


def json_log_entry(logger, obj: dict):
    for h in logger.handlers:
        if isinstance(h, logging.FileHandler):
            record = logging.LogRecord(logger.name, logging.INFO, '', 0, json.dumps(obj), None, None)
            h.emit(record)
