import httpx
import trafilatura
from urllib.robotparser import RobotFileParser

from .base import ExtractedPage


class URLExtractor:

    async def extract(self, url: str):

        robots_url = url.rstrip("/") + "/robots.txt"

        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()

        if not rp.can_fetch("*", url):
            raise PermissionError("Blocked by robots.txt")

        async with httpx.AsyncClient() as client:

            response = await client.get(url, timeout=30)

            response.raise_for_status()

        downloaded = trafilatura.extract(
            response.text,
            include_tables=True,
            with_metadata=True,
        )

        return [
            ExtractedPage(
                page_number=1,
                content=downloaded if downloaded else "",
                content_type="text",
                metadata={
                    "url": url,
                },
            )
        ]