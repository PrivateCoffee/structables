#!/usr/bin/env python

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    Response,
    stream_with_context,
)
import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
from traceback import print_exc
from requests_html import HTMLSession
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from argparse import ArgumentParser

import os

global_ibles = {}

def proxy(src):
    return "/proxy/?url=" + quote(str(src))

def update_data():
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    channels = []

    data = requests.get(f"https://www.instructables.com/sitemap/")

    soup = BeautifulSoup(data.text, "html.parser")

    main = soup.select("div.sitemap-content")[0]

    groups = []
    for group in main.select("div.group-section"):
        channels.append(group.select("h2 a")[0].text.lower())

    global_ibles["/projects"] = []

    page.goto("https://www.instructables.com/projects")

    while len(global_ibles["/projects"]) <= 0:
        for ible in page.query_selector_all(".ibleCard__QPJVm"):
            link = (
                ible.query_selector("a")
                .get_attribute("href")
                .replace("https://www.instructables.com", "{instance_root_url}")
            )
            img = proxy(ible.query_selector("img").get_attribute("src"))

            title = ible.query_selector(".title__t0fGQ").inner_text()
            author = ible.query_selector("a[href^='/member/']").inner_text()
            author_link = (
                ible.query_selector("a[href^='/member/']")
                .get_attribute("href")
                .replace("https://www.instructables.com", "{instance_root_url}")
            )

            channel = "TEST"
            channel_link = "TEST"

            for c in channels:
                try:
                    channel = ible.query_selector("a[href^='/" + c + "']").inner_text()
                    channel_link = (
                        ible.query_selector("a[href^='/" + c + "']")
                        .get_attribute("href")
                        .replace("https://www.instructables.com", "{instance_root_url}")
                    )
                except:
                    try:
                        channel = ible.query_selector("a[href^='/projects/']").inner_text()
                        channel_link = (
                            ible.query_selector("a[href^='/projects/']")
                            .get_attribute("href")
                            .replace("https://www.instructables.com", "{instance_root_url}")
                        )
                    except:
                        pass

            stats = ible.query_selector(".stats__GFKyl")
            views = 0
            if stats.query_selector("div[title$=' views']"):
                views = stats.query_selector("div[title$=' views']").inner_text()
            favorites = 0
            if stats.query_selector("div[title$=' favorites']"):
                favorites = stats.query_selector("div[title$=' favorites']").inner_text()

            global_ibles["/projects"].append(
                [
                    link,
                    img,
                    title,
                    author,
                    author_link,
                    channel,
                    channel_link,
                    views,
                    favorites,
                ]
            )

    browser.close()
    playwright.stop()

debugmode = False

if __name__ == "__main__":
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
    args = parser.parse_args()
    
    if args.debug:
        debugmode = True

print("Loading...")

update_data()

print("Started!")

app = Flask(__name__, template_folder="templates", static_folder="static")

def get_instance_root_url(request):
    return request.url_root

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
            [
                link,
                img,
                alt,
                title,
                author,
                author_link,
                channel,
                channel_link,
                favorites,
                views,
            ]
        )
    return list_


def member_header(header):
    avatar = proxy(
        header.select("div.profile-avatar-container img.profile-avatar")[0].get("src")
    )
    title = header.select("div.profile-top div.profile-headline h1.profile-title")[
        0
    ].text

    profile_top = header.select("div.profile-top")[0]

    print(header.encode_contents())

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

    return [
        avatar,
        title,
        location,
        signup,
        instructables,
        views,
        comments,
        followers,
        bio,
    ]


def category_page(path, name, teachers=False):
    data = requests.get("https://www.instructables.com" + path)
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

    channels = []
    for card in soup.select("div.scrollable-cards-inner div.scrollable-card"):
        link = card.a["href"]
        img = proxy(
            card.select(f"a{' noscript' if teachers else ''} img")[0].get("src")
        )
        title = card.select("a img")[0].get("alt")

        channels.append([link, title, img])

    ibles = []
    for ible in soup.select(
        "div.category-landing-projects-list div.category-landing-projects-ible"
    ):
        link = ible.a["href"]
        img = proxy(ible.select("a noscript img")[0].get("src"))

        info = ible.select("div.category-landing-projects-ible-info")[0]
        title = info.select("a.ible-title")[0].text
        author = info.select("span.ible-author a")[0].text
        author_link = info.select("span.ible-author a")[0].get("href")
        channel = info.select("span.ible-channel a")[0].text
        channel_link = info.select("span.ible-channel a")[0].get("href")

        stats = ible.select("span.ible-stats-right-col")[0]
        views = 0
        if stats.select("span.ible-views") != []:
            views = stats.select("span.ible-views")[0].text
        favorites = 0
        if stats.select("span.ible-favorites") != []:
            favorites = stats.select("span.ible-favorites")[0].text

        ibles.append(
            [
                link,
                img,
                title,
                author,
                author_link,
                channel,
                channel_link,
                views,
                favorites,
            ]
        )

    contests = []
    for contest in soup.select(
        "div.category-landing-contests-list div.category-landing-contests-item"
    ):
        link = contest.a["href"]
        img = proxy(contest.select("a noscript img")[0].get("src"))
        title = contest.select("a img")[0].get("alt")

        contests.append([link, img, title])

    return render_template(
        "category.html", data=[name, channels, ibles, contests, path]
    )


