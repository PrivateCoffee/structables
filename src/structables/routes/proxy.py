from flask import render_template, request, Response, abort
from werkzeug.exceptions import BadRequest, InternalServerError
from urllib.parse import unquote
from urllib.error import HTTPError
from urllib.request import urlopen
import logging

logger = logging.getLogger(__name__)

def init_proxy_routes(app):
    @app.route("/proxy/")
    def route_proxy():
        url = request.args.get("url")
        filename = request.args.get("filename")
        
        logger.debug(f"Proxy request for URL: {url}, filename: {filename}")

        if url is not None:
            if url.startswith("https://cdn.instructables.com/") or url.startswith(
                "https://content.instructables.com/"
            ):
                logger.debug(f"Valid proxy URL: {url}")

                def generate():
                    # Subfunction to allow streaming the data instead of
                    # downloading all of it at once
                    try:
                        logger.debug(f"Opening connection to {url}")
                        with urlopen(unquote(url)) as data:
                            logger.debug("Connection established, streaming data")
                            while True:
                                chunk = data.read(1024 * 1024)
                                if not chunk:
                                    break
                                yield chunk
                            logger.debug("Finished streaming data")
                    except HTTPError as e:
                        logger.error(f"HTTP error during streaming: {e.code}")
                        abort(e.code)

                try:
                    logger.debug(f"Getting content type for {url}")
                    with urlopen(unquote(url)) as data:
                        content_type = data.headers["content-type"]
                        logger.debug(f"Content type: {content_type}")
                except HTTPError as e:
                    logger.error(f"HTTP error getting content type: {e.code}")
                    abort(e.code)
                except KeyError:
                    logger.error("Content-Type header missing")
                    raise InternalServerError()

                headers = dict()

                if filename is not None:
                    headers["Content-Disposition"] = (
                        f'attachment; filename="{filename}"'
                    )
                    logger.debug(f"Added Content-Disposition header for {filename}")

                return Response(generate(), content_type=content_type, headers=headers)
            else:
                logger.warning(f"Invalid proxy URL: {url}")
                raise BadRequest()
        else:
            logger.warning("No URL provided for proxy")
            raise BadRequest()

    @app.route("/iframe/")
    def route_iframe():
        url = request.args.get("url")
        url = unquote(url)
        
        logger.debug(f"iframe request for URL: {url}")
        
        if url is not None:
            return render_template("iframe.html", url=url)
        else:
            logger.warning("No URL provided for iframe")
            raise BadRequest()