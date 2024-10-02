from flask import render_template, request, abort
from urllib.request import urlopen
from urllib.error import HTTPError
from ..utils.helpers import proxy
from bs4 import BeautifulSoup
import json


def init_contest_routes(app):
    @app.route("/contest/archive/")
    def route_contest_archive():
        # Default pagination settings
        limit = 10
        page = request.args.get("page", default=1, type=int)
        offset = (page - 1) * limit

        try:
            # Fetch data using urlopen
            url = f"https://www.instructables.com/json-api/getClosedContests?limit={limit}&offset={offset}"
            response = urlopen(url)
            data = json.loads(response.read().decode())
        except HTTPError as e:
            abort(e.code)
        except Exception as e:
            abort(500)  # Handle other exceptions like JSON decode errors

        contests = data.get("contests", [])
        full_list_size = data.get("fullListSize", 0)

        contest_list = []
        for contest in contests:
            contest_details = {
                "title": contest["title"],
                "link": f"https://www.instructables.com/{contest['urlString']}",
                "deadline": contest["deadline"],
                "startDate": contest["startDate"],
                "numEntries": contest["numEntries"],
                "state": contest["state"],
                "bannerUrl": contest["bannerUrlMedium"],
            }
            contest_list.append(contest_details)

        # Calculate total pages
        total_pages = (full_list_size + limit - 1) // limit

        # Create pagination
        pagination = {
            "current_page": page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages,
            "limit": limit
        }

        return render_template(
            "archives.html",
            title=f"Contest Archives (Page {page})",
            page=page,
            pagination=pagination,
            contest_list=contest_list,
        )

    @app.route("/contest/<contest>/")
    def route_contest(contest):
        try:
            data = urlopen(f"https://www.instructables.com/contest/{contest}/")
        except HTTPError as e:
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        title = soup.select('meta[property="og:title"]')[0].get("content")

        body = soup.select("div#contest-wrapper")[0]

        img = proxy(body.select("div#contest-masthead img")[0].get("src"))

        entry_count = body.select("li.entries-nav-btn")[0].text.split(" ")[0]
        prizes = body.select("li.prizes-nav-btn")[0].text.split(" ")[0]

        info = body.select("div.contest-body-column-left")[0]
        info.select("div#site-announcements-page")[0].decompose()
        info.select("h3")[0].decompose()
        info.select("div#contest-body-nav")[0].decompose()
        info = str(info).replace("https://www.instructables.com", "/")

        body.select("span.contest-entity-count")[0].text

        entry_list = []
        for entry in body.select(
            "div.contest-entries-list div.contest-entries-list-ible"
        ):
            link = entry.a["href"]
            entry_img = proxy(entry.select("a noscript img")[0].get("src"))
            entry_title = entry.select("a.ible-title")[0].text
            author = entry.select("div span.ible-author a")[0].text
        author_link = entry.select("div span.ible-author a")[0].get("href")
        channel = entry.select("div span.ible-channel a")[0].text
        channel_link = entry.select("div span.ible-channel a")[0].get("href")
        views = entry.select(".ible-views")[0].text

        entry_list.append(
            {
                "link": link,
                "entry_img": entry_img,
                "entry_title": entry_title,
                "author": author,
                "author_link": author_link,
                "channel": channel,
                "channel_link": channel_link,
                "views": views,
            }
        )

        return render_template(
            "contest.html",
            title=title,
            img=img,
            entry_count=entry_count,
            prizes=prizes,
            info=info,
            entry_list=entry_list,
        )

    @app.route("/contest/")
    def route_contests():
        try:
            data = urlopen("https://www.instructables.com/contest/")
        except HTTPError as e:
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        contest_count = "0"

        contests = []
        for contest in soup.select("div#cur-contests div.row-fluid div.contest-banner"):
            link = contest.select("div.contest-banner-inner a")[0].get("href")
            img = proxy(contest.select("div.contest-banner-inner a img")[0].get("src"))
            alt = contest.select("div.contest-banner-inner a img")[0].get("alt")
            deadline = contest.select("span.contest-meta-deadline")[0].get(
                "data-deadline"
            )
            prizes = contest.select("span.contest-meta-count")[0].text
            entries = contest.select("span.contest-meta-count")[1].text

            contests.append(
                {
                    "link": link,
                    "img": img,
                    "alt": alt,
                    "deadline": deadline,
                    "prizes": prizes,
                    "entries": entries,
                }
            )

        closed = []
        for display in soup.select("div.contest-winner-display"):
            link = display.select("div.contest-banner-inner a")[0].get("href")
            img = proxy(display.select("div.contest-banner-inner a img")[0].get("src"))
            alt = display.select("div.contest-banner-inner a img")[0].get("alt")
            featured_items = []
            for featured_item in display.select("ul.featured-items li"):
                item_link = featured_item.select("div.ible-thumb a")[0].get("href")
                item_img = proxy(
                    featured_item.select("div.ible-thumb a img")[0].get("src")
                )
                item_title = featured_item.select("a.title")[0].text
                item_author = featured_item.select("a.author")[0].text
                item_author_link = featured_item.select("a.author")[0].get("href")

                featured_items.append(
                    {
                        "link": item_link,
                        "img": item_img,
                        "title": item_title,
                        "author": item_author,
                        "author_link": item_author_link,
                    }
                )
            closed.append(
                {"link": link, "img": img, "alt": alt, "featured_items": featured_items}
            )

        return render_template(
            "contests.html",
            title="Contests",
            contest_count=contest_count,
            contests=contests,
            closed=closed,
        )
