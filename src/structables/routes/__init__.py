from .main import init_main_routes
from .category import init_category_routes
from .member import init_member_routes
from .proxy import init_proxy_routes
from .contest import init_contest_routes

def init_routes(app):
    init_main_routes(app)
    init_category_routes(app)
    init_member_routes(app)
    init_proxy_routes(app)
    init_contest_routes(app)