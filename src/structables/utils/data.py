from urllib.request import urlopen
import logging
import time
from bs4 import BeautifulSoup
from .helpers import proxy, projects_search

logger = logging.getLogger(__name__)

# Track the last data update time
last_data_update = 0

def update_data(app):
    """Update the application's cached data.
    
    This function fetches fresh data from Instructables.com and updates
    the app's global cache.
    
    Args:
        app: The Flask app instance.
    """
    logger.debug("Starting data update")

    channels = []

    try:
        app.global_ibles
    except AttributeError:
        logger.debug("Initializing global_ibles dictionary")
        app.global_ibles = {}

    try:
        logger.debug("Fetching sitemap data from instructables.com")
        sitemap_data = urlopen("https://www.instructables.com/sitemap/")
        sitemap_soup = BeautifulSoup(sitemap_data.read().decode(), "html.parser")
        main = sitemap_soup.select("div.sitemap-content")[0]

        for group in main.select("div.group-section"):
            channels.append(group.select("h2 a")[0].text.lower())
        
        logger.debug(f"Found {len(channels)} channels in sitemap")

        logger.debug("Fetching featured projects")
        app.global_ibles["/projects"] = []
        project_ibles, total = projects_search(app, filter_by="featureFlag:=true")
        
        logger.debug(f"Found {len(project_ibles)} featured projects")

        while len(app.global_ibles["/projects"]) <= 0:
            for ible in project_ibles:
                link = f"/{ible['document']['urlString']}"
                img = proxy(ible['document']['coverImageUrl'])

                title = ible['document']['title']
                author = ible['document']['screenName']
                author_link = f"/member/{author}"

                channel = ible['document']['primaryClassification']
                channel_link = f"/channel/{channel}"

                views = ible['document']['views']
                favorites = ible['document']['favorites']

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
        
        logger.debug(f"Updated global projects list with {len(app.global_ibles['/projects'])} projects")
        logger.debug("Data update completed successfully")
    except Exception as e:
        logger.error(f"Error updating data: {str(e)}")


def maybe_update_data(app):
    """Updates the data if it's time to do so.

    This replaces the background thread with a request-triggered update.

    Args:
        app (Flask): The Flask app instance.
    """
    global last_data_update
    current_time = time.time()
    
    # Update every 5 minutes (300 seconds)
    if current_time - last_data_update >= 300:
        logger.debug("Running scheduled data update")
        update_data(app)
        last_data_update = current_time
        logger.debug("Data update complete")