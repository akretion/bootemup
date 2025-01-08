# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT
from ..utils import get_infos
from ..html import Html


async def kill(request):
    html = Html(request)
    await html._init_()

    async with html._page_():
        await html._with_scroll_()

        async with html.code(style="white-space: pre-wrap;"):
            name = request.match_info.get("name")
            infos = await get_infos()
            info = next((info for info in infos if info["Name"] == name), None)
            if not info:
                await html(f"Unknown service {name}")
                return html.response

            await html(f"Killing, {name}...\n\n")

            configs = [
                arg
                for config in info.get("ConfigFiles").split(",")
                for arg in ["-f", config]
            ]

            process = await create_subprocess_exec(
                "docker", "compose", *configs, "kill", stdout=PIPE, stderr=STDOUT
            )
            stdout, _ = await process.communicate()

            if stdout:
                await html(stdout)

            process = await create_subprocess_exec(
                "docker", "compose", *configs, "logs", "-f", stdout=PIPE, stderr=STDOUT
            )

            backlog = b""
            while True:
                stdout = await process.stdout.read(256)
                if stdout:
                    backlog += stdout
                    await html(stdout)
                    if b"exited with code" in backlog:
                        process.terminate()
                        return html.response
                    break

        await html._with_redirect_("/")

    return html.response
