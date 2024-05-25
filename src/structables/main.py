#!/usr/bin/env python

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    Response,
)

from urllib.parse import quote, unquote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from traceback import print_exc
from urllib.parse import urlparse
from argparse import ArgumentParser
from typing import List

from werkzeug.exceptions import BadRequest, abort, InternalServerError, NotFound
from bs4 import BeautifulSoup

import os
import json
import re
import logging
import pathlib

logging.basicConfig(level=logging.DEBUG)

global_ibles = {}


def proxy(url):
    logging.debug(f"Generating proxy URL for {url}")
    return f"/proxy/?url={url}"


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


TYPESENSE_API_KEY = get_typesense_api_key()

debugmode = False
invidious = None
unsafe = False


def unslugify(slug: str) -> List[str]:
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


def projects_search(
    query="*",
    category="",
    channel="",
    filter_by="",
    page=1,
    per_page=50,
    query_by="title,stepBody,screenName",
    sort_by="publishDate:desc",
    timeout=5,
):
    if category:
        if filter_by:
            filter_by += " && "
        filter_by += f"category:={category}"

    if channel:
        if filter_by:
            filter_by += " && "
        filter_by += f"channel:={channel}"

    query = quote(query)
    filter_by = quote(filter_by)

    logging.debug(
        f"Searching projects with query {query} and filter {filter_by}, page {page}"
    )

    projects_headers = {"x-typesense-api-key": TYPESENSE_API_KEY}

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


