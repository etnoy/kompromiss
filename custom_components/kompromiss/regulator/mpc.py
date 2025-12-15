"""Model Predictive Control regulator for temperature control using 1R1C thermal model.

Refactored to use CasADi with the IPOPT solver for the MPC optimization problem.
"""

from __future__ import annotations

import logging
import math
import time
from typing import Final

import numpy as np
import casadi as ca

from . import Regulator
from ..state import ControllerState


_LOGGER: Final = logging.getLogger(__name__)


class MPCParameters:
    """Holds parameters for the MPC regulator."""

    R_THERMAL: float = 0.01  # Thermal resistance [K/W]
    C_THERMAL: float = 3.6e6  # Thermal capacitance [J/K]

    HEAT_PUMP_THERMAL_POWER: float = 5000.0  # Maximum heat output [W]

    TARGET_TEMPERATURE: float = 21.0  # Desired indoor temperature [°C]
    TARGET_TEMPERATURE_FLOOR: float = 19.5  # Minimum comfort bound [°C]
    TARGET_TEMPERATURE_CEILING: float = 22.5  # Maximum comfort bound [°C]

    PREDICTION_HORIZON: int = 12 * 4  # Number of steps to predict ahead
    TIME_STEP: float = 900.0  # Time step in seconds (15 minutes)

    # MPC cost weights
    WEIGHT_TEMPERATURE_DEVIATION: float = (
        1000.0  # Cost for being far from temperature target
    )
    WEIGHT_COMFORT_BAND_VIOLATION: float = (
        10000.0  # Cost for violating comfort band (floor/ceiling)
    )
    WEIGHT_HEAT_INPUT: float = 25  # Cost for using energy


