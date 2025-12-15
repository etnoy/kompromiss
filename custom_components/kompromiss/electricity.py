from __future__ import annotations
import logging
from typing import Final


from datetime import timedelta
from homeassistant.util import dt as dt_util

_LOGGER: Final = logging.getLogger(__name__)


class ElectricityPriceData:
    """Class to fetch electricity price data from Nordpool."""

    def __init__(self, start_time: str, end_time: str, price: float):
        self.start_time: str = start_time
        self.end_time: str = end_time
        self.price: float = price

    def __repr__(self):
        return f"Price is {self.price} from {self.start_time} to {self.end_time}"


async def fetch_next_24h_prices_15m(
    hass,
    *,
    area: str,
    currency: str | None = None,
) -> list[dict]:
    _LOGGER.debug(
        "Fetching electricity prices for area=%s, currency=%s",
        area,
        currency,
    )

    # Get the first Nordpool entry id
    entries = hass.config_entries.async_entries("nordpool")
    if not entries:
        raise RuntimeError(
            "No Nordpool config entry found, ensure the official Nordpool integration is set up (not HACS)"
        )
    config_entry_id = entries[0].entry_id

    now = dt_util.utcnow()
    end = now + timedelta(hours=24)

    async def _fetch(date):
        service_data = {
            "config_entry": config_entry_id,
            "date": str(date),
            "areas": area,
            # For 15-min markets:
            "resolution": 15,
        }

        if currency:
            service_data["currency"] = currency

        _LOGGER.debug("Fetching electricity prices with data: %s", service_data)

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
                ElectricityPriceData(
                    start_utc.isoformat(),
                    p.get("end"),
                    float(p["price"]),
                )
            )

    out.sort(key=lambda x: x.start_time)
    _LOGGER.debug("Fetched electricity prices: %s", out)
    return out
