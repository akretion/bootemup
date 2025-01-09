# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from asyncio import gather

from ..container import Container
from ..html import Html


async def stop(request):
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

            await html(f"Stopping, {name}...\n\n")

            async def log():
                async for log in container.logs(
                    break_on={"exited with code": False}, tail=1
                ):
                    await html(log)

            async def stop():
                async for log in (await container.stop(stream=True))():
                    await html(log)

            try:
                await gather(log(), stop())
            except Exception as e:
                await html(str(e))
                return html.response

        await html._with_redirect_("/")

    return html.response