class MPCRegulator(Regulator):
    """Full MPC regulator using a 1R1C thermal model.

    The 1R1C model represents a building as:
    - R (thermal resistance): resistance to heat flow between indoor and outdoor
    - C (thermal capacitance): ability to store thermal energy

    The model: dT_indoor/dt = (T_outdoor - T_indoor)/(R*C) + Q_heat/C

    Where:
    - T_indoor: indoor temperature
    - T_outdoor: outdoor temperature
    - Q_heat: heat power added by heat pump (function of simulated outdoor temp)
    - Lower simulated temp → more heat output from heat pump

    MPC solves: minimize sum over horizon of (cost of deviation + cost of control)
    subject to: thermal model constraints and heat pump limits
    """

    def __init__(self) -> None:
        self._state: ControllerState = ControllerState()
        self._parameters: MPCParameters = MPCParameters()
        self._tau = self._parameters.R_THERMAL * self._parameters.C_THERMAL
        # Discrete time system model: x[k+1] = A*x[k] + B*u[k] + C*d[k]
        # where x = indoor temp, u = heat input, d = outdoor temp disturbance
        self._system_matrix_a = math.exp(-self._parameters.TIME_STEP / self._tau)
        self._system_matrix_b = (
            1.0 - self._system_matrix_a
        ) * self._parameters.R_THERMAL
        super().__init__()

    async def set_state(self, state: ControllerState) -> None:
        """Set the current state including outdoor and indoor temperatures.

        Args:
            state: ControllerState object with actual_outdoor_temperature and indoor_temperature
        """
        self._state = state

    async def get_output(self) -> float | None:
        """Return the computed simulated outdoor temperature."""
        if self._state is None:
            return None
        return self._state.simulated_temperature

    def set_weight_temperature_deviation(self, value: float) -> None:
        """Update the weight for temperature deviation from target.

        Args:
            value: New weight value for temperature deviation cost
        """
        self._parameters.WEIGHT_TEMPERATURE_DEVIATION = value

        _LOGGER.debug("MPC weight for temperature deviation updated to %.2f", value)

    def set_weight_comfort_band_violation(self, value: float) -> None:
        """Update the weight for comfort band violations.

        Args:
            value: New weight value for comfort band violation cost
        """
        self._parameters.WEIGHT_COMFORT_BAND_VIOLATION = value

        _LOGGER.debug("MPC weight for comfort band violation updated to %.2f", value)

    def _optimize_heat_input(
        self,
        initial_temp: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Solve MPC using CasADi IPOPT.

        Args:
            initial_temp: Current indoor temperature

        Returns:
            Tuple of (optimal heat inputs, optimal temperature trajectory)
        """

        # Decision variables
        heat_input_variable = ca.SX.sym("u", self._parameters.PREDICTION_HORIZON)
        temperature_state = ca.SX.sym("x", self._parameters.PREDICTION_HORIZON + 1)
        slack_lower = ca.SX.sym("sL", self._parameters.PREDICTION_HORIZON)
        slack_upper = ca.SX.sym("sH", self._parameters.PREDICTION_HORIZON)

        # Objective
        objective = 0
        for step in range(self._parameters.PREDICTION_HORIZON):
            # Penalize deviation from target temperature
            temperature_error = (
                temperature_state[step] - self._parameters.TARGET_TEMPERATURE
            )
            energy_cost = (
                heat_input_variable[step]
                / 1000
                * self._state.electricity_prices[step].price
                / 4
            )
            objective = (
                objective
                + self._parameters.WEIGHT_TEMPERATURE_DEVIATION * (temperature_error**2)
                + self._parameters.WEIGHT_COMFORT_BAND_VIOLATION
                * (slack_lower[step] ** 2 + slack_upper[step] ** 2)
                + self._parameters.WEIGHT_HEAT_INPUT * energy_cost
            )

        # Constraints
        constraints = []
        constraints_lower = []
        constraints_upper = []

        # Initial condition
        constraints.append(temperature_state[0] - initial_temp)
        constraints_lower.append(0.0)
        constraints_upper.append(0.0)

        # Dynamics and slack constraints
        for step in range(self._parameters.PREDICTION_HORIZON):
            constraints.append(
                temperature_state[step + 1]
                - (
                    self._system_matrix_a * temperature_state[step]
                    + self._system_matrix_b * heat_input_variable[step]
                    + (1.0 - self._system_matrix_a)
                    * self._state.actual_outdoor_temperature
                )
            )
            constraints_lower.append(0.0)
            constraints_upper.append(0.0)

            constraints.append(
                temperature_state[step]
                + slack_lower[step]
                - self._parameters.TARGET_TEMPERATURE_FLOOR
            )
            constraints_lower.append(0.0)
            constraints_upper.append(ca.inf)

            constraints.append(
                -temperature_state[step]
                + slack_upper[step]
                + self._parameters.TARGET_TEMPERATURE_CEILING
            )
            constraints_lower.append(0.0)
            constraints_upper.append(ca.inf)

        # Variable vector
        decision_vars = ca.vertcat(
            heat_input_variable, temperature_state, slack_lower, slack_upper
        )

        # Bounds
        decision_lower_bounds = (
            [0.0] * self._parameters.PREDICTION_HORIZON
            + [-ca.inf] * (self._parameters.PREDICTION_HORIZON + 1)
            + [0.0] * self._parameters.PREDICTION_HORIZON
            + [0.0] * self._parameters.PREDICTION_HORIZON
        )
        decision_upper_bounds = (
            [self._parameters.HEAT_PUMP_THERMAL_POWER]
            * self._parameters.PREDICTION_HORIZON
            + [ca.inf] * (self._parameters.PREDICTION_HORIZON + 1)
            + [ca.inf] * self._parameters.PREDICTION_HORIZON
            + [ca.inf] * self._parameters.PREDICTION_HORIZON
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

        # Initial guess
        temperature_initial_guess = [initial_temp]
        for _ in range(self._parameters.PREDICTION_HORIZON):
            temperature_initial_guess.append(
                float(
                    self._system_matrix_a * temperature_initial_guess[-1]
                    + (1.0 - self._system_matrix_a)
                    * self._state.actual_outdoor_temperature
                )
            )
        heat_initial_guess = [0.0] * self._parameters.PREDICTION_HORIZON
        slack_initial_guess = [0.0] * self._parameters.PREDICTION_HORIZON
        initial_guess = (
            heat_initial_guess
            + temperature_initial_guess
            + slack_initial_guess
            + slack_initial_guess
        )

        solution = solver(
            x0=ca.DM(initial_guess),
            lbg=ca.DM(constraints_lower),
            ubg=ca.DM(constraints_upper),
            lbx=ca.DM(decision_lower_bounds),
            ubx=ca.DM(decision_upper_bounds),
        )

        solution_vector = np.array(solution["x"]).flatten()
        optimal_heat_inputs = solution_vector[: self._parameters.PREDICTION_HORIZON]

        # Extract temperature trajectory
        temp_start = self._parameters.PREDICTION_HORIZON
        temp_end = temp_start + self._parameters.PREDICTION_HORIZON + 1
        optimal_temperatures = solution_vector[temp_start:temp_end]

        return optimal_heat_inputs.astype(float), optimal_temperatures.astype(float)

    async def async_regulate(self) -> float:
        """Run MPC to compute optimal simulated outdoor temperature.

        The MPC algorithm:
        1. Predict future indoor temperature over horizon using thermal model
        2. Optimize heat input sequence to minimize deviation from target and energy use
        3. Convert optimal first heat input to simulated outdoor temperature
        4. Lower simulated temp = more heat from heat pump
        """
        if self._state is None or not self._state.is_valid():
            if self._state and self._state.actual_outdoor_temperature is not None:
                self._state.simulated_temperature = (
                    self._state.actual_outdoor_temperature
                )
            return self._state.simulated_temperature if self._state else None

        if self._state.electricity_prices is None:
            raise RuntimeError("No electricity price data available for MPC regulation")

        if len(self._state.electricity_prices) < self._parameters.PREDICTION_HORIZON:
            available = len(self._state.electricity_prices)
            required = self._parameters.PREDICTION_HORIZON
            raise RuntimeError(
                f"Insufficient electricity price data for MPC regulation. \n"
                f"Only {available} points available, but {required} required."
            )

        _LOGGER.debug("Electricity prices for MPC: %s", self._state.electricity_prices)
        for electricity_price in self._state.electricity_prices:
            _LOGGER.debug("Electricity price: %s", electricity_price)

        # Optimize heat input over prediction horizon
        start_time = time.perf_counter()
        optimal_heat_inputs, optimal_temperatures = self._optimize_heat_input(
            self._state.indoor_temperature,
        )

        # Use the first optimal heat input
        optimal_heat = optimal_heat_inputs[0]

        # Convert required heat to simulated outdoor temperature
        # Lower simulated temp → heat pump works harder → more heat
        # Normalized heat: 0 to 1
        normalized_heat = optimal_heat / self._parameters.HEAT_PUMP_THERMAL_POWER

        # Temperature offset: 0 to -10°C based on heat demand
        temp_offset = -10.0 * normalized_heat

        self._state.simulated_temperature = (
            self._state.actual_outdoor_temperature + temp_offset
        )

        if (
            self._state.simulated_outdoor_temperature
            < self.MINIMUM_SIMULATED_TEMPERATURE
        ):
            _LOGGER.warning(
                "Simulated outdoor temperature %.2f°C is below minimum %.2f°C",
                self._state.simulated_outdoor_temperature,
                self.MINIMUM_SIMULATED_TEMPERATURE,
            )
        if (
            self._state.simulated_outdoor_temperature
            > self.MAXIMUM_SIMULATED_TEMPERATURE
        ):
            _LOGGER.warning(
                "Simulated outdoor temperature %.2f°C is above maximum %.2f°C",
                self._state.simulated_outdoor_temperature,
                self.MAXIMUM_SIMULATED_TEMPERATURE,
            )

        # Ensure simulated temp stays within bounds
        self._state.simulated_temperature = max(
            self.MINIMUM_SIMULATED_TEMPERATURE,
            min(self.MAXIMUM_SIMULATED_TEMPERATURE, self._state.simulated_temperature),
        )
        computation_time = time.perf_counter() - start_time

        _LOGGER.debug(
            "MPC regulation computed simulated outdoor temperature: %.2f°C in %.0fms.\n"
            "Weights: temp_dev=%.0f, comfort_viol=%.0f, heat=%.2f\n"
            "Optimal temperature trajectory: %s\n"
            "Heat inputs: %s",
            self._state.simulated_temperature,
            computation_time * 1000,
            self._parameters.WEIGHT_TEMPERATURE_DEVIATION,
            self._parameters.WEIGHT_COMFORT_BAND_VIOLATION,
            self._parameters.WEIGHT_HEAT_INPUT,
            np.round(optimal_temperatures, 1),
            np.round(optimal_heat_inputs, 0),
        )

        return self._state.simulated_temperature
