# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from aiohttp.web import AppKey
from asyncio import Task, create_task, CancelledError, sleep
from contextlib import suppress
from datetime import datetime, UTC
from traceback import print_exc

from ..config import config
from ..container import get_containers


async def loop(app):
    interval = config["stop_inactive"]["check_interval"]
    print(f"Scheduling stop_inactive task every {interval}s")

    while True:
        try:
            print("Running stop_inactive task")
            containers = await get_containers()
            for container in containers:
                if "running" not in container.status:
                    continue

                await container.get_last_access()
                if container.last_access is not None:
                    age = (datetime.now(UTC) - container.last_access).total_seconds()
                    if age > config["stop_inactive"]["inactive_threshold"]:
                        print(f"Stopping {container.name} (inactive for {age} seconds)")
                        await container.kill()
        except Exception:
            print("Error in stop_inactive task:")
            print_exc()

        await sleep(interval)


stop_inactive_listener = AppKey("stop_inactive", Task[None])


async def stop_inactive(app):
    app[stop_inactive_listener] = create_task(loop(app))

    yield

    app[stop_inactive_listener].cancel()
    with suppress(CancelledError):
        await app[stop_inactive_listener]