def project_list(path, head, sort=""):
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto(urljoin("https://www.instructables.com", path))

    head = f"{head + ' ' if head != '' else ''}Projects" + sort
    path_ = path.rsplit("/", 1)[0]

    if path == "/projects/" or path == "/projects":
        ibles = global_ibles["/projects"]
    else:
        ibles = []

        for ible in page.query_selector_all(".ibleCard__QPJVm"):
            link = (
                ible.query_selector("a")
                .get_attribute("href")
                .replace("https://www.instructables.com", "{instance_root_url}")
            )
            img = proxy(
                ible.find_elements(By.CSS_SELECTOR, "img")[0].get_attribute("src")
            )

            title = ible.find_elements(By.CLASS_NAME, "title__t0fGQ")[0].text
            author = ible.find_elements(By.CSS_SELECTOR, "a[href^='/member/']")[0].text
            author_link = (
                ible.find_elements(By.CSS_SELECTOR, "a[href^='/member/']")[0]
                .get_attribute("href")
                .replace("https://www.instructables.com", "{instance_root_url}")
            )

            channel = "TEST"
            channel_link = "TEST"

            for c in channels:
                try:
                    channel = ible.query_selector("a[href^='/" + c + "']").inner_text()
                    channel_link = (
                        ible.query_selector("a[href^='/" + c + "']")
                        .get_attribute("href")
                        .replace("https://www.instructables.com", "{instance_root_url}")
                    )
                except:
                    try:
                        channel = ible.query_selector("a[href^='/projects/'] span").inner_text()
                        channel_link = (
                            ible.query_selector("a[href^='/projects/']")
                            .get_attribute("href")
                            .replace("https://www.instructables.com", "{instance_root_url}")
                        )
                    except:
                        pass

            stats = ible.query_selector(".stats__GFKyl")
            views = 0

            if stats.query_selector("div[title$=' views']"):
                views = stats.query_selector("div[title$=' views']").inner_text()

            favorites = 0

            if stats.query_selector("div[title$=' favorites']"):
                favorites = stats.query_selector("div[title$=' favorites']").inner_text()

            ibles.append(
                [
                    link,
                    img,
                    title,
                    author,
                    author_link,
                    channel,
                    channel_link,
                    views,
                    favorites,
                ]
            )

            if len(ibles) >= 8:
                break

    browser.close()
    playwright.stop()

    return render_template("projects.html", data=[head, ibles, path_])

@app.route("/sitemap/")
def route_sitemap():
    data = requests.get(f"https://www.instructables.com/sitemap/")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

    main = soup.select("div.sitemap-content")[0]

    groups = []
    for group in main.select("div.group-section"):
        category = group.select("h2 a")[0].text
        category_link = group.select("h2 a")[0].get("href")
        channels = []
        for li in group.select("ul.sitemap-listing li"):
            channel = li.a.text
            channel_link = li.a["href"]
            channels.append([channel, channel_link])
        groups.append([category, category_link, channels])

    return render_template("sitemap.html", data=groups)


@app.route("/contest/archive/")
def route_contest_archive():
    page = 1
    if request.args.get("page") != None:
        page = request.args.get("page")
    data = requests.get(f"https://www.instructables.com/contest/archive/?page={page}")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

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
        "archives.html", data=[page, contest_count, pagination, contest_list]
    )