def update_data():
    logging.debug("Updating data...")

    channels = []

    sitemap_data = urlopen("https://www.instructables.com/sitemap/")
    sitemap_soup = BeautifulSoup(sitemap_data.read().decode(), "html.parser")
    main = sitemap_soup.select("div.sitemap-content")[0]

    for group in main.select("div.group-section"):
        channels.append(group.select("h2 a")[0].text.lower())

    global_ibles["/projects"] = []
    project_ibles, total = projects_search(filter_by="featureFlag:=true")

    while len(global_ibles["/projects"]) <= 0:
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

            global_ibles["/projects"].append(
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


app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/cron/")
def cron():
    update_data()
    return "OK"


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


def member_header(header):
    avatar = proxy(
        header.select("div.profile-avatar-container img.profile-avatar")[0].get("src")
    )
    title = header.select("div.profile-top div.profile-headline h1.profile-title")[
        0
    ].text

    header.select("div.profile-top")[0]

    # stats_text = profile_top.select("div.profile-header-stats")[0]
    # stats_num = header.select("div.profile-top div.profile-header-stats")[1]

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


def category_page(name, teachers=False):
    path = urlparse(request.path).path
    page = request.args.get("page", 1, type=int)

    ibles = []

    channels = []
    contests = []

    for channel in global_ibles["/projects"]:
        if (
            channel["channel"].startswith(name.lower())
            and channel["channel"] not in channels
        ):
            channels.append(channel["channel"])

    category_ibles, total = projects_search(
        category=name, page=page, filter_by="featureFlag:=true"
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


def project_list(head, sort="", per_page=20):
    head = f"{head + ' ' if head != '' else ''}Projects" + sort
    path = urlparse(request.path).path

    page = request.args.get("page", 1, type=int)

    if path in ("/projects/", "/projects"):
        ibles = global_ibles["/projects"]
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
        title=head,
        ibles=ibles,
        path=path,
        pagination=get_pagination(request, total, per_page),
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


@app.route("/contest/archive/")
def route_contest_archive():
    page = 1
    if request.args.get("page") is not None:
        page = request.args.get("page")

    try:
        data = urlopen(f"https://www.instructables.com/contest/archive/?page={page}")
    except HTTPError as e:
        abort(e.code)

    soup = BeautifulSoup(data.read().decode(), "html.parser")

    main = soup.select("div#contest-archive-wrapper")[0]

    contest_count = main.select("p.contest-count")[0].text

    contest_list = []
    for index, year in enumerate(main.select("div.contest-archive-list h2")):
        year_list = main.select(
            "div.contest-archive-list div.contest-archive-list-year"
        )[index]
        year_name = year.text
        month_list = []
        for month in year_list.select("div.contest-archive-list-month"):
            month_name = month.select("h3")[0].text
            month_contest_list = []
            for p in month.select("p"):
                date = p.select("span")[0].text
                link = p.select("a")[0].get("href")
                title = p.select("a")[0].text
                month_contest_list.append([date, link, title])
            month_list.append([month_name, month_contest_list])
        contest_list.append([year_name, month_list])

    pagination = main.select("nav.pagination ul.pagination")[0]

    return render_template(
        "archives.html",
        title=f"Contest Archives (Page {page})",
        page=page,
        contest_count=contest_count,
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
    for entry in body.select("div.contest-entries-list div.contest-entries-list-ible"):
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

    contest_count = str(soup.select("p.contest-count")[0])

    contests = []
    for contest in soup.select("div#cur-contests div.row-fluid div.contest-banner"):
        link = contest.select("div.contest-banner-inner a")[0].get("href")
        img = proxy(contest.select("div.contest-banner-inner a img")[0].get("src"))
        alt = contest.select("div.contest-banner-inner a img")[0].get("alt")
        deadline = contest.select("span.contest-meta-deadline")[0].get("data-deadline")
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
            item_img = proxy(featured_item.select("div.ible-thumb a img")[0].get("src"))
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


@app.route("/<category>/<channel>/projects/")
def route_channel_projects(category, channel):
    return project_list(channel.title())


@app.route("/<category>/<channel>/projects/<sort>/")
def route_channel_projects_sort(category, channel, sort):
    return project_list(
        channel.title(),
        " Sorted by " + sort.title(),
    )


@app.route("/<category>/projects/")
def route_category_projects(category):
    return project_list(category.title())


@app.route("/<category>/projects/<sort>/")
def route_category_projects_sort(category, sort):
    return project_list(category.title(), " Sorted by " + sort.title())


@app.route("/projects/")
def route_projects():
    return project_list("")


@app.route("/search", methods=["POST", "GET"])
def route_search():
    return project_list("Search")


@app.route("/projects/<sort>/")
def route_projects_sort(sort):
    return project_list("", " Sorted by " + sort.title())


@app.route("/circuits/")
def route_circuits():
    return category_page("Circuits")


@app.route("/workshop/")
def route_workshop():
    return category_page("Workshop")


@app.route("/craft/")
def route_craft():
    return category_page("Craft")


@app.route("/cooking/")
def route_cooking():
    return category_page("Cooking")


@app.route("/living/")
def route_living():
    return category_page("Living")


@app.route("/outside/")
def route_outside():
    return category_page("Outside")


@app.route("/teachers/")
def route_teachers():
    return category_page("Teachers", True)


@app.route("/member/<member>/instructables/")
def route_member_instructables(member):
    try:
        data = urlopen(f"https://www.instructables.com/member/{member}/instructables/")
    except HTTPError as e:
        abort(e.code)

    soup = BeautifulSoup(data.read().decode(), "html.parser")

    header = soup.select(".profile-header.profile-header-social")[0]
    header_content = member_header(header)

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

    return render_template(
        "member-instructables.html",
        title=f"{header_content['title']}'s Instructables",
        header_content=header_content,
        ibles=ible_list,
    )


@app.route("/member/<member>/")
def route_member(member):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0"
    }

    request = Request(
        f"https://www.instructables.com/member/{member}/", headers=headers
    )

    try:
        data = urlopen(request)
    except HTTPError as e:
        abort(e.code)

    soup = BeautifulSoup(data.read().decode(), "html.parser")

    header_content = member_header(soup)

    body = soup.select("div.member-profile-body")[0]

    ible_list = body.select(".boxed-content.promoted-content")

    ible_list_title = ""
    ibles = []

    if ible_list != []:
        ible_list = ible_list[0]
        ible_list_title = ible_list.select("h2.module-title")[0].text
        for ible in ible_list.select("ul.promoted-items li"):
            ible_title = ible.get("data-title")
            ible_link = ible.select("div.image-wrapper")[0].a.get("href")
            ible_img = proxy(ible.select("div.image-wrapper a img")[0].get("src"))

            ibles.append({"title": ible_title, "link": ible_link, "img": ible_img})

    ach_list = body.select(
        "div.two-col-section div.right-col-section.centered-sidebar div.boxed-content.about-me"
    )

    ach_list_title = ""
    achs = []

    if len(ach_list) > 1:
        ach_list = ach_list[1]
        ach_list_title = ach_list.select("h2.module-title")[0].text
        for ach in ach_list.select(
            "div.achievements-section.main-achievements.contest-achievements div.achievement-item:not(.two-column-filler)"
        ):
            ach_title = ach.select("div.achievement-info span.achievement-title")[
                0
            ].text
            ach_desc = ach.select("div.achievement-info span.achievement-description")[
                0
            ].text
            achs.append([ach_title, ach_desc])

    return render_template(
        "member.html",
        title=header_content["title"] + "'s Profile",
        header_content=header_content,
        ible_list_title=ible_list_title,
        ibles=ibles,
        ach_list_title=ach_list_title,
        achs=achs,
    )


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
                    1, {"title": "Supplies", "body": supplies, "files": supplies_files}
                )

            for step in data["steps"]:
                step_title = step["title"]
                print(step_title)

                step_imgs = []
                step_videos = []  # TODO: Check if this is still required
                step_iframes = []
                step_downloads = []

                for file in step["files"]:
                    print(file)
                    if file["image"] and "embedType" not in "file":
                        step_imgs.append(
                            {"src": proxy(file["downloadUrl"]), "alt": file["name"]}
                        )

                    elif not file["image"]:
                        step_downloads.append(
                            {"src": proxy(file["downloadUrl"]), "name": file["name"]}
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

                        elif invidious and src.startswith("https://www.youtube.com"):
                            src = src.replace("https://www.youtube.com", invidious)

                        elif not unsafe:
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
                thumbnail_channel_link = f"/{thumbnail_category}/{thumbnail_channel}"

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

                print(thumbnails[-1])

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


@app.route("/<category>/<channel>/")
def route_channel_redirect(category, channel):
    # TODO: Just check if the channel exists
    if (
        category == "circuits"
        or category == "workshop"
        or category == "craft"
        or category == "cooking"
        or category == "living"
        or category == "outside"
        or category == "teachers"
    ):
        return redirect(f"/{category}/{channel}/projects/", 307)
    else:
        raise NotFound()


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
    cooking = explore_lists(explore.select(".home-content-explore-category-cooking")[0])
    living = explore_lists(explore.select(".home-content-explore-category-living")[0])
    outside = explore_lists(explore.select(".home-content-explore-category-outside")[0])
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


@app.route("/proxy/")
def route_proxy():
    url = request.args.get("url")
    if url is not None:
        if url.startswith("https://cdn.instructables.com/") or url.startswith(
            "https://content.instructables.com/"
        ):

            def generate():
                # Subfunction to allow streaming the data instead of
                # downloading all of it at once
                try:
                    with urlopen(unquote(url)) as data:
                        while True:
                            chunk = data.read(1024 * 1024)
                            if not chunk:
                                break
                            yield chunk
                except HTTPError as e:
                    abort(e.code)

            try:
                with urlopen(unquote(url)) as data:
                    content_type = data.headers["content-type"]
            except HTTPError as e:
                abort(e.code)
            except KeyError:
                raise InternalServerError()

            return Response(generate(), content_type=content_type)
        else:
            raise BadRequest()
    else:
        raise BadRequest()


@app.route("/iframe/")
def route_iframe():
    url = request.args.get("url")
    url = unquote(url)
    if url is not None:
        return render_template("iframe.html", url=url)
    else:
        raise BadRequest()


@app.route("/privacypolicy/")
def privacypolicy():
    content = "No privacy policy found."

    try:
        with (pathlib.Path(__file__).parent / "privacy.txt").open() as f:
            content = f.read()
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


def main():
    global debugmode, invidious, unsafe

    parser = ArgumentParser()
    parser.add_argument(
        "-p",
        "--port",
        default=8002,
        type=int,
        help="Port to listen on",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "-l",
        "--listen-host",
        default="127.0.0.1",
        help="Host to listen on",
    )
    parser.add_argument(
        "-I",
        "--invidious",
        help="URL to Invidious instance, e.g. https://invidious.private.coffee/",
    )
    parser.add_argument(
        "-u",
        "--unsafe",
        action="store_true",
        help="Display iframes regardless of origin",
    )
    parser.add_argument(
        "-P",
        "--privacy-file",
        default="privacy.txt",
        help="File to read privacy policy from",
    )
    args = parser.parse_args()

    debugmode = os.environ.get(
        "FLASK_DEBUG", os.environ.get("STRUCTABLES_DEBUG", False)
    )
    invidious = os.environ.get("STRUCTABLES_INVIDIOUS")
    unsafe = os.environ.get("STRUCTABLES_UNSAFE", False)

    if args.debug:
        debugmode = True

    if args.invidious:
        invidious = args.invidious

    if args.unsafe:
        unsafe = True

    if debugmode:
        app.logger.setLevel(logging.DEBUG)

    app.run(port=args.port, host=args.listen_host, debug=debugmode)


if __name__ == "__main__":
    main()

# Initialize data when the server starts
update_data()
