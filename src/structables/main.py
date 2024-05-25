#!/usr/bin/env python

from flask import Flask

from .config import Config
from .routes import init_routes
from .utils.data import update_data
from .utils.helpers import get_typesense_api_key

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object(Config)
app.typesense_api_key = get_typesense_api_key()

init_routes(app)

def main():
    app.run(port=app.config['PORT'], host=app.config['LISTEN_HOST'], debug=app.config['DEBUG'])

if __name__ == "__main__":
    main()

# Initialize data when the server starts
update_data(app)