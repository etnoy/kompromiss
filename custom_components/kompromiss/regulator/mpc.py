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
    COMFORT_BAND_VIOLATION_PENALTY,
    DEFAULT_COMFORT_BAND_VIOLATION_PENALTY,
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
    ENERGY_COST_PENALTY,
    MINIMUM_INDOOR_TEMPERATURE,
    SIMULATED_OUTDOOR_MOVE_PENALTY,
    TARGET_TEMPERATURE,
    TEMPERATURE_DEVIATION_PENALTY,
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
    medium_to_room_resistance: float = DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE
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
        self._time_step: float = self._parameters.time_step
        super().__init__()

    def set_state(self, state: ControllerState) -> None:
        """Set the current state including outdoor and indoor temperatures.

        Args:
            state: ControllerState object with actual_outdoor_temperature and indoor_temperature
        """
        self._state = state

    def get_state(self) -> ControllerState:
        """Return the current controller state."""
        return self._state

    def set_weight_temperature_deviation(self, value: float) -> None:
        """Update the weight for temperature deviation from target.

        Args:
            value: New weight value for temperature deviation cost
        """
        self._parameters.temperature_deviation_penalty = value

        _LOGGER.debug("MPC weight for temperature deviation updated to %.2f", value)

    def set_weight_comfort_band_violation(self, value: float) -> None:
        """Update the weight for comfort band violations.

        Args:
            value: New weight value for comfort band violation cost
        """
        self._parameters.comfort_band_violation_penalty = value

        _LOGGER.debug("MPC weight for comfort band violation updated to %.2f", value)

    def update_parameters_from_options(self, options: dict) -> None:
        """Update all MPC parameters from config entry options.

        Args:
            options: Dictionary of options from config entry
        """

        if TARGET_TEMPERATURE in options:
            self._parameters.target_temperature = options[TARGET_TEMPERATURE]
        if MINIMUM_INDOOR_TEMPERATURE in options:
            self._parameters.lower_temperature_bound = options[
                MINIMUM_INDOOR_TEMPERATURE
            ]

        if "r_thermal" in options:
            self._parameters.thermal_resistance = options["r_thermal"]
        if "c_thermal" in options:
            self._parameters.thermal_capacitance = options["c_thermal"]
        if "r_medium_to_room" in options:
            self._parameters.medium_to_room_resistance = options["r_medium_to_room"]
        if "r_medium_to_environment" in options:
            self._parameters.medium_to_outdoor_thermal_resistance = options[
                "r_medium_to_environment"
            ]
        if "c_medium" in options:
            self._parameters.medium_thermal_capacity = options["c_medium"]

        if "heat_pump_thermal_power" in options:
            self._parameters.heater_thermal_power = options["heat_pump_thermal_power"]
        if "heat_pump_heat_transfer_coeff" in options:
            self._parameters.heater_transfer_coefficient = options[
                "heat_pump_heat_transfer_coeff"
            ]
        if "return_temperature_min" in options:
            self._parameters.minimum_medium_return_temperature = options[
                "return_temperature_min"
            ]
        if "return_temperature_max" in options:
            self._parameters.maximum_medium_return_temperature = options[
                "return_temperature_max"
            ]

        if "heat_curve_slope" in options:
            self._parameters.heat_curve_slope = options["heat_curve_slope"]
        if "heat_curve_intercept" in options:
            self._parameters.heat_curve_intercept = options["heat_curve_intercept"]

        if "time_step" in options:
            self._parameters.time_step = options["time_step"]
            self._time_step = options["time_step"]
        if "ramp_limit_outdoor" in options:
            self._parameters.outdoor_ramp_limit = options["ramp_limit_outdoor"]

        if TEMPERATURE_DEVIATION_PENALTY in options:
            self._parameters.temperature_deviation_penalty = options[
                TEMPERATURE_DEVIATION_PENALTY
            ]
        if COMFORT_BAND_VIOLATION_PENALTY in options:
            self._parameters.comfort_band_violation_penalty = options[
                COMFORT_BAND_VIOLATION_PENALTY
            ]
        if ENERGY_COST_PENALTY in options:
            self._parameters.energy_cost_penalty = options[ENERGY_COST_PENALTY]
        if SIMULATED_OUTDOOR_MOVE_PENALTY in options:
            self._parameters.simulated_outdoor_move_penalty = options[
                SIMULATED_OUTDOOR_MOVE_PENALTY
            ]

    def _heat_from_return_setpoint(
        self, return_temp: ca.SX, medium_temp: ca.SX
    ) -> ca.SX:
        """Convert a return temperature setpoint to heat flow into the medium.

        The heat pump tries to lift the medium temperature towards the
        setpoint. The delivered heat is capped by the maximum thermal power and
        cannot be negative.
        """

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

        time_step = self._time_step
        outdoor_temp = self._state.actual_outdoor_temperature
        slope = self._parameters.heat_curve_slope
        intercept = self._parameters.heat_curve_intercept
        ramp_limit = self._parameters.outdoor_ramp_limit
        move_weight = self._parameters.simulated_outdoor_move_penalty

        if slope == 0:
            raise RuntimeError("Heat curve slope cannot be zero")

        def _simulated_outdoor(u: ca.SX) -> ca.SX:
            return (u - intercept) / slope

        # Decision variables
        return_temp_setpoints = ca.SX.sym("u_return", horizon)
        room_temps = ca.SX.sym("x_room", horizon + 1)
        medium_temps = ca.SX.sym("x_medium", horizon + 1)
        slack_lower = ca.SX.sym("sL", horizon)
        slack_upper = ca.SX.sym("sH", horizon)

        # Objective
        objective = 0
        for step in range(horizon):
            # We only penalize temperature error when below the target, not above
            temperature_error = ca.fmin(
                0, room_temps[step] - self._parameters.target_temperature
            )
            heat_flow = self._heat_from_return_setpoint(
                return_temp_setpoints[step], medium_temps[step]
            )
            energy_cost = (
                heat_flow / 1000 * self._state.electricity_price[step].price / 4
            )

            if step == 0:
                delta_simulated = (
                    _simulated_outdoor(return_temp_setpoints[step])
                    - prev_simulated_outdoor
                )
            else:
                delta_simulated = _simulated_outdoor(
                    return_temp_setpoints[step]
                ) - _simulated_outdoor(return_temp_setpoints[step - 1])
            objective = (
                objective
                + self._parameters.temperature_deviation_penalty
                * (temperature_error**2)
                + self._parameters.comfort_band_violation_penalty
                * (slack_lower[step] ** 2 + slack_upper[step] ** 2)
                + self._parameters.energy_cost_penalty * energy_cost
                + move_weight * (delta_simulated**2)
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

            next_room = room_temps[step] + time_step * (
                (outdoor_temp - room_temps[step])
                / (
                    self._parameters.thermal_resistance
                    * self._parameters.thermal_capacitance
                )
                + (medium_temps[step] - room_temps[step])
                / (
                    self._parameters.medium_to_room_resistance
                    * self._parameters.thermal_capacitance
                )
            )

            next_medium = medium_temps[step] + time_step * (
                heat_flow / self._parameters.medium_thermal_capacity
                - (medium_temps[step] - room_temps[step])
                / (
                    self._parameters.medium_to_room_resistance
                    * self._parameters.medium_thermal_capacity
                )
                - (medium_temps[step] - outdoor_temp)
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
                delta_simulated = (
                    _simulated_outdoor(return_temp_setpoints[step])
                    - prev_simulated_outdoor
                )
            else:
                delta_simulated = _simulated_outdoor(
                    return_temp_setpoints[step]
                ) - _simulated_outdoor(return_temp_setpoints[step - 1])

            constraints.append(delta_simulated)
            constraints_lower.append(-ramp_limit)
            constraints_upper.append(ramp_limit)

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
        """Run MPC to compute optimal simulated outdoor temperature.

        The MPC algorithm:
        1. Predict future indoor and medium temperatures over horizon
        2. Optimize return temperature setpoints to minimize deviation and energy use
        3. Convert the first return setpoint to a simulated outdoor temperature using the heat curve
        4. Lower simulated temp → higher return setpoint → more heat
        """
        if self._parameters.heat_curve_slope == 0:
            raise RuntimeError("Heat curve slope cannot be zero")

        if self._state is None or not self._state.is_valid():
            raise RuntimeError("Invalid controller state for MPC regulation")

        if self._state.electricity_price is None:
            raise RuntimeError("No electricity price data available for MPC regulation")

        horizon = self._parameters.prediction_horizon

        if len(self._state.electricity_price) < horizon:
            horizon = len(self._state.electricity_price)

            # If we have at least 8h of data we will truncate the horizon and proceed anyway
            # This can happen shortly before 13:00 when nordpool publishes next day's prices
            if horizon * self._parameters.time_step >= 3600 * 8:
                _LOGGER.warning(
                    "Electricity price data is not available for the full prediction horizon, "
                    "only %d points available which covers %.1f hours. "
                    "Proceeding anyway but truncating horizon from %d.",
                    horizon,
                    horizon * self._parameters.time_step / 3600,
                    self._parameters.prediction_horizon,
                )
            else:
                raise RuntimeError(
                    f"Insufficient electricity price data for MPC regulation. Only {horizon} points available."
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
