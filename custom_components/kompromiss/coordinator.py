from __future__ import annotations

from datetime import timedelta
from typing import Any, List

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SOT_NUMBER,
    CONF_TEMPERATURE_SENSORS,
    CONF_PRICE_SENSOR,
    CONF_MINIMUM_INDOOR_TEMPERATURE,
    CONF_MAXIMUM_INDOOR_TEMPERATURE,
    CONF_SOT_MIN,
    CONF_SOT_MAX,
    CONF_STEP_MINUTES,
    CONF_HORIZON_STEPS,
    CONF_ENABLED,
)
from .controller import ControllerConfig, SimplePriceAwareController


def _float_or_none(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class KompromissCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        data = {**entry.data, **(entry.options or {})}

        self.sot_number = data[CONF_SOT_NUMBER]
        self.temp_sensors: List[str] = list(data[CONF_TEMPERATURE_SENSORS])
        self.nordpool_sensor = data[CONF_PRICE_SENSOR]

        self.enabled = bool(data.get(CONF_ENABLED, True))
        self.cfg = ControllerConfig(
            minimum_indoor_temperature=float(data.get(CONF_MINIMUM_INDOOR_TEMPERATURE)),
            maximum_indoor_temperature=float(data.get(CONF_MAXIMUM_INDOOR_TEMPERATURE)),
            sot_min=float(data.get(CONF_SOT_MIN)),
            sot_max=float(data.get(CONF_SOT_MAX)),
            step_minutes=int(data.get(CONF_STEP_MINUTES)),
            horizon_steps=int(data.get(CONF_HORIZON_STEPS)),
        )
        self.controller = SimplePriceAwareController(self.cfg)

        super().__init__(
            hass,
            logger=hass.helpers.logger.LoggerAdapter(__name__),
            name="Heat Price Optimizer Coordinator",
            update_interval=timedelta(minutes=self.cfg.step_minutes),
        )

    async def _async_get_prices(self) -> list[float]:
        # Expect Nordpool sensor with 'today'/'tomorrow' attributes or state as current price
        state = self.hass.states.get(self.nordpool_sensor)
        if not state:
            return []
        attrs = state.as_dict().get("attributes", {})
        series = []
        # Nordpool integration often exposes "raw_today" / "raw_tomorrow" or "today"/"tomorrow"
        for key in ("today", "tomorrow", "raw_today", "raw_tomorrow"):
            v = attrs.get(key)
            if isinstance(v, list):
                # Items can be dicts with "value" or plain floats
                for item in v:
                    if isinstance(item, dict) and "value" in item:
                        try:
                            series.append(float(item["value"]))
                        except (TypeError, ValueError):
                            pass
                    else:
                        try:
                            series.append(float(item))
                        except (TypeError, ValueError):
                            pass
        # Fallback: use current state as first price
        try:
            price_now = float(state.state)
            if not series:
                series = [price_now]
            else:
                series[0] = price_now
        except (TypeError, ValueError):
            pass

        if not series:
            return []
        # Return next horizon steps
        return series[: max(self.cfg.horizon_steps, 1)]

    async def _async_get_temps(self) -> list[float]:
        temps: list[float] = []
        for ent_id in self.temp_sensors:
            st = self.hass.states.get(ent_id)
            temps.append(_float_or_none(st.state) if st else None)
        # Filter Nones
        temps = [t for t in temps if t is not None]
        return temps

    async def _async_write_sot(self, sot: float) -> None:
        # Write to the selected number entity
        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": self.sot_number, "value": float(sot)},
            blocking=False,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False}

        temps = await self._async_get_temps()
        prices = await self._async_get_prices()

        if not temps or not prices:
            raise UpdateFailed("Missing temperatures or prices")

        result = self.controller.compute(temps, prices)

        if result.get("sot") is not None:
            await self._async_write_sot(result["sot"])

        data = {
            "enabled": True,
            "sot": result.get("sot"),
            "virtual_temp": result.get("virtual_temp"),
            "coldest": result.get("coldest"),
            "hottest": result.get("hottest"),
            "prices": prices,
            "temps": temps,
        }
        return data
