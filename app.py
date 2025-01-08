# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from aiohttp import web
from bootemup.config import config
from bootemup.routes import info, boot, kill, logs
from bootemup.tasks import remove_obsolete, stop_inactive


app = web.Application()
app.add_routes(
    [
        web.get("/", info),
        web.get("/boot/{name}", boot),
        web.get("/kill/{name}", kill),
        web.get("/logs/{name}", logs),
    ]
)
if not config["server"]["disable_background_tasks"]:
    app.cleanup_ctx.append(remove_obsolete)
    app.cleanup_ctx.append(stop_inactive)
else:
    print("Background tasks are disabled")


if __name__ == "__main__":
    web.run_app(app, port=1212)
