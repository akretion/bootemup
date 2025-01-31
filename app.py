# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from aiohttp import web
from bootemup.config import config
from bootemup.routes import info, start, stop, logs
from bootemup.tasks import remove_obsolete, stop_inactive


app = web.Application()

if config["server"]["disable_interface"]:
    print("Web interface is disabled")

app.add_routes(
    [
        web.get("/start/{name}", start),
        web.get("/start/{name}/boot", start),
        web.get("/stop/{name}", stop),
    ]
    + (
        [
            web.get("/", info),
            web.get("/logs/{name}", logs),
        ]
        if not config["server"]["disable_interface"]
        else []
    )
)
if not config["server"]["disable_background_tasks"]:
    app.cleanup_ctx.append(remove_obsolete)
    app.cleanup_ctx.append(stop_inactive)
else:
    print("Background tasks are disabled")


if __name__ == "__main__":
    web.run_app(app, port=1212)
