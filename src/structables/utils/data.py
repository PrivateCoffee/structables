from urllib.request import urlopen
import logging
from bs4 import BeautifulSoup
from .helpers import proxy, projects_search

logging.basicConfig(level=logging.DEBUG)


def update_data(app):
    logging.debug("Updating data...")

    channels = []

    try:
        app.global_ibles
    except AttributeError:
        app.global_ibles = {}

    sitemap_data = urlopen("https://www.instructables.com/sitemap/")
    sitemap_soup = BeautifulSoup(sitemap_data.read().decode(), "html.parser")
    main = sitemap_soup.select("div.sitemap-content")[0]

    for group in main.select("div.group-section"):
        channels.append(group.select("h2 a")[0].text.lower())

    app.global_ibles["/projects"] = []
    project_ibles, total = projects_search(app, filter_by="featureFlag:=true")

    while len(app.global_ibles["/projects"]) <= 0:
        for ible in project_ibles:
            link = f"/{ible['document']['urlString']}"
            img = proxy(ible["document"]["coverImageUrl"])

            title = ible["document"]["title"]
            author = ible["document"]["screenName"]
            author_link = f"/member/{author}"

            channel = ible["document"]["primaryClassification"]
            channel_link = f"/channel/{channel}"

            views = ible["document"]["views"]
            favorites = ible["document"]["favorites"]

            app.global_ibles["/projects"].append(
                {
                    "link": link,
                    "img": img,
                    "title": title,
                    "author": author,
                    "author_link": author_link,
                    "channel": channel,
                    "channel_link": channel_link,
                    "views": views,
                    "favorites": favorites,
                }
            )
