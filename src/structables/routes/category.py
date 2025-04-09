from flask import redirect
from werkzeug.exceptions import NotFound
from ..utils.helpers import project_list, category_page
import logging

logger = logging.getLogger(__name__)


def init_category_routes(app):
    @app.route("/<category>/<channel>/projects/")
    def route_channel_projects(category, channel):
        logger.debug(f"Rendering channel projects for {category}/{channel}")
        return project_list(app, channel.title())

    @app.route("/<category>/<channel>/projects/<sort>/")
    def route_channel_projects_sort(category, channel, sort):
        logger.debug(
            f"Rendering channel projects for {category}/{channel} sorted by {sort}"
        )
        return project_list(
            app,
            channel.title(),
            " Sorted by " + sort.title(),
        )

    @app.route("/<category>/projects/")
    def route_category_projects(category):
        logger.debug(f"Rendering category projects for {category}")
        return project_list(app, category.title())

    @app.route("/<category>/projects/<sort>/")
    def route_category_projects_sort(category, sort):
        logger.debug(f"Rendering category projects for {category} sorted by {sort}")
        return project_list(app, category.title(), " Sorted by " + sort.title())

    @app.route("/projects/")
    def route_projects():
        logger.debug("Rendering all projects")
        return project_list(app, "")

    @app.route("/projects/<sort>/")
    def route_projects_sort(sort):
        logger.debug(f"Rendering all projects sorted by {sort}")
        return project_list(app, "", " Sorted by " + sort.title())

    @app.route("/circuits/")
    def route_circuits():
        logger.debug("Rendering circuits category page")
        return category_page(app, "Circuits")

    @app.route("/workshop/")
    def route_workshop():
        logger.debug("Rendering workshop category page")
        return category_page(app, "Workshop")

    @app.route("/craft/")
    def route_craft():
        logger.debug("Rendering craft category page")
        return category_page(app, "Craft")

    @app.route("/cooking/")
    def route_cooking():
        logger.debug("Rendering cooking category page")
        return category_page(app, "Cooking")

    @app.route("/living/")
    def route_living():
        logger.debug("Rendering living category page")
        return category_page(app, "Living")

    @app.route("/outside/")
    def route_outside():
        logger.debug("Rendering outside category page")
        return category_page(app, "Outside")

    @app.route("/teachers/")
    def route_teachers():
        logger.debug("Rendering teachers category page")
        return category_page(app, "Teachers", True)

    @app.route("/<category>/<channel>/")
    def route_channel_redirect(category, channel):
        logger.debug(f"Channel redirect for {category}/{channel}")
        if (
            category == "circuits"
            or category == "workshop"
            or category == "craft"
            or category == "cooking"
            or category == "living"
            or category == "outside"
            or category == "teachers"
        ):
            logger.debug(f"Redirecting to /{category}/{channel}/projects/")
            return redirect(f"/{category}/{channel}/projects/", 307)
        else:
            logger.warning(f"Invalid category: {category}")
            raise NotFound()
