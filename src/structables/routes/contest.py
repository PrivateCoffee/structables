from flask import render_template, request, abort, url_for
from urllib.request import urlopen, Request
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
                "link": url_for("route_contest", contest=contest["urlString"]),
                "deadline": contest["deadline"],
                "startDate": contest["startDate"],
                "numEntries": contest["numEntries"],
                "state": contest["state"],
                "bannerUrl": proxy(contest["bannerUrlMedium"]),
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
            "limit": limit,
        }

        return render_template(
            "archives.html",
            title=f"Contest Archives (Page {page})",
            page=page,
            pagination=pagination,
            contest_list=contest_list,
        )

    def get_entries(contest):
        base_url = f"https://www.instructables.com/api_proxy/search/collections/projects/documents/search"
        headers = {"x-typesense-api-key": app.typesense_api_key}
        page, per_page = 1, 100
        all_entries = []

        while True:
            try:
                url = f"{base_url}?q=*&filter_by=contestPath:{contest}&sort_by=contestEntryDate:desc&per_page={per_page}&page={page}"
                request = Request(url, headers=headers)
                response = urlopen(request)
                data = json.loads(response.read().decode())
            except HTTPError as e:
                abort(e.code)

            hits = data.get("hits", [])
            if not hits:
                break

            all_entries.extend(hits)
            if len(hits) < per_page:
                break
            page += 1

        return all_entries

    @app.route("/contest/<contest>/")
    def route_contest(contest):
        try:
            data = urlopen(f"https://www.instructables.com/contest/{contest}/")
            html = data.read().decode()
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("h1")
            title = title_tag.get_text() if title_tag else "Contest"

            img_tag = soup.find("img", alt=lambda x: x and "Banner" in x)
            img = img_tag.get("src") if img_tag else "default.jpg"

            entry_count = len(get_entries(contest))
            prizes_items = soup.select("article")
            prizes = len(prizes_items) if prizes_items else 0

            overview_section = soup.find("section", id="overview")
            info = (
                overview_section.decode_contents()
                if overview_section
                else "No Overview"
            )

        except HTTPError as e:
            abort(e.code)

        entry_list = []
        entries = get_entries(contest)
        for entry in entries:
            doc = entry["document"]
            entry_details = {
                "link": url_for("route_article", article=doc["urlString"]),
                "entry_img": doc["coverImageUrl"],
                "entry_title": doc["title"],
                "author": doc["screenName"],
                "author_link": url_for("route_member", member=doc["screenName"]),
                "channel": doc["channel"][0],
                "channel_link": f"/{doc['primaryClassification']}",
                "views": doc.get("views", 0),
            }
            entry_list.append(entry_details)

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
            # Fetch current contests from the JSON API
            response = urlopen(
                "https://www.instructables.com/json-api/getCurrentContests?limit=50&offset=0"
            )
            data = json.loads(response.read().decode())
        except HTTPError as e:
            abort(e.code)
        except Exception as e:
            abort(500)  # Handle other exceptions such as JSON decode errors

        contests = data.get("contests", [])
        contest_list = []
        for contest in contests:
            contest_details = {
                "link": url_for("route_contest", contest=contest["urlString"]),
                "img": proxy(contest["bannerUrlMedium"]),
                "alt": contest["title"],
                "title": contest["title"],
                "deadline": contest["deadline"],
                "prizes": contest["prizeCount"],
                "entries": contest["numEntries"],
            }
            contest_list.append(contest_details)

        return render_template(
            "contests.html",
            title="Contests",
            contest_count=len(contest_list),
            contests=contest_list,
        )
