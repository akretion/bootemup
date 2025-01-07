# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from aiohttp import web
from asyncio import sleep
from asyncio.subprocess import create_subprocess_exec, PIPE, STDOUT
from contextlib import asynccontextmanager


def url_for(name):
    return f"http://{name}.localhost"


@asynccontextmanager
async def html(response):
    await response.write(b"<html>")
    await response.write(b"<head>")
    await response.write(
        b'<link rel="stylesheet" href="https://cdn.simplecss.org/simple.min.css" />'
    )
    await response.write(b"</head>")
    await response.write(b"<body>")

    yield

    await response.write(b"</body>")
    await response.write(b"</html>")
    await response.write_eof()


async def get_infos():
    process = await create_subprocess_exec(
        "docker", "compose", "ls", "--all", "--format", "json", stdout=PIPE
    )
    stdout, _ = await process.communicate()
    return json.loads(stdout)


async def with_scroll(response):
    await response.write(b"<script>")
    await response.write(
        b"const autoScroll = setInterval(() => { window.scrollTo(0, document.body.scrollHeight); }, 17);"
        b"window.addEventListener('wheel', () => { clearInterval(autoScroll); });"
        b"window.addEventListener('touchmove', () => { clearInterval(autoScroll); });"
    )
    await response.write(b"</script>")


async def with_redirect(response, url):
    await response.write(b"<footer>")
    await response.write(f'Redirecting to <a href="{url}">{url}</a>...'.encode())
    await response.write(b"</footer>")

    # wait a bit before redirecting
    await sleep(2)

    # TODO: wait for the client to be ready directly

    await response.write(b"<script>")
    await response.write(
        f"window.addEventListener('load', () => {{ window.location.href = '{url}'; }});".encode()
    )
    await response.write(b"</script>")


async def info(request):
    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "text/html"},
    )
    await response.prepare(request)

    async with html(response):
        await response.write(b"<table>")

        data = await get_infos()

        keys = {key: None for line in data for key in line.keys()}
        keys["Actions"] = None

        await response.write(b"<thead>")
        for key in keys:
            await response.write(f"<th>{key}</th>".encode())
        await response.write(b"</thead>")

        await response.write(b"<tbody>")
        for line in data:
            await response.write(b"<tr>")
            for key in keys:
                if key == "Actions":
                    name = line["Name"]
                    state = line["Status"]
                    value = ""
                    if "exited" in state:
                        value += f'<a href="/boot/{name}">Boot</a> '
                    if "running" in state:
                        value += f'<a href="{url_for(name)}">Open</a> '
                        value += f'<a href="/kill/{name}">Kill</a> '

                else:
                    value = line.get(key)

                await response.write(f"<td>{value}</td>".encode())
            await response.write(b"</tr>")
        await response.write(b"</tbody>")

        await response.write(b"</table>")

    return response


async def boot(request):
    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "text/html"},
    )

    await response.prepare(request)
    async with html(response):
        await with_scroll(response)

        await response.write(b"<code style='white-space: pre-wrap;'>")

        name = request.match_info.get("name")
        infos = await get_infos()
        info = next((info for info in infos if info["Name"] == name), None)
        if not info:
            await response.write(f"Unknown service {name}".encode())
            return response

        await response.write(f"Booting, {name}...\n\n".encode())

        configs = [
            arg
            for config in info.get("ConfigFiles").split(",")
            for arg in ["-f", config]
        ]

        process = await create_subprocess_exec(
            "docker", "compose", *configs, "up", "-d", stdout=PIPE, stderr=STDOUT
        )
        stdout, _ = await process.communicate()

        if stdout:
            await response.write(stdout)

        process = await create_subprocess_exec(
            "docker", "compose", *configs, "logs", "-f", stdout=PIPE, stderr=STDOUT
        )

        backlog = b""
        while True:
            stdout = await process.stdout.read(256)
            if stdout:
                backlog += stdout
                await response.write(stdout)
                if b"running on" in backlog:
                    process.terminate()
                if b"exited with code" in backlog:
                    process.terminate()
                    return response
            else:
                break

        await response.write(b"</code>")

        await with_redirect(response, url_for(name))

    return response


async def kill(request):
    response = web.StreamResponse(
        status=200,
        headers={"Content-Type": "text/html"},
    )

    await response.prepare(request)
    async with html(response):
        await with_scroll(response)

        await response.write(b"<code style='white-space: pre-wrap;'>")

        name = request.match_info.get("name")
        infos = await get_infos()
        info = next((info for info in infos if info["Name"] == name), None)
        if not info:
            await response.write(f"Unknown service {name}".encode())
            return response

        await response.write(f"Killing, {name}...\n\n".encode())

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
            await response.write(stdout)

        process = await create_subprocess_exec(
            "docker", "compose", *configs, "logs", "-f", stdout=PIPE, stderr=STDOUT
        )

        backlog = b""
        while True:
            stdout = await process.stdout.read(256)
            if stdout:
                backlog += stdout
                await response.write(stdout)
                if b"exited with code" in backlog:
                    process.terminate()
                    return response
                break

        await response.write(b"</code>")

        await with_redirect(response, "/")

    return response


app = web.Application()
app.add_routes(
    [
        web.get("/", info),
        web.get("/boot/{name}", boot),
        web.get("/kill/{name}", kill),
    ]
)

if __name__ == "__main__":
    web.run_app(app, port=1212)
