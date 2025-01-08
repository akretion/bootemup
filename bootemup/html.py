# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from aiohttp import web, request
from contextlib import asynccontextmanager
from asyncio import sleep
from inspect import cleandoc as dedent


class Html:
    __self_closing_tags__ = [
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    ]

    def __init__(self, request):
        self.request = request

    async def __tag__(self, name, state, *args, **kwargs):
        if state == "close":
            await self(f"</{name}>")
            return

        attrs = " ".join(k for k in args)
        kwattrs = " ".join(f'{k}="{v}"' for k, v in kwargs.items())
        tag = " ".join(s for s in (name, attrs, kwattrs) if s)

        if state == "self-closing":
            tag += " /"

        await self(f"<{tag}>")

    async def _init_(self):
        response = web.StreamResponse(
            status=200,
            headers={"Content-Type": "text/html"},
        )
        await response.prepare(self.request)
        self.response = response

    def __getattr__(self, name):
        if name.startswith("_") or name in dir(self):
            return super().__getattr__(name)

        if name in self.__self_closing_tags__:

            def tag(*args, **kwargs):
                return self.__tag__(name, "self-closing", *args, **kwargs)

        else:

            @asynccontextmanager
            async def tag(*args, **kwargs):
                await self.__tag__(name, "open", *args, **kwargs)
                yield
                await self.__tag__(name, "close", *args, **kwargs)

        tag.__name__ = f"{name}_tag"
        return tag

    async def __call__(self, value):
        if isinstance(value, str):
            value = value.encode("utf-8")
        await self.response.write(value)

    @asynccontextmanager
    async def _page_(self):
        try:
            async with self.html():
                async with self.head():
                    await self.link(
                        rel="stylesheet",
                        href="https://cdn.simplecss.org/simple.min.css",
                    )

                async with self.body():
                    yield
        finally:
            await self.response.write_eof()

    async def _with_scroll_(self):
        async with self.script():
            await self(
                dedent("""
                const autoScroll = setInterval(() => {
                       window.scrollTo(0, document.body.scrollHeight);
                }, 17);
                window.addEventListener('wheel', () => {
                       clearInterval(autoScroll);
                 }, { once: true });
                window.addEventListener('touchmove', () => {
                          clearInterval(autoScroll);
                  }, { once: true });
                """)
            )

    async def _with_redirect_(self, url):
        async with self.footer():
            await self(f'Redirecting to <a href="{url}">{url}</a>...')

            if not url.startswith("http"):
                # wait a bit before redirecting
                await sleep(0.5)
            else:
                # Wait for the client to be ready
                for i in range(50):
                    await self(".")
                    async with request("GET", url) as resp:
                        if resp.status < 400:
                            break

                    await sleep(0.25)

        async with self.script():
            await self(
                dedent(f"""
                window.addEventListener('load', () => {{
                    window.location.href = '{url}'; 
                }});
                """)
            )
