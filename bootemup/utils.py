# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT

from .config import config


async def run(*args):
    if config["server"]["dry_run"]:
        if args[0] == "docker" and args[1] == "compose":
            args = args[:2] + ("--dry-run",) + args[2:]
            print(" ".join(args))

    process = await create_subprocess_exec(
        *args,
        stdout=PIPE,
        stderr=STDOUT,
    )
    stdout, _ = await process.communicate()

    return stdout
