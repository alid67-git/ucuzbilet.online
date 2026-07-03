from contextlib import asynccontextmanager
import os
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


class ScraperSession:
    """Tek Chromium oturumu — her aramada tarayici yeniden acilmaz."""

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def start(self) -> None:
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        launch_kwargs: dict = {
            "headless": self.headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if os.environ.get("RENDER") or Path("/.dockerenv").exists():
            launch_kwargs["args"].extend(
                [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ]
            )
        for channel in ("chrome", "msedge"):
            try:
                self._browser = await self._playwright.chromium.launch(channel=channel, **launch_kwargs)
                break
            except Exception:
                continue
        if not self._browser:
            self._browser = await self._playwright.chromium.launch(**launch_kwargs)

        self._context = await self._browser.new_context(
            locale="tr-TR",
            timezone_id="Europe/Istanbul",
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

    async def new_page(self) -> Page:
        if not self._context:
            await self.start()
        assert self._context is not None
        page = await self._context.new_page()
        page.set_default_timeout(25000)
        return page

    async def close(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    @asynccontextmanager
    async def page(self):
        page = await self.new_page()
        try:
            yield page
        finally:
            await page.close()
