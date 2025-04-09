from flask import render_template, request, abort, url_for
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from ..utils.helpers import proxy
from bs4 import BeautifulSoup
import json
import logging

logger = logging.getLogger(__name__)


def init_contest_routes(app):
    @app.route("/contest/archive/")
    def route_contest_archive():
        # Default pagination settings
        limit = 10
        page = request.args.get("page", default=1, type=int)
        offset = (page - 1) * limit

        logger.debug(f"Fetching contest archive page {page} with limit {limit}")

        try:
            # Fetch data using urlopen
            url = f"https://www.instructables.com/json-api/getClosedContests?limit={limit}&offset={offset}"
            logger.debug(f"Making request to {url}")
            response = urlopen(url)
            data = json.loads(response.read().decode())
            logger.debug(
                f"Received contest archive data with {len(data.get('contests', []))} contests"
            )
        except HTTPError as e:
            logger.error(f"HTTP error fetching contest archive: {e.code}")
            abort(e.code)
        except Exception as e:
            logger.error(f"Error fetching contest archive: {str(e)}")
            abort(500)  # Handle other exceptions like JSON decode errors

        contests = data.get("contests", [])
        full_list_size = data.get("fullListSize", 0)
        logger.debug(f"Total contests in archive: {full_list_size}")

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
        logger.debug(f"Pagination: page {page}/{total_pages}")

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
        base_url = "https://www.instructables.com/api_proxy/search/collections/projects/documents/search"
        headers = {"x-typesense-api-key": app.config["TYPESENSE_API_KEY"]}
        page, per_page = 1, 100
        all_entries = []

        logger.debug(f"Fetching entries for contest: {contest}")

        while True:
            try:
                url = f"{base_url}?q=*&filter_by=contestPath:{contest}&sort_by=contestEntryDate:desc&per_page={per_page}&page={page}"
                logger.debug(f"Making request to {url} (page {page})")
                request = Request(url, headers=headers)
                response = urlopen(request)
                data = json.loads(response.read().decode())
            except HTTPError as e:
                logger.error(f"HTTP error fetching contest entries: {e.code}")
                abort(e.code)

            hits = data.get("hits", [])
            logger.debug(f"Received {len(hits)} entries on page {page}")

            if not hits:
                break

            all_entries.extend(hits)
            if len(hits) < per_page:
                break
            page += 1

        logger.debug(f"Total entries fetched: {len(all_entries)}")
        return all_entries

    @app.route("/contest/<contest>/")
    def route_contest(contest):
        logger.debug(f"Fetching contest page for: {contest}")

        try:
            data = urlopen(f"https://www.instructables.com/contest/{contest}/")
            html = data.read().decode()
            soup = BeautifulSoup(html, "html.parser")

            title_tag = soup.find("h1")
            title = title_tag.get_text() if title_tag else "Contest"
            logger.debug(f"Contest title: {title}")

            img_tag = soup.find("img", alt=lambda x: x and "Banner" in x)
            img = img_tag.get("src") if img_tag else "default.jpg"

            logger.debug(f"Fetching entries for contest: {contest}")
            entries = get_entries(contest)
            entry_count = len(entries)
            logger.debug(f"Found {entry_count} entries")

            prizes_items = soup.select("article")
            prizes = len(prizes_items) if prizes_items else 0
            logger.debug(f"Found {prizes} prizes")

            overview_section = soup.find("section", id="overview")
            info = (
                overview_section.decode_contents()
                if overview_section
                else "No Overview"
            )

        except HTTPError as e:
            logger.error(f"HTTP error fetching contest page: {e.code}")
            abort(e.code)

        entry_list = []
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
        logger.debug("Fetching current contests")

        try:
            # Fetch current contests from the JSON API
            response = urlopen(
                "https://www.instructables.com/json-api/getCurrentContests?limit=50&offset=0"
            )
            data = json.loads(response.read().decode())
            logger.debug("Received current contests data")
        except HTTPError as e:
            logger.error(f"HTTP error fetching current contests: {e.code}")
            abort(e.code)
        except Exception as e:
            logger.error(f"Error fetching current contests: {str(e)}")
            abort(500)  # Handle other exceptions such as JSON decode errors

        contests = data.get("contests", [])
        logger.debug(f"Found {len(contests)} current contests")

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
