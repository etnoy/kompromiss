"""Controller for computing simulated outdoor temperature."""

from typing import Callable, Any, Final
import logging

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .electricity import (
    ElectricityPriceData,
    fetch_next_24h_prices_15m,
)

from .state import ControllerState


from .regulator.mpc import MPCRegulator
from .const import (
    SIGNAL_MPC_WEIGHT_TEMP_DEVIATION_CHANGED,
    SIGNAL_MPC_WEIGHT_COMFORT_VIOLATION_CHANGED,
)

_LOGGER: Final = logging.getLogger(__name__)


class TemperatureController:
    """Coordinates data flow between sensors and regulator."""

    def __init__(
        self,
        hass: HomeAssistant,
        actual_temperature_entity_id: str,
        simulated_temperature_entity_id: str,
        indoor_temperature_entity_id: str,
    ):
        self._hass = hass
        self._actual_outdoor_temperature_entity_id = actual_temperature_entity_id
        self._simulated_outdoor_temperature_entity_id = simulated_temperature_entity_id
        self._indoor_temperature_entity_id = indoor_temperature_entity_id
        self._regulator: MPCRegulator = MPCRegulator()
        self._unsub = None
        self._unsub_dispatchers = []
        self._subscribers: list[Callable[[float | None], Any]] = []
        self._state = ControllerState()
        self._price_data: list[ElectricityPriceData] = []

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

    def _compute_temperature_offset(self) -> float | None:
        """Get the current temperature offset (simulated - actual)."""
        if (
            self._state.simulated_outdoor_temperature is None
            or self._state.actual_outdoor_temperature is None
        ):
            return None
        return (
            self._state.simulated_outdoor_temperature
            - self._state.actual_outdoor_temperature
        )

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

        # Subscribe to MPC weight parameter changes
        self._unsub_dispatchers.append(
            async_dispatcher_connect(
                self._hass,
                SIGNAL_MPC_WEIGHT_TEMP_DEVIATION_CHANGED,
                self._handle_weight_temp_deviation_changed,
            )
        )
        self._unsub_dispatchers.append(
            async_dispatcher_connect(
                self._hass,
                SIGNAL_MPC_WEIGHT_COMFORT_VIOLATION_CHANGED,
                self._handle_weight_comfort_violation_changed,
            )
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

        if not self._price_data:
            _LOGGER.debug("Fetching initial electricity price data")
            self._price_data = await fetch_next_24h_prices_15m(
                self._hass,
                area="SE3",
                currency="SEK",
            )

        if not self._price_data:
            raise RuntimeError("No electricity price data available")

        self._state.electricity_price = self._price_data

        self._regulator.set_state(self._state)

        await self._regulate()

    async def _regulate(self) -> None:
        """Invoke the regulator to compute new simulated outdoor temperature."""

        await self._regulator.async_regulate()
        regulator_output = self._regulator.get_state()
        self._state.simulated_outdoor_temperature = (
            regulator_output.simulated_outdoor_temperature
        )
        self._state.offset = regulator_output.offset

        await self._notify_subscribers()

    async def _handle_weight_temp_deviation_changed(self, value: float) -> None:
        """Handle weight temperature deviation parameter change."""
        self._regulator.set_weight_temperature_deviation(value)

    async def _handle_weight_comfort_violation_changed(self, value: float) -> None:
        """Handle weight comfort band violation parameter change."""
        self._regulator.set_weight_comfort_band_violation(value)

    async def update_parameters_from_options(self, options: dict) -> None:
        """Update regulator parameters from config entry options.

        Args:
            options: Dictionary of options from config entry
        """
        self._regulator.update_parameters_from_options(options)
        await self._regulate()
