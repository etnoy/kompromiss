"""Model Predictive Control regulator for temperature control.

This implementation models a building with a 1R1C indoor envelope plus a
thermal medium (e.g. hydronic water loop) that is heated by the heat pump.
The medium transfers heat to the room and loses heat to the environment. The
heat pump controls the return temperature of the medium using a linear heat
curve that maps outdoor temperature to the desired return temperature.
"""

from __future__ import annotations

import logging
import time
from typing import Final
from datetime import datetime, timezone

import numpy as np
import casadi as ca

from ..const import (
    DEFAULT_COMFORT_BAND_VIOLATION_PENALTY,
    DEFAULT_ELECTRICITY_PRICE_AREA,
    DEFAULT_ELECTRICITY_PRICE_CURRENCY,
    DEFAULT_ELECTRICITY_PRICE_ENABLED,
    DEFAULT_ENERGY_COST_PENALTY,
    DEFAULT_HEAT_CURVE_INTERCEPT,
    DEFAULT_HEAT_CURVE_SLOPE,
    DEFAULT_HEATER_THERMAL_POWER,
    DEFAULT_HEATER_TRANSFER_COEFFICIENT,
    DEFAULT_MAXIMUM_MEDIUM_RETURN_TEMPERATURE,
    DEFAULT_MEDIUM_THERMAL_CAPACITY,
    DEFAULT_MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
    DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
    DEFAULT_MINIMUM_INDOOR_TEMPERATURE,
    DEFAULT_MINIMUM_MEDIUM_RETURN_TEMPERATURE,
    DEFAULT_OUTDOOR_RAMP_LIMIT,
    DEFAULT_PREDICTION_HORIZON,
    DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY,
    DEFAULT_TARGET_TEMPERATURE,
    DEFAULT_TEMPERATURE_DEVIATION_PENALTY,
    DEFAULT_THERMAL_CAPACITANCE,
    DEFAULT_THERMAL_RESISTANCE,
    DEFAULT_TIME_STEP,
    ELECTRICITY_PRICE_TIME_STEP,
    ELECTRICITY_PRICE_MINIMUM_HOURS_AVAILABLE,
)

from . import Regulator
from ..state import ControllerState


_LOGGER: Final = logging.getLogger(__name__)


class MPCParameters:
    """Holds parameters for the MPC regulator."""

    # Building envelope (room) parameters
    thermal_resistance: float = DEFAULT_THERMAL_RESISTANCE
    thermal_capacitance: float = DEFAULT_THERMAL_CAPACITANCE

    # Thermal medium (water loop) parameters
    medium_to_building_thermal_resistance: float = (
        DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE
    )
    medium_to_outdoor_thermal_resistance: float = (
        DEFAULT_MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE
    )
    medium_thermal_capacity: float = DEFAULT_MEDIUM_THERMAL_CAPACITY

    heater_thermal_power: float = DEFAULT_HEATER_THERMAL_POWER
    heater_transfer_coefficient: float = DEFAULT_HEATER_TRANSFER_COEFFICIENT
    minimum_medium_return_temperature: float = DEFAULT_MINIMUM_MEDIUM_RETURN_TEMPERATURE
    maximum_medium_return_temperature: float = DEFAULT_MAXIMUM_MEDIUM_RETURN_TEMPERATURE

    heat_curve_slope: float = DEFAULT_HEAT_CURVE_SLOPE
    heat_curve_intercept: float = DEFAULT_HEAT_CURVE_INTERCEPT

    # Comfort targets
    target_temperature: float = DEFAULT_TARGET_TEMPERATURE
    lower_temperature_bound: float = DEFAULT_MINIMUM_INDOOR_TEMPERATURE

    # MPC settings
    prediction_horizon: int = DEFAULT_PREDICTION_HORIZON
    time_step: float = DEFAULT_TIME_STEP
    outdoor_ramp_limit: float = DEFAULT_OUTDOOR_RAMP_LIMIT

    # MPC cost weights
    temperature_deviation_penalty: float = DEFAULT_TEMPERATURE_DEVIATION_PENALTY
    comfort_band_violation_penalty: float = DEFAULT_COMFORT_BAND_VIOLATION_PENALTY
    energy_cost_penalty: float = DEFAULT_ENERGY_COST_PENALTY
    simulated_outdoor_move_penalty: float = DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY

    # Electricity price settings
    electricity_price_enabled: bool = DEFAULT_ELECTRICITY_PRICE_ENABLED
    electricity_price_area: str = DEFAULT_ELECTRICITY_PRICE_AREA
    electricity_price_currency: str = DEFAULT_ELECTRICITY_PRICE_CURRENCY

    def __repr__(self) -> str:
        """Return string representation of MPCParameters."""
        # Get all class attributes with defaults
        all_attrs = {
            k: v
            for k, v in type(self).__dict__.items()
            if not k.startswith("_") and not callable(v)
        }
        # Override with any instance attributes
        all_attrs.update(self.__dict__)

        attrs = "\n".join(f"{key}={value!r}" for key, value in all_attrs.items())
        return f"MPCParameters({attrs})"


