"""Controller for computing simulated outdoor temperature."""

from typing import Callable, Any

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event


from .regulator.passthrough import PassthroughRegulator


class ControllerState:
    """Holds the current state of the controller."""

    def __init__(self):
        self.simulated_temperature: float | None = None
        self.actual_outdoor_temperature: float | None = None
        self.indoor_temperature: float | None = None
        self.offset: float | None = None


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
        self._regulator = PassthroughRegulator()
        self._unsub = None
        self._subscribers: list[Callable[[float | None], Any]] = []
        self._state = ControllerState()

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
            self._state.simulated_temperature is None
            or self._state.actual_outdoor_temperature is None
        ):
            return None
        return (
            self._state.simulated_temperature - self._state.actual_outdoor_temperature
        )

    def async_subscribe(self) -> None:
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

        await self._regulator.set_state(self._state.actual_outdoor_temperature)
        await self._regulator.async_regulate()
        self._state.simulated_temperature = await self._regulator.get_output()
        self._state.offset = self._compute_temperature_offset()

        await self._notify_subscribers()
