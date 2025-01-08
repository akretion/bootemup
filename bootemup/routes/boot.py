# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..container import Container
from ..html import Html


async def boot(request):
    html = Html(request)
    await html._init_()

    async with html._page_(full_width=True):
        await html._with_scroll_()

        async with html.pre("word-break: break-all;font-size: 0.9em;"):
            name = request.match_info.get("name")
            try:
                container = await Container.get(name)
            except ValueError as e:
                await html(str(e))
                return html.response

            await html(f"Booting, {name}...\n\n")

            await html(await container.boot())

            try:
                async for log in container.logs(
                    break_on={"running on": False, "exited with code": True}
                ):
                    await html(log)
            except Exception as e:
                await html(str(e))
                return html.response

        await html._with_redirect_(container.url)

    return html.response
