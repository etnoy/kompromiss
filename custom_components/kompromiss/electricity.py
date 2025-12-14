from __future__ import annotations

from datetime import timedelta
from homeassistant.util import dt as dt_util


async def fetch_next_24h_prices_15m(
    hass,
    *,
    config_entry_id: str,
    area: str,
    currency: str | None = None,
) -> list[dict]:
    now = dt_util.utcnow()
    end = now + timedelta(hours=24)

    async def _fetch(date):
        service_data = {
            "config_entry": config_entry_id,
            "date": str(date),
            "areas": [area],
            # For 15-min markets:
            "resolution": 15,
        }
        if currency:
            service_data["currency"] = currency

        return await hass.services.async_call(
            "nordpool",
            "get_price_indices_for_date",
            service_data,
            blocking=True,
            return_response=True,
        )

    today_resp = await _fetch(dt_util.now().date())
    tomorrow_resp = await _fetch((dt_util.now() + timedelta(days=1)).date())

    # Response shape is a mapping keyed by area, e.g. {"FI": [{start, end, price}, ...]}
    points = (today_resp.get(area) or []) + (tomorrow_resp.get(area) or [])

    # Keep only points that start within [now, now+24h)
    out = []
    for p in points:
        start = dt_util.parse_datetime(p["start"])
        if start is None:
            continue
        start_utc = dt_util.as_utc(start)
        if now <= start_utc < end:
            out.append(
                {
                    "start": start_utc.isoformat(),
                    "end": p.get("end"),
                    "price": p["price"],
                }
            )

    out.sort(key=lambda x: x["start"])
    return out
