"""Controller for computing simulated outdoor temperature."""

import time
from typing import Callable, Any, Final
import logging

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ELECTRICITY_PRICE_AREA,
    ELECTRICITY_PRICE_CURRENCY,
    ELECTRICITY_PRICE_ENABLED,
    ELECTRICITY_PRICE_UPDATE_INTERVAL,
)

from .electricity import (
    ElectricityPriceData,
    fetch_next_24h_prices_15m,
)

from .state import ControllerState


from .regulator.mpc import MPCRegulator


_LOGGER: Final = logging.getLogger(__name__)


class TemperatureController:
    """Coordinates data flow between sensors and regulator."""

    def __init__(
        self,
        hass: HomeAssistant,
        actual_temperature_entity_id: str,
        indoor_temperature_entity_id: str,
    ):
        self._hass = hass
        self._actual_outdoor_temperature_entity_id = actual_temperature_entity_id
        self._indoor_temperature_entity_id = indoor_temperature_entity_id
        self._regulator: MPCRegulator = MPCRegulator()
        self._unsub = None
        self._unsub_dispatchers = []
        self._subscribers: list[Callable[[float | None], Any]] = []
        self._state = ControllerState()
        self._price_control_enabled = False
        self._price_area: str | None = None
        self._price_currency: str | None = None
        self._price_last_updated_at: float | None = None

    def async_subscribe_sensor(self, callback: Callable[[float | None], Any]) -> None:
        """Subscribe a sensor to state change notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def async_unsubscribe_sensor(self, callback: Callable[[float | None], Any]) -> None:
        """Unsubscribe a sensor from state change notifications."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _notify_subscribers(self) -> None:
        """Notify all subscribers of state changes."""
        for callback in self._subscribers:
            callback(self._state)

    async def async_subscribe(self) -> None:
        """Register a listener for state updates."""
        self._unsub = async_track_state_change_event(
            self._hass,
            [
                self._actual_outdoor_temperature_entity_id,
                self._indoor_temperature_entity_id,
            ],
            self._handle_state_change,
        )

    def async_unsubscribe(self) -> None:
        if getattr(self, "_unsub", None):
            self._unsub()
            self._unsub = None

        # Unsubscribe from all dispatcher signals
        for unsub in self._unsub_dispatchers:
            unsub()
        self._unsub_dispatchers.clear()

    async def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Runs on each outdoor temperature change and calls the regulator."""
        new_state = event.data.get("new_state")

        value = None

        # Extract and store actual temperature
        if new_state and new_state.state not in ("unknown", "unavailable"):
            try:
                value = float(new_state.state)
            except (ValueError, TypeError):
                # TODO: This error state must be handled better in the future
                pass

        entity_id = event.data.get("entity_id")
        if entity_id == self._actual_outdoor_temperature_entity_id:
            self._state.actual_outdoor_temperature = value
        elif entity_id == self._indoor_temperature_entity_id:
            self._state.indoor_temperature = value

        if self._price_control_enabled and not self._state.electricity_price:
            await self._update_price_data()

        if self._price_control_enabled and not self._state.electricity_price:
            raise RuntimeError("No electricity price data available")

        self._regulator.set_state(self._state)

        await self._regulate()

    async def _regulate(self) -> None:
        """Invoke the regulator to compute new simulated outdoor temperature."""

        if self._state is None or not self._state.is_valid():
            _LOGGER.debug("Controller state is not valid, skipping regulation")
            return

        current_time = time.time()

        if self._price_last_updated_at is None or (
            current_time - self._price_last_updated_at
            >= ELECTRICITY_PRICE_UPDATE_INTERVAL
        ):
            await self._update_price_data()
            self._regulator.set_state(self._state)

        await self._regulator.async_regulate()
        self._state = self._regulator.get_state()

        await self._notify_subscribers()

    async def _update_price_data(self) -> None:
        """Fetch updated electricity price data."""
        if not self._price_control_enabled:
            return

        _LOGGER.debug(
            "Fetching updated electricity price data for area %s and currency %s",
            self._price_area,
            self._price_currency,
        )

        try:
            self._state.electricity_price = await fetch_next_24h_prices_15m(
                self._hass,
                area=self._price_area,
                currency=self._price_currency,
            )

            if not self._state.electricity_price:
                _LOGGER.error("No electricity price data was fetched")

            self._price_last_updated_at = time.time()

        except Exception as e:
            _LOGGER.error(
                "Failed to fetch electricity price data: %s",
                e,
            )
            self._state.electricity_price = []

    async def update_parameters_from_options(self, options: dict) -> None:
        """Update regulator parameters from config entry options."""

        update_price_data = False

        price_control_enabled = options.get(
            ELECTRICITY_PRICE_ENABLED, self._price_control_enabled
        )
        if price_control_enabled != self._price_control_enabled:
            self._price_control_enabled = price_control_enabled
            update_price_data = price_control_enabled

        if self._price_control_enabled:
            price_area = options.get(ELECTRICITY_PRICE_AREA, self._price_area)
            if not price_area or price_area.strip() == "":
                raise ValueError(
                    "Electricity price area must be set when price control is enabled"
                )

            self._price_area = price_area

            price_currency = options.get(
                ELECTRICITY_PRICE_CURRENCY, self._price_currency
            )
            if not price_currency or price_currency.strip() == "":
                raise ValueError(
                    "Electricity price currency must be set when price control is enabled"
                )
            self._price_currency = price_currency
        else:
            self._state.electricity_price = []
            self._price_area = None
            self._price_currency = None

        if self._price_control_enabled and update_price_data:
            await self._update_price_data()
            self._regulator.set_state(self._state)

        self._regulator.update_parameters_from_options(options)
        await self._regulate()