@app.route("/contest/<contest>/")
def route_contest(contest):
    data = requests.get(f"https://www.instructables.com/contest/{contest}/")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

    title = soup.select('meta[property="og:title"]')[0].get("content")

    body = soup.select("div#contest-wrapper")[0]

    img = proxy(body.select("div#contest-masthead img")[0].get("src"))

    entry_count = body.select("li.entries-nav-btn")[0].text.split(" ")[0]
    prizes = body.select("li.prizes-nav-btn")[0].text.split(" ")[0]

    info = body.select("div.contest-body-column-left")[0]
    info.select("div#site-announcements-page")[0].decompose()
    info.select("h3")[0].decompose()
    info.select("div#contest-body-nav")[0].decompose()
    info = str(info).replace("https://www.instructables.com", "{instance_root_url}")

    entries = body.select("span.contest-entity-count")[0].text

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
            [
                link,
                entry_img,
                entry_title,
                author,
                author_link,
                channel,
                channel_link,
                views,
            ]
        )

    return render_template(
        "contest.html", data=[title, img, entry_count, prizes, info, entry_list]
    )


@app.route("/contest/")
def route_contests():
    data = requests.get("https://www.instructables.com/contest/")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

    contest_count = str(soup.select("p.contest-count")[0])

    contests = []
    for contest in soup.select("div#cur-contests div.row-fluid div.contest-banner"):
        link = contest.select("div.contest-banner-inner a")[0].get("href")
        img = proxy(contest.select("div.contest-banner-inner a img")[0].get("src"))
        alt = contest.select("div.contest-banner-inner a img")[0].get("alt")
        deadline = contest.select("span.contest-meta-deadline")[0].get("data-deadline")
        prizes = contest.select("span.contest-meta-count")[0].text
        entries = contest.select("span.contest-meta-count")[1].text

        contests.append([link, img, alt, deadline, prizes, entries])

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
                [item_link, item_img, item_title, item_author, item_author_link]
            )
        closed.append([link, img, alt, featured_items])

    return render_template("contests.html", data=[contest_count, contests, closed])


@app.route("/<category>/<channel>/projects/")
def route_channel_projects(category, channel):
    return project_list(f"/{category}/{channel}/projects/", channel.title())


@app.route("/<category>/<channel>/projects/<sort>/")
def route_channel_projects_sort(category, channel, sort):
    return project_list(
        f"/{category}/{channel}/projects/{sort}",
        channel.title(),
        " Sorted by " + sort.title(),
    )


@app.route("/<category>/projects/")
def route_category_projects(category):
    return project_list(f"/{category}/projects/", category.title())


@app.route("/<category>/projects/<sort>/")
def route_category_projects_sort(category, sort):
    return project_list(
        f"/{category}/projects/{sort}", category.title(), " Sorted by " + sort.title()
    )


@app.route("/projects/")
def route_projects():
    return project_list("/projects/", "")


@app.route("/search")
def route_search():
    return project_list("/search/?q=" + request.args["q"] + "&projects=all", "Search")


@app.route("/projects/<sort>/")
def route_projects_sort(sort):
    return project_list(f"/projects/{sort}", "", " Sorted by " + sort.title())


@app.route("/circuits/")
def route_circuits():
    return category_page("/circuits/", "Circuits")


@app.route("/workshop/")
def route_workshop():
    return category_page("/workshop/", "Workshop")


@app.route("/craft/")
def route_craft():
    return category_page("/craft/", "Craft")


@app.route("/cooking/")
def route_cooking():
    return category_page("/cooking/", "Cooking")


@app.route("/living/")
def route_living():
    return category_page("/living/", "Living")


@app.route("/outside/")
def route_outside():
    return category_page("/outside/", "Outside")


@app.route("/teachers/")
def route_teachers():
    return category_page("/teachers/", "Teachers", True)


@app.route("/sitemap/projects/<category>/<subcategory>")
def route_sitemap_circuits(category, subcategory):
    return category_page(
        "/" + category + "/" + subcategory, subcategory + " - " + category
    )


@app.route("/member/<member>/instructables/")
def route_member_instructables(member):
    data = requests.get(f"https://www.instructables.com/member/{member}/instructables")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

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

        ible_list.append([link, img, title, views, favorites])

    return render_template(
        "member-instructables.html", data=header_content + [ible_list]
    )


@app.route("/member/<member>/")
def route_member(member):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/113.0"
    }

    data = requests.get(
        f"https://www.instructables.com/member/{member}/", headers=headers
    )
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

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

            ibles.append([ible_title, ible_link, ible_img])

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
        data=header_content + [ible_list_title, ibles, ach_list_title, achs],
    )


