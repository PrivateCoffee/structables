#!/usr/bin/env python

from flask import Flask
import threading
import time
import logging

from .config import Config
from .routes import init_routes
from .utils.data import update_data
from .routes.proxy import start_cache_cleanup_thread

# Configure logging
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)

logger.debug("Initializing routes")
init_routes(app)
logger.debug("Performing initial data update")
update_data(app)

def background_update_data(app):
    """Runs the update_data function every 5 minutes.

    This replaces the need for a cron job to update the data.

    Args:
        app (Flask): The Flask app instance.
    """
    logger.debug("Starting background update thread")
    while True:
        logger.debug("Running scheduled data update")
        update_data(app)
        logger.debug("Data update complete, sleeping for 5 minutes")
        time.sleep(300)

def main():
    if app.config["DEBUG"]:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    logger.debug("Starting background update thread")
    threading.Thread(target=background_update_data, args=(app,), daemon=True).start()
    
    # Start the cache cleanup thread
    start_cache_cleanup_thread(app)
    
    logger.info(f"Starting Structables on {app.config['LISTEN_HOST']}:{app.config['PORT']}")
    app.run(
        port=app.config["PORT"],
        host=app.config["LISTEN_HOST"],
        debug=app.config["DEBUG"],
    )

if __name__ == "__main__":
    main()