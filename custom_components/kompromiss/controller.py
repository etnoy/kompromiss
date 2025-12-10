"""Controller for computing simulated outdoor temperature."""

from homeassistant.core import HomeAssistant


class SimulatedOutdoorTemperatureController:
    """Controller that computes the simulated outdoor temperature."""

    TEMPERATURE_OFFSET = 10.0

    def __init__(self, hass: HomeAssistant, actual_temperature_entity_id: str):
        """Initialize the controller.

        Args:
            hass: The Home Assistant instance
            actual_temperature_entity_id: The entity ID of the actual outdoor temperature sensor
        """
        self.hass = hass
        self.actual_temperature_entity_id = actual_temperature_entity_id

    def get_simulated_temperature(self) -> float | None:
        """Get the simulated outdoor temperature by applying offset to actual temperature.

        Returns:
            The simulated temperature, or None if the actual temperature cannot be retrieved.
        """
        if not self.actual_temperature_entity_id:
            return None

        state = self.hass.states.get(self.actual_temperature_entity_id)
        if state is None:
            return None

        try:
            return float(state.state) + self.TEMPERATURE_OFFSET
        except (ValueError, TypeError):
            return None
