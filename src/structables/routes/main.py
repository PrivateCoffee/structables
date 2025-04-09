from flask import render_template, abort, request
from urllib.request import urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from urllib.parse import quote
from werkzeug.exceptions import InternalServerError
from markdown2 import Markdown
from traceback import print_exc
import pathlib
import json
import logging

from ..utils.data import update_data
from ..utils.helpers import explore_lists, proxy
from .category import project_list

logger = logging.getLogger(__name__)


def init_main_routes(app):
    @app.route("/")
    def route_explore():
        logger.debug("Rendering explore page")

        try:
            logger.debug("Fetching data from instructables.com")
            data = urlopen("https://www.instructables.com/")
        except HTTPError as e:
            logger.error(f"HTTP error fetching explore page: {e.code}")
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        explore = soup.select(".home-content-explore-wrap")[0]

        title = explore.select("h2")[0].text
        logger.debug(f"Explore page title: {title}")

        logger.debug("Parsing category sections")
        circuits = explore_lists(
            explore.select(".home-content-explore-category-circuits")[0]
        )
        workshop = explore_lists(
            explore.select(".home-content-explore-category-workshop")[0]
        )
        craft = explore_lists(explore.select(".home-content-explore-category-craft")[0])
        cooking = explore_lists(
            explore.select(".home-content-explore-category-cooking")[0]
        )
        living = explore_lists(
            explore.select(".home-content-explore-category-living")[0]
        )
        outside = explore_lists(
            explore.select(".home-content-explore-category-outside")[0]
        )
        teachers = explore_lists(
            explore.select(".home-content-explore-category-teachers")[0]
        )

        logger.debug("Rendering explore page template")

        return render_template(
            "index.html",
            title=title,
            sections=[
                ("Circuits", "/circuits", circuits),
                ("Workshop", "/workshop", workshop),
                ("Craft", "/craft", craft),
                ("Cooking", "/cooking", cooking),
                ("Living", "/living", living),
                ("Outside", "/outside", outside),
                ("Teachers", "/teachers", teachers),
            ],
        )

    @app.route("/sitemap/")
    @app.route("/sitemap/<path:path>")
    def route_sitemap(path=""):
        logger.debug(f"Rendering sitemap for path: {path}")

        try:
            logger.debug(
                f"Fetching sitemap data from instructables.com for path: {path}"
            )
            data = urlopen("https://www.instructables.com/sitemap/" + path)
        except HTTPError as e:
            logger.error(f"HTTP error fetching sitemap: {e.code}")
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        main = soup.select("div.sitemap-content")[0]

        group_section = main.select("div.group-section")

        if group_section:
            logger.debug(f"Found {len(group_section)} group sections")
            groups = []
            for group in group_section:
                category = group.select("h2 a")[0].text
                category_link = group.select("h2 a")[0].get("href")
                channels = []
                for li in group.select("ul.sitemap-listing li"):
                    channel = li.a.text
                    channel_link = li.a["href"]
                    channels.append([channel, channel_link])
                groups.append([category, category_link, channels])
                logger.debug(f"Added group {category} with {len(channels)} channels")

        else:
            logger.debug("No group sections found, using flat list")
            groups = []
            channels = []
            for li in main.select("ul.sitemap-listing li"):
                channel = li.a.text
                channel_link = li.a["href"]

                if channel_link.startswith("https://"):
                    channel_link = f'/{"/".join(channel_link.split("/")[3:])}'

                channels.append([channel, channel_link])
            groups.append(["", "", channels])
            logger.debug(f"Added flat list with {len(channels)} channels")

        return render_template("sitemap.html", title="Sitemap", groups=groups)

    @app.route("/<article>/")
    def route_article(article):
        logger.debug(f"Rendering article page for: {article}")

        try:
            logger.debug(f"Fetching article data from instructables.com for: {article}")
            data = urlopen(
                f"https://www.instructables.com/json-api/showInstructableModel?urlString={article}"
            )
            data = json.loads(data.read().decode())
            logger.debug("Successfully fetched article data")
        except HTTPError as e:
            logger.error(f"HTTP error fetching article: {e.code}")
            abort(e.code)

        try:
            title = data["title"]
            author = data["author"]["screenName"]
            author_link = f"/member/{author}"
            category = data["classifications"][0]["title"]
            category_slug = data["classifications"][0]["name"]
            category_link = f"/{category_slug}/"
            channel = data["classifications"][0]["channels"][0]["title"]
            channel_slug = data["classifications"][0]["channels"][0]["name"]
            channel_link = f"/{category_slug}/{channel_slug}/"

            views = data["views"]
            favorites = data["favorites"]

            logger.debug(f"Article: {title} by {author} in {category}/{channel}")

            if "steps" in data:
                logger.debug(f"Article has {len(data['steps'])} steps")
                steps = []

                if "supplies" in data:
                    supplies = data["supplies"]
                    logger.debug("Article has supplies section")

                    supplies_files = []

                    if "suppliesFiles" in data:
                        supplies_files = data["suppliesFiles"]
                        logger.debug(f"Article has {len(supplies_files)} supply files")

                    data["steps"].insert(
                        1,
                        {
                            "title": "Supplies",
                            "body": supplies,
                            "files": supplies_files,
                        },
                    )

                for step in data["steps"]:
                    step_title = step["title"]
                    logger.debug(f"Processing step: {step_title}")

                    step_imgs = []
                    step_iframes = []
                    step_downloads = []

                    for file in step["files"]:
                        if file["image"]:
                            if "embedType" not in "file":
                                step_imgs.append(
                                    {
                                        "src": proxy(file["downloadUrl"], file["name"]),
                                        "alt": file["name"],
                                    }
                                )
                            if file["embedType"] == "VIDEO":
                                embed_html_code = file["embedHtmlCode"]
                                soup = BeautifulSoup(embed_html_code, "html.parser")
                                if soup.select("iframe"):
                                    src = soup.select("iframe")[0].get("src")
                                    width = soup.select("iframe")[0].get("width")
                                    height = soup.select("iframe")[0].get("height")
                                    logger.debug(
                                        f"Processing video iframe with src: {src}"
                                    )

                                    if src.startswith(
                                        "https://content.instructables.com"
                                    ):
                                        src = src.replace(
                                            "https://content.instructables.com",
                                            f"/proxy/?url={src}",
                                        )
                                        logger.debug(
                                            f"Proxying instructables content: {src}"
                                        )

                                    elif app.config["INVIDIOUS"] and src.startswith(
                                        "https://www.youtube.com"
                                    ):
                                        src = src.replace(
                                            "https://www.youtube.com",
                                            app.config["INVIDIOUS"],
                                        )
                                        logger.debug(
                                            f"Using Invidious for YouTube: {src}"
                                        )

                                    elif not app.config["UNSAFE"]:
                                        src = "/iframe/?url=" + quote(src)
                                        logger.debug(
                                            f"Using iframe wrapper for safety: {src}"
                                        )

                                    step_iframes.append(
                                        {
                                            "src": src,
                                            "width": width,
                                            "height": height,
                                        }
                                    )

                        elif not file["image"]:
                            if "downloadUrl" in file.keys():
                                step_downloads.append(
                                    {
                                        "src": proxy(file["downloadUrl"], file["name"]),
                                        "name": file["name"],
                                    }
                                )

                            else:  # Leaves us with embeds
                                embed_code = file["embedHtmlCode"]
                                soup = BeautifulSoup(embed_code, "html.parser")

                                iframe = soup.select("iframe")[0]

                                src = iframe.get("src")
                                logger.debug(f"Processing iframe with src: {src}")

                                if src.startswith("https://content.instructables.com"):
                                    src = src.replace(
                                        "https://content.instructables.com",
                                        f"/proxy/?url={src}",
                                    )
                                    logger.debug(
                                        f"Proxying instructables content: {src}"
                                    )

                                elif app.config["INVIDIOUS"] and src.startswith(
                                    "https://www.youtube.com"
                                ):
                                    src = src.replace(
                                        "https://www.youtube.com",
                                        app.config["INVIDIOUS"],
                                    )
                                    logger.debug(f"Using Invidious for YouTube: {src}")

                                elif not app.config["UNSAFE"]:
                                    src = "/iframe/?url=" + quote(src)
                                    logger.debug(
                                        f"Using iframe wrapper for safety: {src}"
                                    )

                                step_iframes.append(
                                    {
                                        "src": src,
                                        "width": file.get("width"),
                                        "height": file.get("height"),
                                    }
                                )

                    step_text = step["body"]
                    step_text = step_text.replace(
                        "https://content.instructables.com",
                        "/proxy/?url=https://content.instructables.com",
                    )

                    logger.debug(
                        f"Step {step_title}: {len(step_imgs)} images, {len(step_iframes)} iframes, {len(step_downloads)} downloads"
                    )

                    steps.append(
                        {
                            "title": step_title,
                            "imgs": step_imgs,
                            "text": step_text,
                            "iframes": step_iframes,
                            "downloads": step_downloads,
                        }
                    )

                comments_list = []
                comment_count = 0

                # TODO: Fix comments

                logger.debug(f"Rendering article template with {len(steps)} steps")
                return render_template(
                    "article.html",
                    title=title,
                    author=author,
                    author_link=author_link,
                    category=category,
                    category_link=category_link,
                    channel=channel,
                    channel_link=channel_link,
                    views=views,
                    favorites=favorites,
                    steps=steps,
                    comment_count=comment_count,
                    comments_list=comments_list,
                    enumerate=enumerate,
                )
            else:
                ## Collections
                logger.debug("Article is a collection")
                thumbnails = []
                for thumbnail in data["instructables"]:
                    text = thumbnail["title"]
                    link = thumbnail["showUrl"]
                    img = proxy(thumbnail["downloadUrl"])
                    thumbnail_title = thumbnail["title"]
                    thumbnail_author = thumbnail["author"]["screenName"]
                    thumbnail_author_link = f"/member/{thumbnail_author}"
                    thumbnail_channel = thumbnail["classifications"][0]["channels"][0][
                        "title"
                    ]
                    thumbnail_category = thumbnail["classifications"][0]["title"]
                    thumbnail_channel_link = (
                        f"/{thumbnail_category}/{thumbnail_channel}"
                    )

                    thumbnails.append(
                        {
                            "text": text,
                            "link": link,
                            "img": img,
                            "title": thumbnail_title,
                            "author": thumbnail_author,
                            "author_link": thumbnail_author_link,
                            "channel": thumbnail_channel,
                            "channel_link": thumbnail_channel_link,
                        }
                    )

                logger.debug(f"Collection has {len(thumbnails)} items")
                return render_template(
                    "collection.html",
                    title=title,
                    author=author,
                    author_link=author_link,
                    category=category,
                    category_link=category_link,
                    channel=channel,
                    channel_link=channel_link,
                    views=views,
                    favorites=favorites,
                    thumbnails=thumbnails,
                )

        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            print_exc()
            raise InternalServerError()

    @app.route("/search", methods=["POST", "GET"])
    def route_search():
        if request.method == "POST":
            query = request.form.get("q", "")
            logger.debug(f"Search request (POST) for: {query}")
        else:
            query = request.args.get("q", "")
            logger.debug(f"Search request (GET) for: {query}")

        return project_list(app, "Search")

    @app.route("/cron/")
    def cron():
        logger.debug("Manual cron update triggered")
        update_data(app)
        return "OK"

    @app.route("/privacypolicy/")
    def privacypolicy():
        """Display the privacy policy.

        The privacy policy is loaded from the file specified in the
        `STRUCTABLES_PRIVACY_FILE` environment variable. If that variable is
        unset or the file cannot be read, a default message is displayed.
        """
        logger.debug("Rendering privacy policy page")

        content = "No privacy policy found."

        path = app.config.get("PRIVACY_FILE")
        logger.debug(f"Privacy policy file path: {path}")

        if not path:
            if pathlib.Path("privacy.md").exists():
                path = "privacy.md"
                logger.debug("Found privacy.md in working directory")
            elif pathlib.Path("privacy.txt").exists():
                path = "privacy.txt"
                logger.debug("Found privacy.txt in working directory")

        if path:
            try:
                logger.debug(f"Reading privacy policy from {path}")
                with pathlib.Path(path).open() as f:
                    content = f.read()

                    if path.endswith(".md"):
                        logger.debug("Converting Markdown to HTML")
                        content = Markdown().convert(content)

            except OSError as e:
                logger.error(f"Error reading privacy policy file: {str(e)}")
                pass

        return render_template(
            "privacypolicy.html", title="Privacy Policy", content=content
        )

    @app.errorhandler(404)
    def not_found(e):
        logger.warning(f"404 error: {request.path}")
        return render_template("404.html"), 404

    @app.errorhandler(400)
    def bad_request(e):
        logger.warning(f"400 error: {request.path}")
        return render_template("400.html"), 400

    @app.errorhandler(429)
    def too_many_requests(e):
        logger.warning(f"429 error: {request.path}")
        return render_template("429.html"), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 error: {request.path}")
        return render_template("500.html"), 500