class MPCRegulator(Regulator):
    """Full MPC regulator using a 1R1C + medium thermal model.

    States:
    - Indoor air temperature (room)
    - Medium temperature (water loop)

    The medium receives heat from the heat pump, transfers heat to the room,
    and loses heat to the environment. The heat pump regulates the return
    temperature setpoint via a linear heat curve of outdoor temperature.
    """

    def __init__(self) -> None:
        self._state: ControllerState = ControllerState()
        self._parameters: MPCParameters = MPCParameters()
        super().__init__()

    def set_state(self, state: ControllerState) -> None:
        """Set the current state including outdoor and indoor temperatures."""
        self._state = state

    def get_state(self) -> ControllerState:
        """Return the current controller state."""
        return self._state

    def update_parameters_from_options(self, options: dict) -> None:
        """Update all MPC parameters from config entry options."""

        _LOGGER.debug("Updating parameters from options: %s", options)

        for key, value in options.items():
            if not hasattr(self._parameters, key):
                raise ValueError(f"Unknown option key: {key}")

            setattr(self._parameters, key, value)

    def _heat_from_return_setpoint(
        self, return_temp: ca.SX, medium_temp: ca.SX
    ) -> ca.SX:
        """Convert a simulated outdoor temperature setpoint to a medium temperature setpoint via the heat curve."""

        delta = return_temp - medium_temp
        raw_heat = self._parameters.heater_transfer_coefficient * delta
        capped = ca.fmin(self._parameters.heater_thermal_power, raw_heat)
        return ca.fmax(0.0, capped)

    def _solve(
        self,
        initial_room_temp: float,
        initial_medium_temp: float,
        prev_simulated_outdoor: float,
        horizon: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Solve MPC using CasADi IPOPT with room + medium dynamics."""

        if self._parameters.heat_curve_slope == 0:
            raise RuntimeError("Heat curve slope cannot be zero")

        def _simulated_outdoor(u: ca.SX) -> ca.SX:
            return (
                u - self._parameters.heat_curve_intercept
            ) / self._parameters.heat_curve_slope

        # Decision variables
        return_temp_setpoints = ca.SX.sym("u_return", horizon)
        room_temps = ca.SX.sym("x_room", horizon + 1)
        medium_temps = ca.SX.sym("x_medium", horizon + 1)
        slack_lower = ca.SX.sym("sL", horizon)
        slack_upper = ca.SX.sym("sH", horizon)

        # Objective function
        objective = 0
        for step in range(horizon):
            # We only penalize temperature error when below the target, not above
            temperature_error = ca.fmin(
                0, room_temps[step] - self._parameters.target_temperature
            )

            # Heat flow is computed from the return setpoint via the heat curve
            heat_flow = self._heat_from_return_setpoint(
                return_temp_setpoints[step], medium_temps[step]
            )

            # Only factor in energy cost if price control is enabled
            energy_cost: float | None = None
            if self._parameters.electricity_price_enabled:
                # Map simulated step to nearest electricity price point
                price_index = int(
                    round(
                        (step * self._parameters.time_step)
                        / ELECTRICITY_PRICE_TIME_STEP
                    )
                )
                price_index = min(
                    len(self._state.electricity_price) - 1, max(0, price_index)
                )

                price = self._state.electricity_price[price_index].price
                energy_cost = (
                    heat_flow / 1000 * price * (self._parameters.time_step / 3600)
                )

            simulated_outdoor_temperature_delta: float

            if step == 0:
                simulated_outdoor_temperature_delta = (
                    _simulated_outdoor(return_temp_setpoints[step])
                    - prev_simulated_outdoor
                )
            else:
                simulated_outdoor_temperature_delta = _simulated_outdoor(
                    return_temp_setpoints[step]
                ) - _simulated_outdoor(return_temp_setpoints[step - 1])

            temperature_deviation_objective = (
                self._parameters.temperature_deviation_penalty * (temperature_error**2)
            )

            comfort_band_objective = self._parameters.comfort_band_violation_penalty * (
                slack_lower[step] ** 2 + slack_upper[step] ** 2
            )

            energy_cost_objective = 0
            if self._parameters.electricity_price_enabled:
                if energy_cost is None:
                    raise RuntimeError(
                        "Energy cost is None despite price control being enabled"
                    )

                energy_cost_objective = (
                    self._parameters.energy_cost_penalty * energy_cost
                )

            outdoor_move_penalty = self._parameters.simulated_outdoor_move_penalty * (
                simulated_outdoor_temperature_delta**2
            )

            # Add all the objectives together
            objective = (
                objective
                + temperature_deviation_objective
                + comfort_band_objective
                + energy_cost_objective
                + outdoor_move_penalty
            )

        constraints: list[ca.SX] = []
        constraints_lower: list[float] = []
        constraints_upper: list[float] = []

        # Initial conditions
        constraints.append(room_temps[0] - initial_room_temp)
        constraints_lower.append(0.0)
        constraints_upper.append(0.0)

        constraints.append(medium_temps[0] - initial_medium_temp)
        constraints_lower.append(0.0)
        constraints_upper.append(0.0)

        # Dynamics and slack constraints
        for step in range(horizon):
            heat_flow = self._heat_from_return_setpoint(
                return_temp_setpoints[step], medium_temps[step]
            )

            next_room = room_temps[step] + self._parameters.time_step * (
                (self._state.actual_outdoor_temperature - room_temps[step])
                / (
                    self._parameters.thermal_resistance
                    * self._parameters.thermal_capacitance
                )
                + (medium_temps[step] - room_temps[step])
                / (
                    self._parameters.medium_to_building_thermal_resistance
                    * self._parameters.thermal_capacitance
                )
            )

            next_medium = medium_temps[step] + self._parameters.time_step * (
                heat_flow / self._parameters.medium_thermal_capacity
                - (medium_temps[step] - room_temps[step])
                / (
                    self._parameters.medium_to_building_thermal_resistance
                    * self._parameters.medium_thermal_capacity
                )
                - (medium_temps[step] - self._state.actual_outdoor_temperature)
                / (
                    self._parameters.medium_to_outdoor_thermal_resistance
                    * self._parameters.medium_thermal_capacity
                )
            )

            constraints.append(room_temps[step + 1] - next_room)
            constraints_lower.append(0.0)
            constraints_upper.append(0.0)

            constraints.append(medium_temps[step + 1] - next_medium)
            constraints_lower.append(0.0)
            constraints_upper.append(0.0)

            constraints.append(
                room_temps[step]
                + slack_lower[step]
                - self._parameters.lower_temperature_bound
            )
            constraints_lower.append(0.0)
            constraints_upper.append(ca.inf)

            if step == 0:
                simulated_outdoor_temperature_delta = (
                    _simulated_outdoor(return_temp_setpoints[step])
                    - prev_simulated_outdoor
                )
            else:
                simulated_outdoor_temperature_delta = _simulated_outdoor(
                    return_temp_setpoints[step]
                ) - _simulated_outdoor(return_temp_setpoints[step - 1])

            constraints.append(simulated_outdoor_temperature_delta)
            constraints_lower.append(-self._parameters.outdoor_ramp_limit)
            constraints_upper.append(self._parameters.outdoor_ramp_limit)

        decision_vars = ca.vertcat(
            return_temp_setpoints, room_temps, medium_temps, slack_lower, slack_upper
        )

        decision_lower_bounds = (
            [self._parameters.minimum_medium_return_temperature] * horizon
            + [-ca.inf] * (horizon + 1)
            + [-ca.inf] * (horizon + 1)
            + [0.0] * horizon
            + [0.0] * horizon
        )
        decision_upper_bounds = (
            [self._parameters.maximum_medium_return_temperature] * horizon
            + [ca.inf] * (horizon + 1)
            + [ca.inf] * (horizon + 1)
            + [ca.inf] * horizon
            + [ca.inf] * horizon
        )

        nlp = {"x": decision_vars, "f": objective, "g": ca.vertcat(*constraints)}
        solver_opts = {
            "print_time": False,
            "ipopt": {
                "print_level": 0,
                "sb": "yes",
                "max_iter": 200,
                "acceptable_tol": 1e-6,
                "tol": 1e-6,
            },
        }
        solver = ca.nlpsol("solver", "ipopt", nlp, solver_opts)

        # Initial guess: keep temperatures near initial, setpoints near intercept
        room_guess = [initial_room_temp]
        medium_guess = [initial_medium_temp]
        for _ in range(horizon):
            room_guess.append(room_guess[-1])
            medium_guess.append(medium_guess[-1])

        return_guess = [self._parameters.heat_curve_intercept] * horizon
        slack_guess = [0.0] * horizon
        initial_guess = (
            return_guess + room_guess + medium_guess + slack_guess + slack_guess
        )

        solution = solver(
            x0=ca.DM(initial_guess),
            lbg=ca.DM(constraints_lower),
            ubg=ca.DM(constraints_upper),
            lbx=ca.DM(decision_lower_bounds),
            ubx=ca.DM(decision_upper_bounds),
        )

        solution_vector = np.array(solution["x"]).flatten()
        idx = 0
        return_setpoints = solution_vector[idx : idx + horizon]
        idx += horizon

        indoor_temperatures = solution_vector[idx : idx + horizon + 1]
        idx += horizon + 1

        medium_temperatures = solution_vector[idx : idx + horizon + 1]
        idx += horizon + 1

        # Compute heat inputs for logging and energy calculations
        heat_inputs = []
        for step in range(horizon):
            heat_inputs.append(
                min(
                    self._parameters.heater_thermal_power,
                    max(
                        0.0,
                        self._parameters.heater_transfer_coefficient
                        * (return_setpoints[step] - medium_temperatures[step]),
                    ),
                )
            )

        return (
            return_setpoints.astype(float),
            indoor_temperatures.astype(float),
            medium_temperatures.astype(float),
            np.array(heat_inputs, dtype=float),
        )

    async def async_regulate(self) -> float:
        """Run MPC to compute optimal simulated outdoor temperature."""

        _LOGGER.debug(
            "Running Model Predictive Control with parameters\n%s",
            self._parameters,
        )

        if self._parameters.heat_curve_slope == 0:
            raise RuntimeError("Heat curve slope cannot be zero")

        if self._state is None or not self._state.is_valid():
            raise RuntimeError("Invalid controller state for MPC regulation")

        if self._parameters.electricity_price_enabled:
            if (
                self._state.electricity_price is None
                or len(self._state.electricity_price) < 0
            ):
                raise RuntimeError(
                    "No electricity price data available for MPC regulation"
                )

        horizon = int(self._parameters.prediction_horizon)

        if (
            self._parameters.electricity_price_enabled
            and len(self._state.electricity_price) * ELECTRICITY_PRICE_TIME_STEP
            < horizon * self._parameters.time_step
        ):
            # If we have at least 8h (default) of data we will truncate the horizon and proceed anyway
            # This can happen shortly before 13:00 when nordpool publishes next day's prices
            if (
                len(self._state.electricity_price) * ELECTRICITY_PRICE_TIME_STEP
                >= 3600 * ELECTRICITY_PRICE_MINIMUM_HOURS_AVAILABLE
            ):
                horizon = np.floor(
                    len(self._state.electricity_price)
                    * ELECTRICITY_PRICE_TIME_STEP
                    / self._parameters.time_step
                )

                _LOGGER.warning(
                    "Electricity price data is not available for the full prediction horizon, "
                    "only %d points available which covers %.1f hours. "
                    "Proceeding anyway but truncating horizon from %d.",
                    len(self._state.electricity_price),
                    len(self._state.electricity_price)
                    * ELECTRICITY_PRICE_TIME_STEP
                    / 3600,
                    self._parameters.prediction_horizon,
                )

            else:
                raise RuntimeError(
                    "Insufficient electricity price data for MPC regulation. "
                    f"Only {len(self._state.electricity_price)} points available."
                )

        initial_room_temperature = self._state.indoor_temperature
        initial_medium_temperature = (
            self._parameters.heat_curve_slope * self._state.actual_outdoor_temperature
            + self._parameters.heat_curve_intercept
        )

        previous_simulated_outdoor_temperature = (
            self._state.simulated_outdoor_temperatures[0]["temperature"]
            if self._state.simulated_outdoor_temperatures is not None
            and len(self._state.simulated_outdoor_temperatures) > 0
            else self._state.actual_outdoor_temperature
            if self._state.actual_outdoor_temperature is not None
            else self._state.actual_outdoor_temperature
        )
        if previous_simulated_outdoor_temperature is None:
            raise RuntimeError("No reference outdoor temperature for ramp constraint")

        start_time = time.perf_counter()
        (
            return_setpoints,
            indoor_temperatures,
            medium_temperatures,
            thermal_power,
        ) = self._solve(
            initial_room_temperature,
            initial_medium_temperature,
            previous_simulated_outdoor_temperature,
            horizon,
        )

        now = time.time()

        self._state.projected_indoor_temperature = []
        self._state.projected_thermal_power = []
        self._state.projected_medium_temperature = []
        self._state.simulated_outdoor_temperatures = []
        self._state.outdoor_temperature_offsets = []

        for i in range(horizon):
            timestamp = now + i * self._parameters.time_step
            next_timestamp = now + (i + 1) * self._parameters.time_step

            data_dictionary = {
                "start_time": datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                ).isoformat(),
                "end_time": datetime.fromtimestamp(
                    next_timestamp, tz=timezone.utc
                ).isoformat(),
            }

            simulated_outdoor_temperature = (
                return_setpoints[i] - self._parameters.heat_curve_intercept
            ) / self._parameters.heat_curve_slope

            simulated_outdoor_temperature = max(
                self.MINIMUM_SIMULATED_TEMPERATURE,
                min(simulated_outdoor_temperature, self.MAXIMUM_SIMULATED_TEMPERATURE),
            )

            outdoor_temperature_offset = (
                simulated_outdoor_temperature - self._state.actual_outdoor_temperature
            )

            self._state.projected_indoor_temperature.append(
                {**data_dictionary, "temperature": float(indoor_temperatures[i])}
            )
            self._state.projected_thermal_power.append(
                {**data_dictionary, "temperature": int(thermal_power[i])}
            )
            self._state.projected_medium_temperature.append(
                {**data_dictionary, "temperature": float(medium_temperatures[i])}
            )
            self._state.simulated_outdoor_temperatures.append(
                {**data_dictionary, "temperature": float(simulated_outdoor_temperature)}
            )
            self._state.outdoor_temperature_offsets.append(
                {**data_dictionary, "temperature": outdoor_temperature_offset}
            )

        computation_time = time.perf_counter() - start_time
        self._state.computation_time = computation_time * 1000
