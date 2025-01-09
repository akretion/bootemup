# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from ..container import Container
from ..html import Html


async def logs(request):
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

            try:
                async for log in container.logs():
                    await html(log)
            except Exception as e:
                await html(str(e))
                return html.response

    return html.response
