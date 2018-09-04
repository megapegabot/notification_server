from aiohttp import web
from app import createMainApp
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--config', type = argparse.FileType('r'), required = True)
args = parser.parse_args()

app = createMainApp(args.config)
web.run_app(app, host = app["config"]["server"]["host"], port = int(app["config"]["server"]["port"]))