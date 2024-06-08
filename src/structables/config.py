import os

class Config:
    DEBUG = os.environ.get("FLASK_DEBUG", os.environ.get("STRUCTABLES_DEBUG", False))
    PORT = int(os.environ.get("STRUCTABLES_PORT", 8002))
    LISTEN_HOST = os.environ.get("STRUCTABLES_LISTEN_HOST", "127.0.0.1")
    INVIDIOUS = os.environ.get("STRUCTABLES_INVIDIOUS")
    UNSAFE = os.environ.get("STRUCTABLES_UNSAFE", False)
    PRIVACY_FILE = os.environ.get("STRUCTABLES_PRIVACY_FILE")

    @staticmethod
    def init_app(app):
        pass