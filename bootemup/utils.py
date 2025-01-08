# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT


def url_for(name):
    return f"http://{name}.localhost"


async def get_infos():
    process = await create_subprocess_exec(
        "docker",
        "compose",
        "ls",
        "--all",
        "--format",
        "json",
        stdout=PIPE,
        stderr=STDOUT,
    )
    stdout, _ = await process.communicate()
    return json.loads(stdout)
