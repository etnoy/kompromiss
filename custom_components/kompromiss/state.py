class ControllerState:
    """Holds the current state of the controller."""

    def __init__(self):
        self.simulated_outdoor_temperature: float | None = None
        self.actual_outdoor_temperature: float | None = None
        self.indoor_temperature: float | None = None
        self.offset: float | None = None

    def is_valid(self) -> bool:
        """Check if the state has valid temperature readings."""
        return (
            self.simulated_outdoor_temperature is not None
            and self.actual_outdoor_temperature is not None
            and self.indoor_temperature is not None
        )
