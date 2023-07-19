<div align="center">
<img src="static/img/logo.png">
<h1>Indestructables</h1>
An open source alternative front-end to Instructables. This is a fork of <a href="https://codeberg.org/indestructables/indestructables">snowcatridge10's Indestructables</a> to use Playwright instead of Selenium, which itself is a fork of <a href="https://git.vern.cc/cobra/Destructables">Cobra's Destructables</a>.

<ul>
    <li>
        <a href="https://matrix.to/#/#indestructables:fedora.im">snowcatridge10's Matrix Room</a>
    </li>
    <li>
        <a href="https://mto.vern.cc/#/%23cobra-frontends:vern.cc">Cobra's Matrix Room</a>
    </li>
</ul>

</div>

# Instances

| URL                                                                                | Provided by                               | Country | Comments |
| ---------------------------------------------------------------------------------- | ----------------------------------------- | ------- | -------- |
| [https://indestructables.private.coffee/](https://indestructables.private.coffee/) | [Private.coffee](https://private.coffee/) | Austria |          |

# Run your own instance

## Dependencies

First, create a virtual environment with `python3 -m venv venv` and activate it with `source venv/bin/activate`. Then, install the dependencies with:

`pip3 install -r requirements.txt`.

For the production environment, you also need the uWSGI Python3 plugin. On Debian, it can be installed via `apt install uwsgi-plugin-python3`

Furthermore, you need to install the Chromium binary used by Playwright. You can do this by running `playwright install chromium`.

## Production

1. Clone the repository
2. Run `uwsgi --plugin python3 --http-socket 0.0.0.0:8002 --wsgi-file main.py --callable app --processes 4 --threads 2`
3. Point your reverse proxy to http://localhost:8002

## Development

1. Clone the repository
2. Run `python3 main.py`
3. Connect to http://localhost:8002

## License

This project, as well as the two projects it is based on, are licensed under the GNU Affero General Public License v3. See the LICENSE file for more information.