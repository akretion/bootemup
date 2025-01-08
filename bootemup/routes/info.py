# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from ..utils import get_infos, url_for
from ..html import Html


async def info(request):
    html = Html(request)
    await html._init_()

    async with html._page_():
        async with html.table():
            data = await get_infos()

            keys = {key: None for line in data for key in line.keys()}
            keys["Actions"] = None

            async with html.thead():
                for key in keys:
                    async with html.th():
                        await html(key)

            async with html.tbody():
                for line in data:
                    async with html.tr():
                        for key in keys:
                            async with html.td():
                                if key == "Actions":
                                    name = line["Name"]
                                    state = line["Status"]
                                    if "exited" in state:
                                        async with html.a(href=f"/boot/{name}"):
                                            await html("Boot ")
                                    if "running" in state:
                                        async with html.a(href=url_for(name)):
                                            await html("Open ")
                                        async with html.a(href=f"/kill/{name}"):
                                            await html("Kill ")
                                else:
                                    await html(line.get(key))

    return html.response
