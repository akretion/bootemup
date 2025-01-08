# Copyright 2025 Akretion (http://www.akretion.com).
# @author Florian Mounier <florian.mounier@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from aiohttp import web, request
from contextlib import asynccontextmanager
from asyncio import sleep
from inspect import cleandoc as dedent
from datetime import datetime


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

    async def _init_(self):
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/html",
                "Cache-Control": "max-age=0, no-cache, must-revalidate, proxy-revalidate",
            },
        )
        await response.prepare(self.request)
        self.response = response

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
        if value is None:
            return

        if isinstance(value, (list, tuple, set)):
            async with self.ul():
                for val in value:
                    async with self.li():
                        await self(val)
            return
        if isinstance(value, datetime):
            async with self.time(datetime=value.isoformat()):
                await self(value.strftime("%Y-%m-%d %H:%M:%S"))
            return

        if isinstance(value, str):
            value = value.encode("utf-8")

        await self.response.write(value)

    @asynccontextmanager
    async def _page_(self, full_width=False):
        try:
            async with self.html():
                async with self.head():
                    # Alternative: "https://cdn.simplecss.org/simple.min.css"
                    await self.meta(charset="utf-8")
                    await self.link(
                        rel="stylesheet",
                        href="https://unpkg.com/sakura.css/css/sakura.css",
                        media="screen",
                    )
                    await self.link(
                        rel="stylesheet",
                        href="https://unpkg.com/sakura.css/css/sakura-dark.css",
                        media="screen and (prefers-color-scheme: dark)",
                    )
                    async with self.script():
                        # Try to prevent browser bfcache
                        await self(
                            dedent(
                                """
                                window.addEventListener('pageshow', (event) => {
                                    if (event.persisted) {
                                    location.reload(true);
                                    }
                                });
                                """
                            )
                        )
                async with self.body(
                    **({"style": "max-width: 90%;"} if full_width else {})
                ):
                    yield
        finally:
            await self.response.write_eof()

    async def _with_scroll_(self):
        async with self.script():
            await self(
                dedent("""
                const autoScroll = setInterval(() => {
                       window.scrollTo({top: document.body.scrollHeight, behavior: 'instant' });
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
            await self("Redirecting to ")
            async with self.a(href=url):
                await self(url)
            await self("…")

            if not url.startswith("http"):
                # wait a bit before redirecting
                await sleep(0.5)
            else:
                # Wait for the client to be ready
                for i in range(250):
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
