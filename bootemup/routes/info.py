# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from asyncio import gather

from ..container import get_containers
from ..html import Html


async def info(request):
    html = Html(request)
    await html._init_()

    async with html._page_():
        containers = await get_containers()

        async with html.table():
            keys = ("name", "status")
            async with html.thead():
                for key in keys:
                    async with html.th():
                        await html(key)
                async with html.th():
                    await html("actions")

            async with html.tbody():
                for container in containers:
                    async with html.tr():
                        for key in keys:
                            value = getattr(container, key)
                            async with html.td():
                                await html(value)

                        async with html.td():
                            link = "margin: 0 0.25em;"
                            async with html.a(
                                style=link, href=f"/logs/{container.name}"
                            ):
                                await html("Logs")
                            if "exited" in container.status:
                                async with html.a(
                                    style=link, href=f"/start/{container.name}"
                                ):
                                    await html("Start")
                            if "running" in container.status:
                                async with html.a(style=link, href=container.url):
                                    await html("Open")
                                async with html.a(
                                    style=link, href=f"/stop/{container.name}"
                                ):
                                    await html("Stop")

        async with html.table():
            keys = ("name", "flags", "last_activity", "last_access", "last_url")
            async with html.thead():
                for key in keys:
                    async with html.th():
                        await html(key)

            async with html.tbody():
                for container in containers:
                    await gather(
                        container.get_last_access(),
                        container.get_last_activity(),
                    )

                    async with html.tr():
                        for key in keys:
                            value = getattr(container, key)
                            async with html.td():
                                await html(value)

    return html.response