@app.route("/<article>/")
def route_article(article):
    data = requests.get(f"https://www.instructables.com/{article}/")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

    try:
        header = soup.select("header")
        if len(header) < 2 and soup.select("title")[0].text.contains("Pending Review"):
            return render_template("article-review.html")
        else:
            header = header[1]
        title = header.find("h1").text

        byline = header.select("div.sub-header div.header-byline")[0]
        author = byline.select("a")[0].text
        author_link = byline.select("a")[0].get("href")
        category = byline.select("a")[1].text
        category_link = byline.select("a")[1].get("href")
        channel = byline.select("a")[2].text
        channel_link = byline.select("a")[2].get("href")

        stats = header.select("div.sub-header div.header-stats")[0]
        views = stats.select(".view-count")[0].text
        favorites = 0
        if stats.select(".favorite-count") != []:
            favorites = stats.select(".favorite-count")[0].text

        if soup.select("div.article-body") != []:
            ## Instructables
            body = soup.select("div.article-body")[0]

            steps = []
            for step in body.select("section.step"):
                step_title = step.select("h2")[0].text

                step_imgs = []
                for img in step.select("div.no-js-photoset img"):
                    step_imgs.append([proxy(img.get("src")), img.get("alt")])

                step_videos = []
                for img in step.select("video"):
                    step_videos.append([proxy(img.get("src"))])

                step_text = str(step.select("div.step-body")[0])
                step_text = step_text.replace(
                    "https://content.instructables.com",
                    "{instance_root_url}/proxy/?url=https://content.instructables.com".format(
                        instance_root_url=get_instance_root_url(request)
                    ),
                )
                steps.append([step_title, step_imgs, step_text, step_videos])

            comments_list = []
            comment_count = 0

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
                data=[
                    title,
                    author,
                    author_link,
                    category,
                    category_link,
                    channel,
                    channel_link,
                    views,
                    favorites,
                    steps,
                    comment_count,
                    comments_list,
                ],
                enumerate=enumerate,
            )
        else:
            ## Collections
            thumbnails = []
            for thumbnail in soup.select("ul#thumbnails-list li"):
                text = (
                    link
                ) = (
                    img
                ) = (
                    thumbnail_title
                ) = (
                    thumbnail_author
                ) = (
                    thumbnail_author_link
                ) = thumbnail_channel = thumbnail_channel_link = ""

                if thumbnail.select("div.thumbnail > p") != []:
                    text = thumbnail.select("div.thumbnail > p")[0]
                if thumbnail.select("div.thumbnail div.thumbnail-image"):
                    link = thumbnail.select("div.thumbnail div.thumbnail-image a")[
                        0
                    ].get("href")
                    img = proxy(
                        thumbnail.select("div.thumbnail div.thumbnail-image a img")[
                            0
                        ].get("src")
                    )
                    thumbnail_title = thumbnail.select(
                        "div.thumbnail div.thumbnail-info h3.title a"
                    )[0].text
                    thumbnail_author = thumbnail.select(
                        "div.thumbnail div.thumbnail-info span.author a"
                    )[0].text
                    thumbnail_author_link = thumbnail.select(
                        "div.thumbnail div.thumbnail-info span.author a"
                    )[0].get("href")
                    thumbnail_channel = thumbnail.select(
                        "div.thumbnail div.thumbnail-info span.origin a"
                    )[0].text
                    thumbnail_channel_link = thumbnail.select(
                        "div.thumbnail div.thumbnail-info span.origin a"
                    )[0].get("href")
                thumbnails.append(
                    [
                        text,
                        link,
                        img,
                        thumbnail_title,
                        thumbnail_author,
                        thumbnail_author_link,
                        thumbnail_channel,
                        thumbnail_channel_link,
                    ]
                )

            return render_template(
                "collection.html",
                data=[
                    title,
                    author,
                    author_link,
                    category,
                    category_link,
                    channel,
                    channel_link,
                    views,
                    favorites,
                    thumbnails,
                ],
            )

    except Exception:
        print_exc()
        return Response(render_template("404.html"), status=404)


@app.route("/<category>/<channel>/")
def route_channel_redirect(category, channel):
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
        return Response(render_template("404.html"), status=404)


@app.route("/")
def route_explore():
    data = requests.get("https://www.instructables.com/")
    if data.status_code != 200:
        return Response(
            render_template(str(data.status_code) + ".html"), status=data.status_code
        )

    soup = BeautifulSoup(data.text, "html.parser")

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
        data=[title, circuits, workshop, craft, cooking, living, outside, teachers],
    )


@app.route("/proxy/")
def route_proxy():
    url = request.args.get("url")
    if url != None:
        if url.startswith("https://cdn.instructables.com/") or url.startswith(
            "https://content.instructables.com/"
        ):
            data = requests.get(unquote(url))
            return Response(data.content, content_type=data.headers["content-type"])
        else:
            return Response(render_template("400.html"), status=400)
    else:
        return Response(render_template("400.html"), status=400)

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html")


if __name__ == "__main__":
    app.run(port=args.port, host=args.listen_host, debug=debugmode)
