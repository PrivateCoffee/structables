import os
import tempfile

from .utils.helpers import get_typesense_api_key


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

    if CACHE_DIR is None:
        CACHE_DIR = os.path.join(
            tempfile.gettempdir(), "structables_cache"
        )

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
