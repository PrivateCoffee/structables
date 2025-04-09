from urllib.parse import urlencode, urlparse, quote
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import logging
import json
import math
from flask import request, render_template, abort

logger = logging.getLogger(__name__)

def proxy(url, filename=None):
    """Generate a proxy URL for external content.
    
    Args:
        url (str): The original URL to proxy.
        filename (str, optional): The filename to use for downloads.
        
    Returns:
        str: The proxied URL.
    """
    logger.debug(f"Generating proxy URL for {url}")
    return f"/proxy/?url={url}" + (f"&filename={filename}" if filename else "")

def get_typesense_api_key():
    """Extract the Typesense API key from Instructables.com.
    
    Returns:
        str: The Typesense API key.
    """
    logger.debug("Getting Typesense API key...")

    try:
        data = urlopen("https://www.instructables.com/")
        soup = BeautifulSoup(data.read().decode(), "html.parser")
        scripts = soup.select("script")

        for script in scripts:
            if "typesense" in script.text and (
                matches := re.search(r'"typesenseApiKey":\s?"(.*?)"', script.text)
            ):
                api_key = matches.group(1)
                logger.debug(f"Identified Typesense API key: {api_key[:5]}...")
                return api_key

        logger.error("Failed to get Typesense API key")
    except Exception as e:
        logger.error(f"Error getting Typesense API key: {str(e)}")

def unslugify(slug):
    """Return a list of possible original titles for a slug.

    Args:
        slug (str): The slug to unslugify.

    Returns:
        List[str]: A list of possible original titles for the slug.
    """
    logger.debug(f"Unslugifying: {slug}")
    results = []

    results.append(slug.replace("-", " ").title())

    if "and" in slug:
        results.append(results[0].replace("And", "&").title())

    logger.debug(f"Unslugify results: {results}")
    return results

def get_pagination(request, total, per_page=1):
    """Generate pagination links.
    
    Args:
        request: The Flask request object.
        total (int): The total number of items.
        per_page (int): The number of items per page.
        
    Returns:
        list: A list of pagination link dictionaries.
    """
    logger.debug(f"Generating pagination for {total} items, {per_page} per page")
    pagination = []

    args = request.args.copy()
    current = int(args.pop("page", 1))

    query_string = urlencode(args)

    total_pages = int(total / per_page)
    logger.debug(f"Total pages: {total_pages}, current page: {current}")

    if query_string:
        query_string = "&" + query_string

    if current > 1:
        pagination.append(
            {
                "link": f"?page={current - 1}{query_string}",
                "text": "Previous",
                "disabled": False,
                "active": False,
            }
        )

    for page in range(max(current - 5, 1), min(current + 5, total_pages)):
        if page == current:
            pagination.append(
                {
                    "link": f"?page={page}{query_string}",
                    "text": page,
                    "disabled": False,
                    "active": True,
                }
            )
        else:
            pagination.append(
                {
                    "link": f"?page={page}{query_string}",
                    "text": page,
                    "disabled": False,
                    "active": False,
                }
            )

    if current < total_pages:
        pagination.append(
            {
                "link": f"?page={current + 1}{query_string}",
                "text": "Next",
                "disabled": False,
                "active": False,
            }
        )

    logger.debug(f"Generated {len(pagination)} pagination links")
    return pagination

def member_header(header):
    """Extract member profile header information.
    
    Args:
        header: The BeautifulSoup header element.
        
    Returns:
        dict: The member header information.
    """
    logger.debug("Parsing member header")
    
    try:
        avatar = proxy(
            header.select("div.profile-avatar-container img.profile-avatar")[0].get("src")
        )
        title = header.select("div.profile-top div.profile-headline h1.profile-title")[
            0
        ].text

        location = header.select("span.member-location")
        if location != []:
            location = location[0].text
        else:
            location = 0

        signup = header.select("span.member-signup-date")
        if signup != []:
            signup = signup[0].text
        else:
            signup = 0

        instructables = header.select("span.ible-count")
        if instructables != []:
            instructables = instructables[0].text
        else:
            instructables = 0

        views = header.select("span.total-views")
        if views != []:
            views = views[0].text
        else:
            views = 0

        comments = header.select("span.total-comments")
        if comments != []:
            comments = comments[0].text
        else:
            comments = 0

        followers = header.select("span.follower-count")
        if followers != []:
            followers = followers[0].text
        else:
            followers = 0

        bio = header.select("span.member-bio")
        if bio != []:
            bio = bio[0].text
        else:
            bio = ""

        logger.debug(f"Parsed member header for {title}")
        
        return {
            "avatar": avatar,
            "title": title,
            "location": location,
            "signup": signup,
            "instructables": instructables,
            "views": views,
            "comments": comments,
            "followers": followers,
            "bio": bio,
        }
    except Exception as e:
        logger.error(f"Error parsing member header: {str(e)}")
        # Return a minimal header to avoid breaking the template
        return {
            "avatar": "",
            "title": "Unknown User",
            "location": "",
            "signup": "",
            "instructables": 0,
            "views": 0,
            "comments": 0,
            "followers": 0,
            "bio": "",
        }

