from flask import render_template, abort
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.parse import quote
from ..utils.helpers import proxy, member_header
from bs4 import BeautifulSoup
from urllib.request import Request
import logging

logger = logging.getLogger(__name__)

def init_member_routes(app):
    """This function initializes all the routes related to Instructables member profiles.

    Args:
        app (Flask): The Flask app instance.
    """

    @app.route("/member/<member>/instructables/")
    def route_member_instructables(member):
        """Route to display a member's Instructables.

        Args:
            member (str): The member's username.

        Returns:
            Response: The rendered HTML page.
        """
        logger.debug(f"Fetching instructables for member: {member}")
        member = quote(member)

        try:
            logger.debug(f"Making request to https://www.instructables.com/member/{member}/instructables/")
            data = urlopen(
                f"https://www.instructables.com/member/{member}/instructables/"
            )
        except HTTPError as e:
            logger.error(f"HTTP error fetching member instructables: {e.code}")
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        header = soup.select(".profile-header.profile-header-social")[0]
        header_content = member_header(header)
        logger.debug(f"Parsed member header for {header_content['title']}")

        ibles = soup.select("ul.ible-list-items")[0]
        ible_list = []
        for ible in ibles.select("li"):
            link = ible.select("div.thumbnail-image")[0].a.get("href")
            img = proxy(ible.select("div.thumbnail-image a noscript img")[0].get("src"))
            title = ible.select("div.caption-inner a.title")[0].text

            stats = ible.select("div.ible-stats-right-col")[0]
            views = 0
            if stats.select("span.ible-views") != []:
                views = stats.select("span.ible-views")[0].text
            favorites = 0
            if stats.select("span.ible-favorites") != []:
                favorites = stats.select("span.ible-favorites")[0].text

            ible_list.append(
                {
                    "link": link,
                    "img": img,
                    "title": title,
                    "views": views,
                    "favorites": favorites,
                }
            )
        
        logger.debug(f"Found {len(ible_list)} instructables for member {member}")

        return render_template(
            "member-instructables.html",
            title=f"{header_content['title']}'s Instructables",
            header_content=header_content,
            ibles=ible_list,
        )

    @app.route("/member/<member>/")
    def route_member(member):
        """Route to display a member's profile.

        Args:
            member (str): The member's username.

        Returns:
            Response: The rendered HTML page.
        """
        logger.debug(f"Fetching profile for member: {member}")
        member = quote(member)

        request = Request(f"https://www.instructables.com/member/{member}/")

        try:
            logger.debug(f"Making request to https://www.instructables.com/member/{member}/")
            data = urlopen(request)
        except HTTPError as e:
            logger.error(f"HTTP error fetching member profile: {e.code}")
            abort(e.code)

        soup = BeautifulSoup(data.read().decode(), "html.parser")

        header_content = member_header(soup)
        logger.debug(f"Parsed member header for {header_content['title']}")

        body = soup.select("div.member-profile-body")[0]

        ible_list = body.select(".boxed-content.promoted-content")

        ible_list_title = ""
        ibles = []

        if ible_list != []:
            ible_list = ible_list[0]
            ible_list_title = ible_list.select("h2.module-title")[0].text
            logger.debug(f"Found promoted content: {ible_list_title}")
            
            for ible in ible_list.select("ul.promoted-items li"):
                ible_title = ible.get("data-title")
                ible_link = ible.select("div.image-wrapper")[0].a.get("href")
                ible_img = proxy(ible.select("div.image-wrapper a img")[0].get("src"))

                ibles.append({"title": ible_title, "link": ible_link, "img": ible_img})
            
            logger.debug(f"Found {len(ibles)} promoted instructables")

        ach_list = body.select(
            "div.two-col-section div.right-col-section.centered-sidebar div.boxed-content.about-me"
        )

        ach_list_title = ""
        achs = []

        if len(ach_list) > 1:
            ach_list = ach_list[1]
            ach_list_title = ach_list.select("h2.module-title")[0].text
            logger.debug(f"Found achievements section: {ach_list_title}")
            
            for ach in ach_list.select(
                "div.achievements-section.main-achievements.contest-achievements div.achievement-item:not(.two-column-filler)"
            ):
                try:
                    ach_title = ach.select(
                        "div.achievement-info span.achievement-title"
                    )[0].text
                    ach_desc = ach.select(
                        "div.achievement-info span.achievement-description"
                    )[0].text
                    achs.append([ach_title, ach_desc])
                except IndexError:
                    logger.warning("Failed to parse an achievement item")
                    pass
            
            logger.debug(f"Found {len(achs)} achievements")

        return render_template(
            "member.html",
            title=header_content["title"] + "'s Profile",
            header_content=header_content,
            ible_list_title=ible_list_title,
            ibles=ibles,
            ach_list_title=ach_list_title,
            achs=achs,
        )