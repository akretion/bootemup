# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from aiohttp import web

from bootemup.routes import info, boot, kill


app = web.Application()
app.add_routes(
    [
        web.get("/", info),
        web.get("/boot/{name}", boot),
        web.get("/kill/{name}", kill),
    ]
)

if __name__ == "__main__":
    web.run_app(app, port=1212)
