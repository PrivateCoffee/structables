import os
import tempfile
import logging

from pathlib import Path

from .utils.helpers import get_typesense_api_key

logger = logging.getLogger(__name__)


class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", os.environ.get("STRUCTABLES_DEBUG", False))
    PORT = int(os.environ.get("STRUCTABLES_PORT", 8002))
    LISTEN_HOST = os.environ.get("STRUCTABLES_LISTEN_HOST", "127.0.0.1")
    INVIDIOUS = os.environ.get("STRUCTABLES_INVIDIOUS")
    UNSAFE = os.environ.get("STRUCTABLES_UNSAFE", False)
    PRIVACY_FILE = os.environ.get("STRUCTABLES_PRIVACY_FILE")
    THEME = os.environ.get("STRUCTABLES_THEME", "auto")
    TYPESENSE_API_KEY = get_typesense_api_key()

    # Cache settings
    CACHE_ENABLED = os.environ.get("STRUCTABLES_CACHE_ENABLED", "true").lower() not in (
        "false",
        "0",
        "no",
        "off",
        "n",
    )
    CACHE_DIR = os.environ.get("STRUCTABLES_CACHE_DIR")

    if CACHE_ENABLED and CACHE_DIR is None:
        try:
            CACHE_DIR = Path(tempfile.gettempdir()) / "structables_cache"
        except FileNotFoundError:
            CACHE_DIR = Path(os.getcwd()) / "structables_cache"

        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / "test").write_text("test")
            (CACHE_DIR / "test").unlink()
        except Exception as e:
            logger.error(f"Could not create or write to cache directory: {e} - disabling cache")
            CACHE_ENABLED = False
            CACHE_DIR = None

    CACHE_MAX_AGE = int(
        os.environ.get("STRUCTABLES_CACHE_MAX_AGE", 60 * 60 * 24 * 7)
    )  # 1 week default
    CACHE_MAX_SIZE = int(
        os.environ.get("STRUCTABLES_CACHE_MAX_SIZE", 1024 * 1024 * 1024)
    )  # 1GB default
    CACHE_CLEANUP_INTERVAL = int(
        os.environ.get("STRUCTABLES_CACHE_CLEANUP_INTERVAL", 60 * 60)
    )  # 1 hour default

    @staticmethod
    def init_app(app):
        pass
