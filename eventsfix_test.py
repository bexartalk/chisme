#!/usr/bin/env python3
"""Offline regression tests. Run: python3 eventsfix_test.py (no pytest or venv needed)."""
import asyncio
from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import httpx
import app


async def main():
    urls, responses, tasks = [], [], []
    place = {"city": "San Antonio", "state_abbr": "TX", "country_code": "us"}
    launch = {"id": "test-launch", "name": "Starship test launch", "status": {"abbrev": "Go"}}

    def network(request):
        url = str(request.url)
        urls.append(url)
        if url == app.LL2_UPCOMING:
            return httpx.Response(200, json={"results": [launch]})
        return httpx.Response(200, content=b"<rss><channel/></rss>")

    async def fetch_page(url):
        urls.append(url)
        return "<html></html>"

    async def get_place(lat, lon):
        return dict(place)

    original_events = app.api_events
    create_task = asyncio.create_task

    async def events(*args, **kwargs):
        result = await original_events(*args, **kwargs)
        responses.append(result)
        return result

    def track_task(coro):
        task = create_task(coro)
        tasks.append(task)
        return task

    async with httpx.AsyncClient(transport=httpx.MockTransport(network)) as client:
        with ExitStack() as stack:
            for name, value in {
                "client": lambda: client,
                "fetch_page": fetch_page,
                "get_place": get_place,
                "event_forecast": AsyncMock(return_value=None),
                "api_events": events,
                **{name: AsyncMock(return_value={}) for name in
                   ("api_news", "api_weather", "api_radar", "api_food", "api_sports")},
            }.items():
                stack.enter_context(patch.object(app, name, value))
            stack.enter_context(patch.dict(app._cache, {}, clear=True))
            with patch.object(app.asyncio, "create_task", track_task):
                await app.warm()
            try:
                await asyncio.wait_for(tasks[0], timeout=5)
                assert len(responses) == 1 and isinstance(responses[0], dict), responses
                key = f"events:{app.cell(app.DEFAULT_LAT, app.DEFAULT_LON, 0.02)}"
                assert app._cache[key][1] == responses[0], "warm() must fill the events cache"
                assert "error" not in responses[0], responses[0]
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

            assert any("eventbrite.com" in u for u in urls), urls
            assert any("allevents.in" in u for u in urls), urls

            # The selected Starbase cell must work even if geocoding calls it Boca Chica.
            for city_name in ("Starbase", "Boca Chica"):
                app._cache.clear()
                urls.clear()
                place["city"] = city_name
                result = await app.api_events(lat=None, lon=None, city="starbase")
                assert isinstance(result, dict) and "error" not in result, result
                launches = await app.api_launches()
                assert launches["launches"][0]["id"] == launch["id"], launches
                assert launches["launches"][0]["name"] == launch["name"], launches
                assert app.LL2_UPCOMING in urls, urls
                assert not any("eventbrite.com" in u or "allevents.in" in u for u in urls), urls
                assert not any(s["id"] in ("eventbrite", "eventbrite2", "allevents")
                               for s in result["sources"]), result["sources"]

    print("PASS: startup events cache, other-city sources, Starbase sources and launches")


if __name__ == "__main__":
    asyncio.run(main())
