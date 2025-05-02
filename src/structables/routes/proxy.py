from flask import render_template, request, Response, abort
from werkzeug.exceptions import BadRequest, InternalServerError
from urllib.parse import unquote
from urllib.error import HTTPError
from urllib.request import urlopen
import logging
import os
import hashlib
import time
import shutil

logger = logging.getLogger(__name__)

# Track last cache cleanup time
last_cache_cleanup = 0


def get_cache_path(app, url):
    """Generate a cache file path for a URL.

    Args:
        app: The Flask app instance.
        url (str): The URL to cache.

    Returns:
        str: The path to the cache file.
    """
    # Create a hash of the URL to use as the filename
    url_hash = hashlib.sha256(url.encode()).hexdigest()
    cache_dir = app.config["CACHE_DIR"]
    return os.path.join(cache_dir, url_hash)


def is_cached(app, url):
    """Check if a URL is cached and not expired.

    Args:
        app: The Flask app instance.
        url (str): The URL to check.

    Returns:
        bool: True if the URL is cached and not expired, False otherwise.
    """
    # If caching is disabled, always return False
    if not app.config["CACHE_ENABLED"]:
        return False

    cache_path = get_cache_path(app, url)

    # Check if the file exists
    if not os.path.exists(cache_path):
        return False

    # Check if the cache has expired
    cache_time = os.path.getmtime(cache_path)
    max_age = app.config["CACHE_MAX_AGE"]
    if time.time() - cache_time > max_age:
        # Cache has expired, remove it
        try:
            os.remove(cache_path)
            # Also remove metadata file if it exists
            meta_path = cache_path + ".meta"
            if os.path.exists(meta_path):
                os.remove(meta_path)
            return False
        except OSError:
            logger.warning(f"Failed to remove expired cache file: {cache_path}")
            return False

    # Cache exists and is not expired
    return True


def get_content_type(cache_path):
    """Get the content type from a cache file.

    Args:
        cache_path (str): The path to the cache file.

    Returns:
        str: The content type, or 'application/octet-stream' if not found.
    """
    meta_path = cache_path + ".meta"
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                return f.read().strip()
        except OSError:
            logger.warning(
                f"Failed to read content type from cache metadata: {meta_path}"
            )

    return "application/octet-stream"


def maybe_cleanup_cache(app):
    """Clean up the cache directory if it's time to do so.

    Args:
        app: The Flask app instance.
    """
    global last_cache_cleanup

    # If caching is disabled, don't do anything
    if not app.config["CACHE_ENABLED"]:
        return

    # Check if it's time to run cleanup
    current_time = time.time()
    cleanup_interval = app.config["CACHE_CLEANUP_INTERVAL"]

    if current_time - last_cache_cleanup < cleanup_interval:
        logger.debug(
            f"Cache cleanup skipped. Time since last cleanup: {current_time - last_cache_cleanup:.2f} seconds"
        )
        return

    logger.debug("Starting cache cleanup")
    last_cache_cleanup = current_time

    try:
        cache_dir = app.config["CACHE_DIR"]
        max_size = app.config["CACHE_MAX_SIZE"]
        max_age = app.config["CACHE_MAX_AGE"]

        # Get all cache files with their modification times
        cache_files = []
        total_size = 0

        for filename in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, filename)
            if os.path.isfile(file_path):
                # Skip metadata files in the count
                if file_path.endswith(".meta"):
                    continue

                file_size = os.path.getsize(file_path)
                file_time = os.path.getmtime(file_path)
                total_size += file_size
                cache_files.append((file_path, file_time, file_size))

        logger.debug(f"Current cache size: {total_size / (1024 * 1024):.2f} MB")

        # First, remove expired files
        current_time = time.time()
        expired_files = [
            (path, mtime, size)
            for path, mtime, size in cache_files
            if current_time - mtime > max_age
        ]

        for file_path, _, file_size in expired_files:
            try:
                os.remove(file_path)
                # Also remove metadata file if it exists
                meta_path = file_path + ".meta"
                if os.path.exists(meta_path):
                    os.remove(meta_path)
                total_size -= file_size
                logger.debug(f"Removed expired cache file: {file_path}")
            except OSError:
                logger.warning(f"Failed to remove expired cache file: {file_path}")

        # Remove files from the list that we've already deleted
        cache_files = [
            (path, mtime, size)
            for path, mtime, size in cache_files
            if (path, mtime, size) not in expired_files
        ]

        # If we're still over the size limit, remove oldest files first
        if total_size > max_size:
            logger.debug("Cache size exceeds limit, cleaning up")
            # Sort by modification time (oldest first)
            cache_files.sort(key=lambda x: x[1])

            # Remove files until we're under the limit
            for file_path, _, file_size in cache_files:
                if total_size <= max_size:
                    break

                try:
                    os.remove(file_path)
                    # Also remove metadata file if it exists
                    meta_path = file_path + ".meta"
                    if os.path.exists(meta_path):
                        os.remove(meta_path)

                    total_size -= file_size
                    logger.debug(f"Removed old cache file: {file_path}")
                except OSError:
                    logger.warning(f"Failed to remove cache file: {file_path}")

        logger.debug(
            f"Cache cleanup complete. New size: {total_size / (1024 * 1024):.2f} MB"
        )

    except Exception as e:
        logger.error(f"Error during cache cleanup: {str(e)}")


