from typing import Any

from .electricity import ElectricityPriceData


class ControllerState:
    """Holds the current state of the controller."""

    def __init__(self):
        self.timestamps: list[str] = []
        self.simulated_outdoor_temperatures: list[dict[str, Any]] | None = None
        self.actual_outdoor_temperature: float | None = None
        self.indoor_temperature: float | None = None
        self.projected_indoor_temperature: list[dict[str, Any]] | None = None
        self.projected_thermal_power: list[dict[str, Any]] | None = None
        self.outdoor_temperature_offsets: list[dict[str, Any]] | None = None
        self.medium_temperature: float | None = None
        self.projected_medium_temperature: list[dict[str, Any]] | None = None
        self.return_temperature_setpoint: float | None = None
        self.computation_time: float | None = None
        self.electricity_price: list[ElectricityPriceData] = []

    def is_valid(self) -> bool:
        """Check if the state has valid temperature readings."""
        return (
            self.actual_outdoor_temperature is not None
            and self.indoor_temperature is not None
        )
