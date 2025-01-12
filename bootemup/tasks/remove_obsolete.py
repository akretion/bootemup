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
    interval = config["remove_obsolete"]["check_interval"]
    print(f"Scheduling remove_obsolete task every {interval}s")

    while True:
        try:
            print("Running remove_obsolete task")
            containers = await get_containers()
            for container in containers:
                if (
                    not container.has_stop_inactive_label
                    or "running" in container.status
                ):
                    continue

                await container.get_last_activity()
                if (
                    container.last_activity is not None
                    and container.last_activity != "running"
                ):
                    age = (datetime.now(UTC) - container.last_activity).total_seconds()
                    if age > config["remove_obsolete"]["obsolete_threshold"]:
                        print(f"Removing {container.name} (inactive for {age} seconds)")
                        await container.rm()
        except Exception:
            print("Error in stop_inactive task:")
            print_exc()

        await sleep(interval)


remove_obsolete_listener = AppKey("remove_obsolete", Task[None])


async def remove_obsolete(app):
    app[remove_obsolete_listener] = create_task(loop(app))

    yield

    app[remove_obsolete_listener].cancel()
    with suppress(CancelledError):
        await app[remove_obsolete_listener]
