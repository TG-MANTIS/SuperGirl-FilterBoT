"""
Web Server Application Module
Initializes and configures the aiohttp web application instance,
setting up route definitions and maximum request payload size limits.
"""

from aiohttp import web
from .route import routes


async def web_server() -> web.Application:
    """
    Creates and configures the aiohttp web application with defined routes and limits.
    """
    web_app = web.Application(client_max_size=30000000)
    web_app.add_routes(routes)
    return web_app
