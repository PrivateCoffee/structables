<img align="right" src="src/structables/static/img/logo.png">

# Structables

An open source alternative front-end to Instructables. This is a fork of <a href="https://codeberg.org/indestructables/indestructables">snowcatridge10's Indestructables</a>, which itself is a fork of <a href="https://git.vern.cc/cobra/Destructables">Cobra's Destructables</a>.

[![Support Private.coffee!](https://shields.private.coffee/badge/private.coffee-support%20us!-pink?logo=coffeescript)](https://private.coffee)
[![Matrix](https://shields.private.coffee/badge/Matrix-join%20us!-blue?logo=matrix)](https://matrix.pcof.fi/#/#structables:private.coffee)
[![PyPI](https://shields.private.coffee/pypi/v/structables)](https://pypi.org/project/structables/)
[![PyPI - Python Version](https://shields.private.coffee/pypi/pyversions/structables)](https://pypi.org/project/structables/)
[![PyPI - License](https://shields.private.coffee/pypi/l/structables)](https://pypi.org/project/structables/)
[![Latest Git Commit](https://shields.private.coffee/gitea/last-commit/privatecoffee/structables?gitea_url=https://git.private.coffee)](https://git.private.coffee/privatecoffee/structables)

## Instances

| URL                                                               | Provided by                               | Country | Comments |
| ----------------------------------------------------------------- | ----------------------------------------- | ------- | -------- |
| [structables.private.coffee](https://structables.private.coffee/) | [Private.coffee](https://private.coffee/) | Austria |          |
| [structables.bloat.cat](https://structables.bloat.cat/)           | [Bloat.cat](https://bloat.cat)            | Germany |          |

To add your own instance to this list, please open a pull request or issue.

## Opening Issues

If you're having problems using Structables, or if you have ideas or feedback for us, feel free to open an issue in the [Private.coffee Git](https://git.private.coffee/PrivateCoffee/structables/issues) or on [Github](https://github.com/PrivateCoffee/structables/issues).

Of course, you can also join our [Matrix room](https://matrix.pcof.fi/#/#structables:private.coffee) to discuss your ideas with us.

## Run your own instance

### Production: Manual

1. Create a virtual environment: `python3 -m venv venv`
2. Activate the virtual environment: `source venv/bin/activate`
3. Install the packages: `pip install structables uwsgi`
4. Run `uwsgi --plugin python3 --http-socket 0.0.0.0:8002 --module structables.main:app --processes 4 --threads 4`
5. Point your reverse proxy to http://localhost:8002 and (optionally) serve static files from the `venv/lib/pythonX.XX/site-packages/structables/static` directory
6. Connect to your instance under your domain
7. Ensure that `/cron/` is executed at regular intervals so that the app updates its cached data.

### Production: Docker

1. Copy `.env.example` to `.env` and adjust the settings as necessary
2. Copy `docker-compose-example.yml` to `docker-compose.yml` and adjust it as necessary, for example modifying resource limits or changing the port/host configuration
3. Build and run the Docker container:

   ```sh
   docker-compose up [-d]
   ```

4. Point your reverse proxy to http://127.0.0.1:8002 (or your chosen port, if you modified it) and (optionally) serve static files from `structables/static`
5. Connect to your instance under your domain
6. Ensure that `/cron/` is executed at regular intervals so that the app updates its cached data.

### Development

1. Clone the repository: `git clone https://git.private.coffee/privatecoffee/structables.git && cd structables`
2. Create a virtual environment: `python3 -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate`
4. Install in editable mode: `pip install -e .`
5. Run `structables`
6. Connect to http://localhost:8002

## License

This project, as well as the two projects it is based on, are licensed under the GNU Affero General Public License v3. See the [LICENSE](LICENSE) file for more information.
