"""Controller for computing simulated outdoor temperature."""

from typing import Callable, Any

from homeassistant.core import HomeAssistant, Event, EventStateChangedData
from homeassistant.helpers.event import async_track_state_change_event

from .regulator.passthrough import PassthroughRegulator


class SimulatedOutdoorTemperatureController:
    """Controller that coordinates data flow between sensors and the chosen control algorithm."""

    TEMPERATURE_OFFSET = 10.0

    def __init__(self, hass: HomeAssistant, actual_temperature_entity_id: str):
        self._hass = hass
        self._actual_temperature_entity_id = actual_temperature_entity_id
        self._regulator = PassthroughRegulator()
        self._unsub = None
        self._subscribers: list[Callable[[float | None], Any]] = []

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
        for callback in self._subscribers:
            await self._hass.async_add_executor_job(callback, temperature)

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
        new_indoor_temperature = event.data.get("new_state")
        await self._regulator.set_state(new_indoor_temperature)
        await self._regulator.async_regulate()
        simulated_outdoor_temperature = await self._regulator.get_output()
        await self._notify_subscribers(simulated_outdoor_temperature)
