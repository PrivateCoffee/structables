from urllib.parse import urlencode, urlparse, quote
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
import logging
import json
from flask import request, render_template, abort

logging.basicConfig(level=logging.DEBUG)


def proxy(url, filename=None):
    logging.debug(f"Generating proxy URL for {url}")
    return f"/proxy/?url={url}" + (f"&filename={filename}" if filename else "")


def get_typesense_api_key():
    logging.debug("Getting Typesense API key...")

    data = urlopen("https://www.instructables.com/")
    soup = BeautifulSoup(data.read().decode(), "html.parser")
    scripts = soup.select("script")

    for script in scripts:
        if "typesense" in script.text and (
            matches := re.search(r'"typesenseApiKey":\s?"(.*?)"', script.text)
        ):
            api_key = matches.group(1)
            logging.debug(f"Identified Typesense API key as {api_key}")
            return api_key

    logging.error("Failed to get Typesense API key")


def unslugify(slug):
    """Return a list of possible original titles for a slug.

    Args:
        slug (str): The slug to unslugify.

    Returns:
        List[str]: A list of possible original titles for the slug.
    """
    results = []

    results.append(slug.replace("-", " ").title())

    if "and" in slug:
        results.append(results[0].replace("And", "&").title())

    return results


def get_pagination(request, total, per_page=1):
    pagination = []

    args = request.args.copy()
    current = int(args.pop("page", 1))

    query_string = urlencode(args)

    total_pages = int(total / per_page)

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

    return pagination


def member_header(header):
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


def explore_lists(soup):
    list_ = []
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
    return list_


def project_list(app, head, sort="", per_page=20):
    head = f"{head + ' ' if head != '' else ''}Projects" + sort
    path = urlparse(request.path).path

    page = request.args.get("page", 1, type=int)

    if path in ("/projects/", "/projects"):
        ibles = app.global_ibles["/projects"]
        total = len(ibles)
    else:
        if "projects" in path.split("/"):
            ibles = []

            parts = path.split("/")
            category = parts[1]
            channel = "" if parts[2] == "projects" else parts[2]

            channel_names = unslugify(channel)

            for channel_name in channel_names:
                project_ibles, total = projects_search(
                    app,
                    category=category,
                    channel=channel_name,
                    per_page=per_page,
                    page=page,
                )

                if project_ibles:
                    break

        elif "search" in path.split("/"):
            ibles = []
            query = (
                request.args.get("q") if request.method == "GET" else request.form["q"]
            )

            project_ibles, total = projects_search(
                app,
                query=query,
                filter_by="",
                per_page=per_page,
                page=page,
                query_by="title,screenName",
            )

        else:
            abort(404)

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

    return render_template(
        "projects.html",
        title=unslugify(head)[0],
        ibles=ibles,
        path=path,
        pagination=get_pagination(request, total, per_page),
    )


def category_page(app, name, teachers=False):
    path = urlparse(request.path).path
    page = request.args.get("page", 1, type=int)

    ibles = []

    channels = []
    contests = []

    for channel in app.global_ibles["/projects"]:
        if (
            channel["channel"].startswith(name.lower())
            and channel["channel"] not in channels
        ):
            channels.append(channel["channel"])

    if teachers:
        category_ibles, total = projects_search(
            app, teachers=True, page=page, filter_by="featureFlag:=true"
        )
    else:
        category_ibles, total = projects_search(
            app, category=name, page=page, filter_by="featureFlag:=true"
        )

    for ible in category_ibles:
        link = f"/{ible['document']['urlString']}"
        img = proxy(ible["document"]["coverImageUrl"])

        title = ible["document"]["title"]
        author = ible["document"]["screenName"]
        author_link = f"/member/{author}"

        channel = ible["document"]["primaryClassification"]
        channel_link = f"/channel/{channel}"

        views = ible["document"]["views"]
        favorites = ible["document"]["favorites"]

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

    logging.debug(
        f"Searching projects with query {query} and filter {filter_by}, page {page}"
    )

    projects_headers = {"x-typesense-api-key": app.typesense_api_key}

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

    projects_request = Request(
        f"https://www.instructables.com/api_proxy/search/collections/projects/documents/search?{args_str}",
        headers=projects_headers,
    )

    projects_data = urlopen(projects_request, timeout=timeout)
    project_obj = json.loads(projects_data.read().decode())
    project_ibles = project_obj["hits"]

    logging.debug(f"Got {len(project_ibles)} projects")

    return project_ibles, project_obj["out_of"]


def update_data(app):
    logging.debug("Updating data...")

    channels = []

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
