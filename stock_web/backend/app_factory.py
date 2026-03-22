from pathlib import Path
from flask import Flask
from backend.routes.api_routes import register_api_routes
from backend.routes.page_routes import register_page_routes
from backend.services.container import ServiceContainer


def create_app():
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )
    services = ServiceContainer()
    register_page_routes(app, services)
    register_api_routes(app, services)
    return app
