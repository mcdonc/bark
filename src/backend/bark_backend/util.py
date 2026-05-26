"""Utility for resolving environment variables that may reference files."""

import logging
import os

logger = logging.getLogger(__name__)


def resolve_env_secret(key: str, default: str | None = None) -> str | None:
    """Read an env var, dereferencing 'path:' prefixed values.

    If the value starts with 'file:', the remainder is treated as a
    file path and the file contents (stripped) are returned. If the
    file cannot be read, logs an error and returns None.
    """
    val = os.environ.get(key)
    if val is None:
        return default
    if val.startswith("file:"):
        path = val[5:]
        try:
            return open(path).read().strip()
        except OSError as e:
            logger.error("Cannot read %s from %s: %s", key, path, e)
            return None
    return val
