"""Model Predictive Control regulator for temperature control using 1R1C thermal model."""

from __future__ import annotations

import logging
import math
from typing import Final

import numpy as np

from . import Regulator
from ..state import ControllerState


_LOGGER: Final = logging.getLogger(__name__)


class MPCParameters:
    """Holds parameters for the MPC regulator."""

    R_THERMAL: float = 0.01  # Thermal resistance [K/W]
    C_THERMAL: float = 3.6e6  # Thermal capacitance [J/K]

    HEAT_PUMP_THERMAL_POWER: float = 5000.0  # Maximum heat output [W]

    TARGET_TEMP_MIN: float = 19.5  # Minimum desired indoor temperature [°C]
    TARGET_TEMP_MAX: float = 22.5  # Maximum desired indoor temperature [°C]

    PREDICTION_HORIZON: int = 12 * 4  # Number of steps to predict ahead
    TIME_STEP: float = 900.0  # Time step in seconds (15 minutes)

    # MPC cost weights
    WEIGHT_TEMPERATURE_DEVIATION: float = (
        1000.0  # Cost for being far from temperature target
    )
    WEIGHT_HEAT_INPUT: float = 0.1  # Cost for using energy


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

    def _predict_indoor_temperature(
        self,
        heat_input: float | np.ndarray,
    ) -> np.ndarray:
        """Predict future indoor temperature using 1R1C model.

        Args:
            heat_input: Heat power input [W] - scalar or array of length horizon
            steps: Number of time steps to predict (if heat_input is scalar)

        Returns:
            Array of predicted indoor temperatures at each time step [k=0, k=1, ..., k=steps]
        """
        if isinstance(heat_input, (int, float)):
            # Scalar heat input - repeat for all steps
            heat_inputs = np.full(self._parameters.PREDICTION_HORIZON, heat_input)
        else:
            # Array heat input
            heat_inputs = np.asarray(heat_input)
            if len(heat_inputs) < self._parameters.PREDICTION_HORIZON:
                # Pad with last value if shorter than horizon
                heat_inputs = np.pad(
                    heat_inputs,
                    (0, self._parameters.PREDICTION_HORIZON - len(heat_inputs)),
                    "edge",
                )

        # Initialize temperature trajectory, initial value is current indoor temp
        temperature_trajectory = np.zeros(self._parameters.PREDICTION_HORIZON + 1)
        temperature_trajectory[0] = self._state.indoor_temperature

        # Predict forward in time
        for k in range(self._parameters.PREDICTION_HORIZON):
            temperature_trajectory[k + 1] = (
                self._system_matrix_a * temperature_trajectory[k]
                + self._system_matrix_b * heat_inputs[k]
                + (1.0 - self._system_matrix_a) * self._state.actual_outdoor_temperature
            )

        _LOGGER.debug(
            "Computed temperature trajectory: %s for heat input %s",
            temperature_trajectory,
            heat_inputs,
        )

        return temperature_trajectory

    def _calculate_total_cost_horizon(
        self,
        heat_inputs: np.ndarray,
    ) -> float:
        """Calculate total cost over prediction horizon.

        Args:
            initial_temp: Current indoor temperature
            outdoor_temp: Outdoor temperature
            heat_inputs: Array of heat inputs for each step in horizon

        Returns:
            Total accumulated cost
        """
        temperature_trajectory = self._predict_indoor_temperature(heat_inputs)

        total_cost = 0.0

        for k in range(0, self._parameters.PREDICTION_HORIZON):
            temperature = temperature_trajectory[k]

            deviation = 0.0

            # Cost for deviation from target temperature range
            if temperature < self._parameters.TARGET_TEMP_MIN:
                deviation = self._parameters.TARGET_TEMP_MIN - temperature
            elif temperature > self._parameters.TARGET_TEMP_MAX:
                deviation = temperature - self._parameters.TARGET_TEMP_MAX

            cost_deviation = self._parameters.WEIGHT_TEMPERATURE_DEVIATION * (
                deviation**2
            )

            # Cost for heat input (energy usage)
            heat_input = heat_inputs[k]
            cost_heat = self._parameters.WEIGHT_HEAT_INPUT * (heat_input)

            total_cost += cost_deviation + cost_heat

        _LOGGER.debug(
            "Calculated total cost %.2f for heat inputs %s", total_cost, heat_inputs
        )

        return total_cost

    def _optimize_heat_input(
        self,
        initial_temp: float,
    ) -> np.ndarray:
        """Find optimal heat input sequence over prediction horizon using gradient descent.

        Args:
            initial_temp: Current indoor temperature

        Returns:
            Array of optimal heat inputs for each step in horizon
        """

        _LOGGER.debug(
            "Starting heat input optimization from initial temp %.2f°C", initial_temp
        )

        # Initialize with simple proportional control
        target_temp = (
            self._parameters.TARGET_TEMP_MIN + self._parameters.TARGET_TEMP_MAX
        ) / 2.0
        heat_inputs = np.full(
            self._parameters.PREDICTION_HORIZON,
            max(
                0,
                min(
                    self._parameters.HEAT_PUMP_THERMAL_POWER,
                    (initial_temp - target_temp) * 1000.0,
                ),
            ),
        )

        total_cost = self._calculate_total_cost_horizon(heat_inputs)

        # Gradient descent optimization with adaptive step length
        step_size = 500.0
        min_step_size = 50.0
        growth_factor = 1.2
        shrink_factor = 0.5
        max_iterations = 40

        for iteration in range(max_iterations):
            current_total_cost = total_cost

            _LOGGER.debug(
                "Optimization iteration %d: cost %.2f, step_size %.1f, heat inputs %s",
                iteration,
                current_total_cost,
                step_size,
                heat_inputs,
            )

            improved = False

            for i, _ in enumerate(heat_inputs):
                # Try increasing heat at step i
                heat_inputs_plus = heat_inputs.copy()
                heat_inputs_plus[i] = min(
                    self._parameters.HEAT_PUMP_THERMAL_POWER,
                    heat_inputs_plus[i] + step_size,
                )
                cost_plus = self._calculate_total_cost_horizon(heat_inputs_plus)

                # Try decreasing heat at step i
                heat_inputs_minus = heat_inputs.copy()
                heat_inputs_minus[i] = max(0, heat_inputs_minus[i] - step_size)
                cost_minus = self._calculate_total_cost_horizon(heat_inputs_minus)

                # Update in direction of steepest descent using current step size
                if cost_plus < current_total_cost and cost_plus <= cost_minus:
                    heat_inputs[i] = heat_inputs_plus[i]
                    current_total_cost = cost_plus
                    improved = True
                elif cost_minus < current_total_cost:
                    heat_inputs[i] = heat_inputs_minus[i]
                    current_total_cost = cost_minus
                    improved = True

                _LOGGER.debug(
                    "Gradient step %d: cost_plus %.2f, cost_minus %.2f, baseline_cost %.2f, step_size %.1f, improved: %s",
                    i,
                    cost_plus,
                    cost_minus,
                    total_cost,
                    step_size,
                    improved,
                )

            if improved:
                total_cost = current_total_cost
                step_size = min(
                    step_size * growth_factor, self._parameters.HEAT_PUMP_THERMAL_POWER
                )
            else:
                step_size = max(step_size * shrink_factor, min_step_size)
                if step_size <= min_step_size:
                    break

        _LOGGER.debug(
            "Optimization completed: optimal heat inputs %s give total cost %.2f",
            heat_inputs,
            total_cost,
        )

        return heat_inputs

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

        # Optimize heat input over prediction horizon
        optimal_heat_inputs = self._optimize_heat_input(
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

        _LOGGER.debug(
            "MPC regulation computed simulated outdoor temperature: %.2f°C. "
            "Predicted indoor temp trajectory: %s, heat inputs: %s",
            self._state.simulated_temperature,
            self._predict_indoor_temperature(optimal_heat_inputs),
            optimal_heat_inputs,
        )

        return self._state.simulated_temperature