def explore_lists(soup):
    """Parse the explore lists from the homepage.
    
    Args:
        soup: The BeautifulSoup element containing the list.
        
    Returns:
        list: A list of dictionaries with project information.
    """
    logger.debug("Parsing explore list")
    list_ = []
    try:
        for ible in soup.select(".home-content-explore-ible"):
            link = ible.a["href"]
            img = proxy(ible.select("a img")[0].get("data-src"))
            alt = ible.select("a img")[0].get("alt")
            title = ible.select("div strong a")[0].text
            author = ible.select("div span.ible-author a")[0].text
            author_link = ible.select("div span.ible-author a")[0].get("href")
            channel = ible.select("div span.ible-channel a")[0].text
            channel_link = ible.select("div span.ible-channel a")[0].get("href")
            views = 0
            if ible.select("span.ible-views") != []:
                views = ible.select("span.ible-views")[0].text
            favorites = 0
            if ible.select("span.ible-favorites") != []:
                favorites = ible.select("span.ible-favorites")[0].text
            list_.append(
                {
                    "link": link,
                    "img": img,
                    "alt": alt,
                    "title": title,
                    "author": author,
                    "author_link": author_link,
                    "channel": channel,
                    "channel_link": channel_link,
                    "favorites": favorites,
                    "views": views,
                }
            )
        logger.debug(f"Found {len(list_)} items in explore list")
    except Exception as e:
        logger.error(f"Error parsing explore list: {str(e)}")
    
    return list_

