# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import json
from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT
import re
from datetime import datetime

from .config import config


async def get_containers():
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
    ls = json.loads(stdout)

    return [
        Container(line["Name"], line["Status"], line["ConfigFiles"].split(","))
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

    def __init__(self, name, status, files):
        self.name = name
        self.status = status
        self.files = files
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

    async def boot(self):
        process = await create_subprocess_exec(
            "docker",
            "compose",
            *self._configs(),
            "up",
            "-d",
            stdout=PIPE,
            stderr=STDOUT,
        )
        stdout, _ = await process.communicate()
        return stdout

    async def rm(self):
        process = await create_subprocess_exec(
            "docker",
            "compose",
            *self._configs(),
            "down",
            "--rmi",
            "local",
            "--volumes",
            stdout=PIPE,
            stderr=STDOUT,
        )
        stdout, _ = await process.communicate()
        return stdout

    async def kill(self):
        process = await create_subprocess_exec(
            "docker", "compose", "-p", self.name, "kill", stdout=PIPE, stderr=STDOUT
        )
        stdout, _ = await process.communicate()
        return stdout

    async def logs(self, break_on=None):
        break_on = break_on or {}
        process = await create_subprocess_exec(
            "docker",
            "compose",
            "-p",
            self.name,
            "logs",
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
            r'.*\| (?P<timestamp>(:?\d|-)+ (:?\d|-|:)+)(?:,\d+)? \d+ .+ "(GET|POST|PUT|DELETE) (?P<url>\S+) HTTP.*'
        )

        process = await create_subprocess_exec(
            "docker",
            "compose",
            *self._configs(),
            "logs",
            stdout=PIPE,
            stderr=STDOUT,
        )
        stdout, _ = await process.communicate()
        lines = stdout.decode("utf-8").split("\n")
        for line in reversed(lines):
            match = access_re.match(line)
            if match:
                date = datetime.fromisoformat(match.group("timestamp"))
                self.last_url = match.group("url")
                self.last_access = date
                return

        return stdout.decode("utf-8")

    async def get_last_activity(self):
        # TODO
        return None
