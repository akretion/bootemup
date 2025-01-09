# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from asyncio import gather
import json
import re
from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT
from datetime import datetime, UTC
from collections import defaultdict

from .utils import run
from .config import config


async def get_containers():
    compose_out, docker_out = await gather(
        run(
            "docker",
            "compose",
            "ls",
            "--all",
            "--format",
            "json",
        ),
        run("docker", "ps", "--all", "--no-trunc", "--format", "json"),
    )

    ls = json.loads(compose_out)

    images = defaultdict(list)

    containers = [
        json.loads(container)
        for container in docker_out.decode("utf-8").split("\n")
        if container
    ]

    for container in containers:
        labels = {
            key: value
            for keyval in container["Labels"].split(",")
            for (key, value) in (
                (keyval.split("=", 1) if "=" in keyval else (keyval, "")),
            )
        }

        if "com.docker.compose.project" not in labels:
            continue

        images[labels["com.docker.compose.project"]].append(
            {
                "id": container["ID"],
                "labels": labels,
                "image": container["Image"],
                "name": container["Names"],
                "state": container["State"],
                "status": container["Status"],
                "command": container["Command"],
                "create_date": container["CreatedAt"],
                "local_volumes": container["LocalVolumes"],
                "mounts": container["Mounts"],
                "networks": container["Networks"],
                "ports": container["Ports"],
                "running_for": container["RunningFor"],
                "size": container["Size"],
            }
        )

    return [
        Container(
            line["Name"],
            line["Status"],
            line["ConfigFiles"].split(","),
            images[line["Name"]],
        )
        for line in ls
    ]


class Container:
    @staticmethod
    async def get(name):
        containers = await get_containers()
        name_containers = {container.name: container for container in containers}
        if name not in name_containers:
            raise ValueError(f"Unknown service {name}")
        return name_containers[name]

    def __init__(self, name, status, files, images):
        self.name = name
        self.status = status
        self.files = files
        self.images = images
        self.last_url = None
        self.last_access = None
        self.last_activity = None

    def _configs(self):
        return [arg for config in self.files for arg in ["-f", config]]

    @property
    def url(self):
        for rexp, url in config["urls"].items():
            rex = re.compile(rexp)
            if rex.match(self.name):
                return rex.sub(url, self.name)

        raise ValueError(f"No url match found for {self.name}")

    @property
    def states(self):
        return [
            f"{container['id'][:12]} ({container['name']}): {container['state']}"
            for container in self.images
        ]

    async def start(self, stream=False):
        return await run(
            "docker",
            "compose",
            "-p",
            self.name,
            "start",
            stream=stream,
        )

    async def stop(self, stream=False):
        return await run(
            "docker",
            "compose",
            "-p",
            self.name,
            "stop",
            "--timeout",
            "1",
            stream=stream,
        )

    async def boot(self, stream=False):
        return await run(
            "docker",
            "compose",
            *self._configs(),
            "up",
            "-d",
            stream=stream,
        )

    async def rm(self, stream=False):
        return await run(
            "docker",
            "compose",
            *self._configs(),
            "down",
            "--rmi",
            "local",
            "--volumes",
            stream=stream,
        )

    async def kill(self):
        return await run("docker", "compose", "-p", self.name, "kill")

    async def logs(self, break_on=None, tail=None):
        break_on = break_on or {}
        tail_params = ["--tail", str(tail)] if tail else []
        process = await create_subprocess_exec(
            "docker",
            "compose",
            "-p",
            self.name,
            "logs",
            *tail_params,
            "-f",
            stdout=PIPE,
            stderr=STDOUT,
        )
        backlog = ""
        while True:
            stdout = await process.stdout.read(256)
            if stdout:
                yield stdout
                backlog += stdout.decode("utf-8")

                for break_, raise_ in break_on.items():
                    if break_ in backlog:
                        process.terminate()
                        if raise_:
                            raise ValueError("Errored")
                        return
            else:
                if process.returncode is not None and process.returncode != 0:
                    raise ValueError(f"Exited with code {process.returncode}")
                break
        return

    async def get_last_access(self):
        access_re = re.compile(
            r".*\| (?P<timestamp>(:?\d|-)+ (:?\d|-|:)+)(?:,\d+)? \d+ .+ "
            r'"(GET|POST|PUT|DELETE) (?P<url>\S+) HTTP.*'
        )
        startup_re = re.compile(
            r".*\| (?P<timestamp>(:?\d|-)+ (:?\d|-|:)+)(?:,\d+)? \d+ .+ "
            r"running on (?P<url>\S+).*"
        )

        stdout = await run(
            "docker",
            "compose",
            "-p",
            self.name,
            "logs",
        )
        lines = stdout.decode("utf-8").split("\n")
        for line in reversed(lines):
            match = access_re.match(line)
            if not match:
                match = startup_re.match(line)
            if match:
                date = datetime.fromisoformat(match.group("timestamp"))
                # assuming logs are in UTC
                date = date.replace(tzinfo=UTC)
                self.last_url = match.group("url")
                self.last_access = date
                return

        self.last_access = "never"
        return stdout.decode("utf-8")

    async def get_last_activity(self):
        for image in self.images:
            if image["state"] != "running":
                last_activity = await run(
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.FinishedAt}}",
                    image["id"],
                )
                last_activity = datetime.fromisoformat(
                    last_activity.decode("utf-8").strip()
                )
                if self.last_activity is None or last_activity > self.last_activity:
                    self.last_activity = last_activity
            else:
                self.last_activity = "running"
                return

    @property
    def has_stop_inactive_label(self):
        label = config["stop_inactive"]["label"]

        for image in self.images:
            if image["labels"].get(label) == "true":
                return True

        return False

    @property
    def has_remove_obsolete_label(self):
        label = config["remove_obsolete"]["label"]

        for image in self.images:
            if image["labels"].get(label) == "true":
                return True

        return False

    @property
    def flags(self):
        flags = []
        if self.has_stop_inactive_label:
            flags.append("stop_inactive")
        if self.has_remove_obsolete_label:
            flags.append("remove_obsolete")
        return flags
