#!/usr/bin/env python

from flask import Flask
import threading
import time

from .config import Config
from .routes import init_routes
from .utils.data import update_data
from .utils.helpers import get_typesense_api_key

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
app.typesense_api_key = get_typesense_api_key()

init_routes(app)
update_data(app)


def background_update_data(app):
    """Runs the update_data function every 5 minutes.

    This replaces the need for a cron job to update the data.

    Args:
        app (Flask): The Flask app instance.
    """
    while True:
        update_data(app)
        time.sleep(300)


def main():
    threading.Thread(target=background_update_data, args=(app,), daemon=True).start()
    app.run(
        port=app.config["PORT"],
        host=app.config["LISTEN_HOST"],
        debug=app.config["DEBUG"],
    )


if __name__ == "__main__":
    main()
