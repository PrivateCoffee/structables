from flask import render_template, abort
from urllib.request import urlopen
from urllib.error import HTTPError
from bs4 import BeautifulSoup
from urllib.parse import quote
from werkzeug.exceptions import InternalServerError
from markdown2 import Markdown
from traceback import print_exc
import pathlib
import json

from ..utils.data import update_data
from ..utils.helpers import explore_lists, proxy
from .category import project_list


def init_main_routes(app):
    @app.route("/")
    def route_explore():
        try:
            data = urlopen("https://www.instructables.com/")
        except HTTPError as e:
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        explore = soup.select(".home-content-explore-wrap")[0]

        title = explore.select("h2")[0].text

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
        try:
            data = urlopen("https://www.instructables.com/sitemap/" + path)
        except HTTPError as e:
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        main = soup.select("div.sitemap-content")[0]

        group_section = main.select("div.group-section")

        if group_section:
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

        else:
            groups = []
            channels = []
            for li in main.select("ul.sitemap-listing li"):
                channel = li.a.text
                channel_link = li.a["href"]

                if channel_link.startswith("https://"):
                    channel_link = f'/{"/".join(channel_link.split("/")[3:])}'

                channels.append([channel, channel_link])
            groups.append(["", "", channels])

        return render_template("sitemap.html", title="Sitemap", groups=groups)

    @app.route("/<article>/")
    def route_article(article):
        try:
            data = urlopen(
                f"https://www.instructables.com/json-api/showInstructableModel?urlString={article}"
            )
            data = json.loads(data.read().decode())
        except HTTPError as e:
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

            if "steps" in data:
                steps = []

                if "supplies" in data:
                    supplies = data["supplies"]

                    supplies_files = []

                    if "suppliesFiles" in data:
                        supplies_files = data["suppliesFiles"]

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

                    step_imgs = []
                    step_videos = []  # TODO: Check if this is still required
                    step_iframes = []
                    step_downloads = []

                    for file in step["files"]:
                        if file["image"] and "embedType" not in "file":
                            step_imgs.append(
                                {
                                    "src": proxy(file["downloadUrl"], file["name"]),
                                    "alt": file["name"],
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

                                if src.startswith("https://content.instructables.com"):
                                    src = src.replace(
                                        "https://content.instructables.com",
                                        f"/proxy/?url={src}",
                                    )

                                elif app.config["INVIDIOUS"] and src.startswith(
                                    "https://www.youtube.com"
                                ):
                                    src = src.replace(
                                        "https://www.youtube.com",
                                        app.config["INVIDIOUS"],
                                    )

                                elif not app.config["UNSAFE"]:
                                    src = "/iframe/?url=" + quote(src)

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
                    steps.append(
                        {
                            "title": step_title,
                            "imgs": step_imgs,
                            "text": step_text,
                            "videos": step_videos,
                            "iframes": step_iframes,
                            "downloads": step_downloads,
                        }
                    )

                comments_list = []
                comment_count = 0

                # TODO: Fix comments

                # comments = body.select("section.discussion")[0]

                # comment_count = comments.select("h2")[0].text
                # comment_list = comments.select("div.posts")

                # if comment_list != []:
                #     comment_list = comment_list[0]
                #     comments_list = []
                #     replies_used = 0
                #     for comment in comment_list.select(".post.js-comment:not(.reply)"):
                #         comment_votes = comment.select(".votes")[0].text
                #         comment_author_img_src = proxy(comment.select(".avatar a noscript img")[0].get("src"))
                #         comment_author_img_alt = comment.select(".avatar a noscript img")[0].get("alt")
                #         comment_author = comment.select(".posted-by a")[0].text
                #         comment_author_link = comment.select(".posted-by a")[0].get("href")
                #         comment_date = comment.select(".posted-by p.posted-date")[0].text
                #         comment_text = comment.select("div.text p")[0]
                #         comment_reply_count = comment.select("button.js-show-replies")
                #         if comment_reply_count != []:
                #             comment_reply_count = comment_reply_count[0].get("data-num-hidden")
                #         else:
                #             comment_reply_count = 0
                #         reply_list = []
                #         for index, reply in enumerate(comment_list.select(".post.js-comment:not(.reply) ~ .post.js-comment.reply.hide:has(~.post.js-comment:not(.reply))")[replies_used:int(comment_reply_count) + replies_used]):
                #             reply_votes = reply.select(".votes")[0].text
                #             reply_author_img_src = proxy(reply.select(".avatar a noscript img")[0].get("src"))
                #             reply_author_img_alt = reply.select(".avatar a noscript img")[0].get("alt")
                #             reply_author = reply.select(".posted-by a")[0].text
                #             reply_author_link = reply.select(".posted-by a")[0].get("href")
                #             reply_date = reply.select(".posted-by p.posted-date")[0].text
                #             reply_text = reply.select("div.text p")[0]

                #             reply_list.append([reply_votes, reply_author_img_src, reply_author_img_alt, reply_author, reply_author_link, reply_date, reply_text])
                #         replies_used += 1

                #         comments_list.append([comment_votes, comment_author_img_src, comment_author_img_alt, comment_author, comment_author_link, comment_date, comment_text, comment_reply_count, reply_list])
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

        except Exception:
            print_exc()
            raise InternalServerError()

    @app.route("/search", methods=["POST", "GET"])
    def route_search():
        return project_list(app, "Search")

    @app.route("/cron/")
    def cron():
        update_data(app)
        return "OK"

    @app.route("/privacypolicy/")
    def privacypolicy():
        """Display the privacy policy.

        The privacy policy is loaded from the file specified in the
        `STRUCTABLES_PRIVACY_FILE` environment variable. If that variable is
        unset or the file cannot be read, a default message is displayed.
        """

        content = "No privacy policy found."

        path = app.config.get("PRIVACY_FILE")

        if not path:
            if pathlib.Path("privacy.md").exists():
                path = "privacy.md"

            elif pathlib.Path("privacy.txt").exists():
                path = "privacy.txt"

        if path:
            try:
                with pathlib.Path(path).open() as f:
                    content = f.read()

                    if path.endswith(".md"):
                        content = Markdown().convert(content)

            except OSError:
                pass

        return render_template(
            "privacypolicy.html", title="Privacy Policy", content=content
        )

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(400)
    def bad_request(e):
        return render_template("400.html"), 400

    @app.errorhandler(429)
    def too_many_requests(e):
        return render_template("429.html"), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template("500.html"), 500