def init_proxy_routes(app):
    # Create cache directory if it doesn't exist and caching is enabled
    if app.config["CACHE_ENABLED"]:
        cache_dir = app.config["CACHE_DIR"]
        os.makedirs(cache_dir, exist_ok=True)
        logger.debug(f"Cache directory: {cache_dir}")
        logger.debug(f"Cache max age: {app.config['CACHE_MAX_AGE']} seconds")
        logger.debug(
            f"Cache max size: {app.config['CACHE_MAX_SIZE'] / (1024 * 1024):.2f} MB"
        )
        logger.debug(
            f"Cache cleanup interval: {app.config['CACHE_CLEANUP_INTERVAL']} seconds"
        )
    else:
        logger.debug("Caching is disabled")

    @app.route("/proxy/")
    def route_proxy():
        url = request.args.get("url")
        filename = request.args.get("filename")

        logger.debug(f"Proxy request for URL: {url}, filename: {filename}")

        # Clean up the cache if needed
        maybe_cleanup_cache(app)

        if url is not None:
            if url.startswith("https://cdn.instructables.com/") or url.startswith(
                "https://content.instructables.com/"
            ):
                logger.debug(f"Valid proxy URL: {url}")
                unquoted_url = unquote(url)

                # Check if the content is already cached
                if is_cached(app, unquoted_url):
                    logger.debug(f"Serving cached content for: {unquoted_url}")
                    cache_path = get_cache_path(app, unquoted_url)
                    content_type = get_content_type(cache_path)

                    def generate_from_cache():
                        with open(cache_path, "rb") as f:
                            while True:
                                chunk = f.read(1024 * 1024)
                                if not chunk:
                                    break
                                yield chunk

                    headers = dict()
                    if filename is not None:
                        headers["Content-Disposition"] = (
                            f'attachment; filename="{filename}"'
                        )

                    return Response(
                        generate_from_cache(),
                        content_type=content_type,
                        headers=headers,
                    )

                # Content is not cached or caching is disabled, fetch it
                def generate_and_maybe_cache():
                    try:
                        logger.debug(f"Opening connection to {unquoted_url}")
                        with urlopen(unquoted_url) as data:
                            logger.debug("Connection established, streaming data")

                            # If caching is enabled, cache the content
                            if app.config["CACHE_ENABLED"]:
                                cache_path = get_cache_path(app, unquoted_url)
                                temp_path = cache_path + ".tmp"
                                with open(temp_path, "wb") as f:
                                    while True:
                                        chunk = data.read(1024 * 1024)
                                        if not chunk:
                                            break
                                        f.write(chunk)
                                        yield chunk

                                # Save the content type
                                try:
                                    content_type = data.headers["content-type"]
                                    with open(cache_path + ".meta", "w") as f:
                                        f.write(content_type)
                                except (KeyError, OSError):
                                    logger.warning(
                                        f"Failed to save content type for: {unquoted_url}"
                                    )

                                # Rename the temporary file to the final cache file
                                try:
                                    os.rename(temp_path, cache_path)
                                    logger.debug(
                                        f"Successfully cached content for: {unquoted_url}"
                                    )
                                except OSError:
                                    logger.warning(
                                        f"Failed to rename temporary cache file: {temp_path}"
                                    )
                                    # Try to copy and delete instead
                                    try:
                                        shutil.copy2(temp_path, cache_path)
                                        os.remove(temp_path)
                                        logger.debug(
                                            f"Successfully cached content using copy method: {unquoted_url}"
                                        )
                                    except OSError:
                                        logger.error(
                                            f"Failed to cache content: {unquoted_url}"
                                        )
                            else:
                                # If caching is disabled, just stream the data
                                while True:
                                    chunk = data.read(1024 * 1024)
                                    if not chunk:
                                        break
                                    yield chunk

                    except HTTPError as e:
                        logger.error(f"HTTP error during streaming: {e.code}")
                        abort(e.code)
                    except Exception as e:
                        logger.error(f"Error fetching content: {str(e)}")
                        abort(500)

                try:
                    logger.debug(f"Getting content type for {unquoted_url}")
                    with urlopen(unquoted_url) as data:
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

                return Response(
                    generate_and_maybe_cache(),
                    content_type=content_type,
                    headers=headers,
                )
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
