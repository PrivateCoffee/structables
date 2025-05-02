#!/usr/bin/env python

from flask import Flask
import logging
import time

from .config import Config
from .routes import init_routes
from .utils.data import maybe_update_data

# Configure logging
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

logger.debug("Initializing routes")
init_routes(app)
logger.debug("Performing initial data update")
maybe_update_data(app)


def main():
    if app.config["DEBUG"]:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

    logger.info(
        f"Starting Structables on {app.config['LISTEN_HOST']}:{app.config['PORT']}"
    )
    app.run(
        port=app.config["PORT"],
        host=app.config["LISTEN_HOST"],
        debug=app.config["DEBUG"],
    )


if __name__ == "__main__":
    main()
