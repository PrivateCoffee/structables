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

<!-- START_INSTANCE_LIST type:eq=clearnet -->

| URL                                                                        | Provided by                                    | Country          | Notes         |
| -------------------------------------------------------------------------- | ---------------------------------------------- | ---------------- | ------------- |
| [structables.private.coffee](https://structables.private.coffee)           | [Private.coffee](https://private.coffee)       | Austria 🇦🇹 🇪🇺    | Main instance |
| [structables.bloat.cat](https://structables.bloat.cat)                     | [Bloat.cat](https://bloat.cat)                 | Germany 🇩🇪 🇪🇺    |               |
| [structables.darkness.services](https://structables.darkness.services)     | [Darkness.services](https://darkness.services) | United States 🇺🇸 |               |
| [structables.franklyflawless.org](https://structables.franklyflawless.org) | [FranklyFlawless](https://franklyflawless.org) | Germany 🇩🇪 🇪🇺    |               |

<!-- END_INSTANCE_LIST -->

### Tor Hidden Services

<!-- START_INSTANCE_LIST type:eq=onion -->

| URL                                                                                                                                                             | Provided by                                    | Country          | Notes         |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- | ---------------- | ------------- |
| [structables.coffee2m3bjsrrqqycx6ghkxrnejl2q6nl7pjw2j4clchjj6uk5zozad.onion](http://structables.coffee2m3bjsrrqqycx6ghkxrnejl2q6nl7pjw2j4clchjj6uk5zozad.onion) | [Private.coffee](https://private.coffee)       | Austria 🇦🇹 🇪🇺    | Main instance |
| [structables.darknessrdor43qkl2ngwitj72zdavfz2cead4t5ed72bybgauww5lyd.onion](http://structables.darknessrdor43qkl2ngwitj72zdavfz2cead4t5ed72bybgauww5lyd.onion) | [Darkness.services](https://darkness.services) | United States 🇺🇸 |               |

<!-- END_INSTANCE_LIST -->

### Adding Your Instance

To add your own instance to this list, please open a pull request or issue, see below.

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

**Note:** The Docker image is now hosted on [git.private.coffee](https://git.private.coffee/privatecoffee/structables/packages) instead of Docker Hub. Please use the new image name `git.private.coffee/privatecoffee/structables` instead of `privatecoffee/structables` to continue receiving updates.

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

### Environment Variables

Structables supports the use of the following environment variables for configuration:

- `STRUCTABLES_PORT`: The port to listen on (default: 8002)
- `STRUCTABLES_LISTEN_HOST`: The host/IP address to listen on (default: 127.0.0.1)
- `STRUCTABLES_INVIDIOUS`: The hostname of an Invidious instance to use for embedded YouTube videos (currently not recommended due to YouTube blocks)
- `STRUCTABLES_UNSAFE`: If set, allow embedding untrusted iframes (if unset, display a warning and allow loading the content manually)
- `STRUCTABLES_PRIVACY_FILE`: The path to a text file or Markdown file (with .md suffix) to use for the Privacy Policy page (if unset, try `privacy.txt` or `privacy.md` in the working directory, or fall back to a generic message)
- `STRUCTABLES_DEBUG`: If set, log additional debug information to stdout
- `STRUCTABLES_THEME`: Allows selecting a theme for the frontend. Currently, only `dark` and `light` are supported. If not set, it will be automatically detected based on the user's system settings, and a toggle will be provided in the header.
- `STRUCTABLES_CACHE_ENABLED`: Whether to enable caching of proxied content (default: true). Set to "false" or "0" to disable caching.
- `STRUCTABLES_CACHE_DIR`: The directory to use for caching proxied content (default: `structables_cache` within the temporary directory as returned by `tempfile.gettempdir()`)
- `STRUCTABLES_CACHE_MAX_AGE`: The maximum age of cached content in seconds before it's considered stale (default: 604800 seconds, or 1 week)
- `STRUCTABLES_CACHE_MAX_SIZE`: The maximum size of the cache directory in bytes (default: 1073741824 bytes, or 1GB)
- `STRUCTABLES_CACHE_CLEANUP_INTERVAL`: How often to run the cache cleanup process in seconds (default: 3600 seconds, or 1 hour)

## License

This project, as well as the two projects it is based on, are licensed under the GNU Affero General Public License v3. See the [LICENSE](LICENSE) file for more information.
