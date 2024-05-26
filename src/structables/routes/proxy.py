from flask import render_template, request, Response, abort
from werkzeug.exceptions import BadRequest, InternalServerError
from urllib.parse import unquote
from urllib.error import HTTPError
from urllib.request import urlopen


def init_proxy_routes(app):
    @app.route("/proxy/")
    def route_proxy():
        url = request.args.get("url")
        filename = request.args.get("filename")

        if url is not None:
            if url.startswith("https://cdn.instructables.com/") or url.startswith(
                "https://content.instructables.com/"
            ):

                def generate():
                    # Subfunction to allow streaming the data instead of
                    # downloading all of it at once
                    try:
                        with urlopen(unquote(url)) as data:
                            while True:
                                chunk = data.read(1024 * 1024)
                                if not chunk:
                                    break
                                yield chunk
                    except HTTPError as e:
                        abort(e.code)

                try:
                    with urlopen(unquote(url)) as data:
                        content_type = data.headers["content-type"]
                except HTTPError as e:
                    abort(e.code)
                except KeyError:
                    raise InternalServerError()

                headers = dict()

                if filename is not None:
                    headers["Content-Disposition"] = (
                        f'attachment; filename="{filename}"'
                    )

                return Response(generate(), content_type=content_type, headers=headers)
            else:
                raise BadRequest()
        else:
            raise BadRequest()

    @app.route("/iframe/")
    def route_iframe():
        url = request.args.get("url")
        url = unquote(url)
        if url is not None:
            return render_template("iframe.html", url=url)
        else:
            raise BadRequest()
