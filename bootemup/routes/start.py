# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..container import Container
from ..html import Html


async def start(request):
    html = Html(request)
    await html._init_()

    async with html._page_(full_width=True):
        async with html._code_():
            name = request.match_info.get("name")
            try:
                container = await Container.get(name)
            except ValueError as e:
                await html(str(e))
                return html.response

            if request.path.endswith("/boot"):
                await html(f"Killing, {name}...\n\n")
                await html.maybe(await container.kill(), "ok\n")
                await html(f"\nBooting, {name}...\n\n")
                await html.maybe(await container.boot(), "ok\n")
            else:
                await html(f"Starting, {name}...\n\n")
                await html.maybe(await container.start(), "ok\n")

            try:
                async for log in container.logs(
                    break_on={"running on": False, "exited with code": True}, tail=1
                ):
                    await html.maybe(log, ".")

            except Exception as e:
                await html.maybe(str(e), "Error")
                return html.response

        await html._with_redirect_(container.url)

    return html.response