def project_list(app, head, sort="", per_page=20):
    """Generate a list of projects for display.
    
    Args:
        app: The Flask app instance.
        head (str): The header title.
        sort (str, optional): Sort description.
        per_page (int, optional): Number of items per page.
        
    Returns:
        Response: The rendered template.
    """
    head = f"{head + ' ' if head != '' else ''}Projects" + sort
    path = urlparse(request.path).path
    logger.debug(f"Generating project list for {path} with title '{head}'")

    page = request.args.get("page", 1, type=int)
    logger.debug(f"Page: {page}, per_page: {per_page}")

    if path in ("/projects/", "/projects"):
        logger.debug("Using global projects list")
        ibles = app.global_ibles["/projects"]
        total = len(ibles)
    else:
        if "projects" in path.split("/"):
            logger.debug("Fetching projects for category/channel")
            ibles = []

            parts = path.split("/")
            category = parts[1]
            channel = "" if parts[2] == "projects" else parts[2]
            
            logger.debug(f"Category: {category}, Channel: {channel}")

            channel_names = unslugify(channel)

            for channel_name in channel_names:
                logger.debug(f"Trying channel name: {channel_name}")
                project_ibles, total = projects_search(
                    app,
                    category=category,
                    channel=channel_name,
                    per_page=per_page,
                    page=page,
                )

                if project_ibles:
                    logger.debug(f"Found {len(project_ibles)} projects for {channel_name}")
                    break

        elif "search" in path.split("/"):
            logger.debug("Processing search request")
            ibles = []
            query = (
                request.args.get("q") if request.method == "GET" else request.form["q"]
            )
            logger.debug(f"Search query: {query}")

            project_ibles, total = projects_search(
                app,
                query=query,
                filter_by="",
                per_page=per_page,
                page=page,
                query_by="title,screenName",
            )
            logger.debug(f"Found {len(project_ibles)} search results")

        else:
            logger.warning(f"Invalid path: {path}")
            abort(404)

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

            ibles.append(
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
        
        logger.debug(f"Processed {len(ibles)} projects for display")

    pagination = get_pagination(request, total, per_page)
    logger.debug(f"Rendering project list template with {len(ibles)} projects")
    
    return render_template(
        "projects.html",
        title=unslugify(head)[0],
        ibles=ibles,
        path=path,
        pagination=pagination,
    )

def category_page(app, name, teachers=False):
    """Generate a category page.
    
    Args:
        app: The Flask app instance.
        name (str): The category name.
        teachers (bool, optional): Whether this is the teachers category.
        
    Returns:
        Response: The rendered template.
    """
    logger.debug(f"Generating category page for {name} (teachers={teachers})")
    path = urlparse(request.path).path
    page = request.args.get("page", 1, type=int)

    ibles = []
    channels = []
    contests = []

    # Get channels for this category
    for channel in app.global_ibles["/projects"]:
        if (
            channel["channel"].startswith(name.lower())
            and channel["channel"] not in channels
        ):
            channels.append(channel["channel"])
    
    logger.debug(f"Found {len(channels)} channels for category {name}")

    # Get featured projects
    if teachers:
        logger.debug("Fetching teachers projects")
        category_ibles, total = projects_search(
            app, teachers=True, page=page, filter_by="featureFlag:=true"
        )
    else:
        logger.debug(f"Fetching featured projects for category {name}")
        category_ibles, total = projects_search(
            app, category=name, page=page, filter_by="featureFlag:=true"
        )
    
    logger.debug(f"Found {len(category_ibles)} featured projects")

    for ible in category_ibles:
        link = f"/{ible['document']['urlString']}"
        img = proxy(ible['document']['coverImageUrl'])

        title = ible['document']['title']
        author = ible['document']['screenName']
        author_link = f"/member/{author}"

        channel = ible['document']['primaryClassification']
        channel_link = f"/channel/{channel}"

        views = ible['document']['views']
        favorites = ible['document']['favorites']

        ibles.append(
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

    logger.debug(f"Rendering category page template with {len(ibles)} projects")
    return render_template(
        "category.html",
        title=name,
        channels=channels,
        ibles=ibles,
        contests=contests,
        path=path,
    )

def projects_search(
    app,
    query="*",
    category="",
    teachers=False,
    channel="",
    filter_by="",
    page=1,
    per_page=50,
    query_by="title,stepBody,screenName",
    sort_by="publishDate:desc",
    timeout=5,
    typesense_api_key=None,
):
    """Search for projects using the Typesense API.
    
    Args:
        app: The Flask app instance.
        query (str, optional): The search query.
        category (str, optional): The category to filter by.
        teachers (bool, optional): Whether to filter for teacher projects.
        channel (str, optional): The channel to filter by.
        filter_by (str, optional): Additional filter criteria.
        page (int, optional): The page number.
        per_page (int, optional): The number of results per page.
        query_by (str, optional): The fields to query.
        sort_by (str, optional): The sort order.
        timeout (int, optional): The request timeout.
        typesense_api_key (str, optional): The Typesense API key.
        
    Returns:
        tuple: A tuple of (projects, total_pages).
    """
    # Build filter string
    if category:
        if filter_by:
            filter_by += " && "
        filter_by += f"category:={category}"

    if channel:
        if filter_by:
            filter_by += " && "
        filter_by += f"channel:={channel}"

    if teachers:
        if filter_by:
            filter_by += " && "
        filter_by += "teachers:=Teachers"

    query = quote(query)
    filter_by = quote(filter_by)

    logger.debug(f"Searching projects: query='{query}', filter='{filter_by}', page={page}, per_page={per_page}")

    projects_headers = {"x-typesense-api-key": app.config["TYPESENSE_API_KEY"]}

    request_args = {
        "q": query,
        "query_by": query_by,
        "page": page,
        "sort_by": sort_by,
        "include_fields": "title,urlString,coverImageUrl,screenName,favorites,views,primaryClassification,featureFlag,prizeLevel,IMadeItCount",
        "filter_by": filter_by,
        "per_page": per_page,
    }

    args_str = "&".join([f"{key}={value}" for key, value in request_args.items()])

    url = f"https://www.instructables.com/api_proxy/search/collections/projects/documents/search?{args_str}"
    logger.debug(f"Making request to {url}")
    
    try:
        projects_request = Request(url, headers=projects_headers)
        projects_data = urlopen(projects_request, timeout=timeout)
        project_obj = json.loads(projects_data.read().decode())
        project_ibles = project_obj["hits"]
        total_found = project_obj["found"]
        
        logger.debug(f"Search returned {len(project_ibles)} projects out of {total_found} total matches")
        
        return project_ibles, math.ceil(total_found / per_page)
    except Exception as e:
        logger.error(f"Error searching projects: {str(e)}")
        return [], 0