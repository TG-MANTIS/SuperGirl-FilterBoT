"""
Web Route Handler Module
Provides a simple HTTP route for health checks or web service status responses using aiohttp.
"""

from aiohttp import web

routes = web.RouteTableDef()


@routes.get("/", allow_head=True)
async def root_route_handler(request: web.Request) -> web.Response:
    """
    Root endpoint handler that returns a JSON response indicating service status.
    """
    return web.json_response("CopyCodeBots")
