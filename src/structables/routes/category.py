from flask import redirect
from werkzeug.exceptions import NotFound
from ..utils.helpers import project_list, category_page


def init_category_routes(app):
    @app.route("/<category>/<channel>/projects/")
    def route_channel_projects(category, channel):
        return project_list(app, channel.title())

    @app.route("/<category>/<channel>/projects/<sort>/")
    def route_channel_projects_sort(category, channel, sort):
        return project_list(
            app,
            channel.title(),
            " Sorted by " + sort.title(),
        )

    @app.route("/<category>/projects/")
    def route_category_projects(category):
        return project_list(app, category.title())

    @app.route("/<category>/projects/<sort>/")
    def route_category_projects_sort(category, sort):
        return project_list(app, category.title(), " Sorted by " + sort.title())

    @app.route("/projects/")
    def route_projects():
        return project_list(app, "")

    @app.route("/projects/<sort>/")
    def route_projects_sort(sort):
        return project_list(app, "", " Sorted by " + sort.title())

    @app.route("/circuits/")
    def route_circuits():
        return category_page(app, "Circuits")

    @app.route("/workshop/")
    def route_workshop():
        return category_page(app, "Workshop")

    @app.route("/craft/")
    def route_craft():
        return category_page(app, "Craft")

    @app.route("/cooking/")
    def route_cooking():
        return category_page(app, "Cooking")

    @app.route("/living/")
    def route_living():
        return category_page(app, "Living")

    @app.route("/outside/")
    def route_outside():
        return category_page(app, "Outside")

    @app.route("/teachers/")
    def route_teachers():
        return category_page(app, "Teachers", True)

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
            raise NotFound()
