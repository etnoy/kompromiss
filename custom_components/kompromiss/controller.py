"""Controller for computing simulated outdoor temperature."""

from typing import Callable, Any

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event

from .regulator.passthrough import PassthroughRegulator


class SimulatedOutdoorTemperatureController:
    """Controller that coordinates data flow between sensors and the chosen control algorithm."""

    def __init__(self, hass: HomeAssistant, actual_temperature_entity_id: str):
        self._hass = hass
        self._actual_temperature_entity_id = actual_temperature_entity_id
        self._regulator = PassthroughRegulator()
        self._unsub = None
        self._subscribers: list[Callable[[float | None], Any]] = []
        self._simulated_temperature: float | None = None
        self._actual_temperature: float | None = None

    def async_subscribe_sensor(self, callback: Callable[[float | None], Any]) -> None:
        """Subscribe a sensor to state change notifications."""
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def async_unsubscribe_sensor(self, callback: Callable[[float | None], Any]) -> None:
        """Unsubscribe a sensor from state change notifications."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    async def _notify_subscribers(self, temperature: float | None) -> None:
        """Notify all subscribers of state changes."""
        self._simulated_temperature = temperature
        for callback in self._subscribers:
            callback(temperature)

    async def async_get_simulated_temperature(self) -> float | None:
        """Get the current simulated outdoor temperature."""
        return self._simulated_temperature

    def get_simulated_temperature(self) -> float | None:
        """Get the current simulated outdoor temperature (sync version for properties)."""
        return self._simulated_temperature

    async def async_get_temperature_offset(self) -> float | None:
        """Get the current temperature offset (simulated - actual)."""
        if self._simulated_temperature is None or self._actual_temperature is None:
            return None
        return self._simulated_temperature - self._actual_temperature

    def get_temperature_offset(self) -> float | None:
        """Get the current temperature offset (simulated - actual, sync version for properties)."""
        if self._simulated_temperature is None or self._actual_temperature is None:
            return None
        return self._simulated_temperature - self._actual_temperature

    def async_subscribe(self) -> None:
        """Register a listener for temperature updates."""
        self._unsub = async_track_state_change_event(
            self._hass,
            [self._actual_temperature_entity_id],
            self._handle_temperature_change,
        )

    def async_unsubscribe(self) -> None:
        if getattr(self, "_unsub", None):
            self._unsub()
            self._unsub = None

    async def _handle_temperature_change(
        self, event: Event[EventStateChangedData]
    ) -> None:
        """Runs on each temperature change and calls the regulator."""
        new_state = event.data.get("new_state")

        # Extract and store actual temperature
        if new_state and new_state.state not in ("unknown", "unavailable"):
            try:
                self._actual_temperature = float(new_state.state)
            except (ValueError, TypeError):
                # TODO: This error state must be handled better in the future
                self._actual_temperature = None
        else:
            self._actual_temperature = None

        await self._regulator.set_state(new_state)
        await self._regulator.async_regulate()
        simulated_outdoor_temperature = await self._regulator.get_output()
        await self._notify_subscribers(simulated_outdoor_temperature)
