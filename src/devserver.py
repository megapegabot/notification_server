from aiohttp import web
from app import createMainApp
app = createMainApp()
web.run_app(app, host = "0.0.0.0", port = 8000)