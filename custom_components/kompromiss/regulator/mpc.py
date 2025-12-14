"""Model Predictive Control regulator for temperature control using 1R1C thermal model."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from . import Regulator

if TYPE_CHECKING:
    from ..controller import ControllerState


class MPCParameters:
    """Holds parameters for the MPC regulator."""

    R_THERMAL: float = 0.01  # Thermal resistance [K/W]
    C_THERMAL: float = 3.6e6  # Thermal capacitance [J/K]

    HEAT_PUMP_THERMAL_POWER: float = 5000.0  # Maximum heat output [W]

    TARGET_TEMP_MIN: float = 19.5  # Minimum desired indoor temperature [°C]
    TARGET_TEMP_MAX: float = 22.5  # Maximum desired indoor temperature [°C]

    PREDICTION_HORIZON: int = 8  # Number of steps to predict ahead
    TIME_STEP: float = 900.0  # Time step in seconds (15 minutes)

    # MPC cost weights
    WEIGHT_TEMPERATURE_DEVIATION: float = 100.0  # Cost for being far from target
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
        self._state: ControllerState | None = None
        self._parameters = MPCParameters()
        self._tau = self._parameters.R_THERMAL * self._parameters.C_THERMAL
        # Discrete time system model: x[k+1] = A*x[k] + B*u[k] + C*d[k]
        # where x = indoor temp, u = heat input, d = outdoor temp disturbance
        self._system_matrix_a = math.exp(-self._parameters.TIME_STEP / self._tau)
        self._system_matrix_b = (
            1.0 - self._system_matrix_a
        ) * self._parameters.R_THERMAL
        super().__init__()

    async def set_state(self, state: "ControllerState") -> None:
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
        initial_temp: float,
        outdoor_temp: float,
        heat_input: float,
        steps: int,
    ) -> float:
        """Predict future indoor temperature using 1R1C model.

        Args:
            initial_temp: Current indoor temperature
            outdoor_temp: Outdoor temperature (assumed constant)
            heat_input: Heat power input [W]
            steps: Number of time steps to predict

        Returns:
            Predicted indoor temperature after 'steps' time steps
        """
        temp = initial_temp
        for _ in range(steps):
            # Discrete-time thermal model
            # T_indoor[k+1] = A * T_indoor[k] + B * Q_heat + (1-A) * T_outdoor
            temp = (
                self._system_matrix_a * temp
                + self._system_matrix_b * heat_input
                + (1.0 - self._system_matrix_a) * outdoor_temp
            )
        return temp

    def _calculate_cost(
        self,
        predicted_temp: float,
        target_temp_min: float,
        target_temp_max: float,
        heat_input: float,
    ) -> float:
        """Calculate cost for a given prediction.

        Args:
            predicted_temp: Predicted indoor temperature
            target_temp_min: Minimum target temperature
            target_temp_max: Maximum target temperature
            heat_input: Heat power input [W]

        Returns:
            Total cost (lower is better)
        """
        # Temperature deviation cost
        if predicted_temp < target_temp_min:
            temp_deviation = target_temp_min - predicted_temp
        elif predicted_temp > target_temp_max:
            temp_deviation = predicted_temp - target_temp_max
        else:
            temp_deviation = 0.0

        temp_cost = self._parameters.WEIGHT_TEMPERATURE_DEVIATION * temp_deviation**2

        # Heat input cost (penalize high energy use)
        heat_cost = (
            self._parameters.WEIGHT_HEAT_INPUT
            * (heat_input / self._parameters.HEAT_PUMP_THERMAL_POWER) ** 2
        )

        return temp_cost + heat_cost

    def _calculate_total_cost_horizon(
        self,
        initial_temp: float,
        outdoor_temp: float,
        heat_inputs: list[float],
    ) -> float:
        """Calculate total cost over prediction horizon.

        Args:
            initial_temp: Current indoor temperature
            outdoor_temp: Outdoor temperature
            heat_inputs: List of heat inputs for each step in horizon

        Returns:
            Total accumulated cost
        """
        temp = initial_temp
        total_cost = 0.0

        for heat_input in heat_inputs:
            # Predict next step
            temp = (
                self._system_matrix_a * temp
                + self._system_matrix_b * heat_input
                + (1.0 - self._system_matrix_a) * outdoor_temp
            )
            # Add cost for this step
            cost = self._calculate_cost(
                temp,
                self._parameters.TARGET_TEMP_MIN,
                self._parameters.TARGET_TEMP_MAX,
                heat_input,
            )
            total_cost += cost

        return total_cost

    def _optimize_heat_input(
        self,
        initial_temp: float,
        outdoor_temp: float,
    ) -> list[float]:
        """Find optimal heat input sequence over prediction horizon using gradient descent.

        Args:
            initial_temp: Current indoor temperature
            outdoor_temp: Outdoor temperature

        Returns:
            List of optimal heat inputs for each step in horizon
        """
        # Initialize with simple proportional control
        target_temp = (
            self._parameters.TARGET_TEMP_MIN + self._parameters.TARGET_TEMP_MAX
        ) / 2.0
        heat_inputs = [
            max(
                0,
                min(
                    self._parameters.HEAT_PUMP_THERMAL_POWER,
                    (initial_temp - target_temp) * 1000.0,
                ),
            )
            for _ in range(self._parameters.PREDICTION_HORIZON)
        ]

        # Gradient descent optimization
        learning_rate = 10.0
        max_iterations = 20

        for iteration in range(max_iterations):
            current_cost = self._calculate_total_cost_horizon(
                initial_temp, outdoor_temp, heat_inputs
            )

            # Calculate gradient numerically
            delta = 1.0
            improved = False

            for i, current_heat in enumerate(heat_inputs):
                # Try increasing heat at step i
                heat_inputs_plus = heat_inputs.copy()
                heat_inputs_plus[i] = min(
                    self._parameters.HEAT_PUMP_THERMAL_POWER,
                    heat_inputs_plus[i] + delta,
                )
                cost_plus = self._calculate_total_cost_horizon(
                    initial_temp, outdoor_temp, heat_inputs_plus
                )

                # Try decreasing heat at step i
                heat_inputs_minus = heat_inputs.copy()
                heat_inputs_minus[i] = max(0, heat_inputs_minus[i] - delta)
                cost_minus = self._calculate_total_cost_horizon(
                    initial_temp, outdoor_temp, heat_inputs_minus
                )

                # Update in direction of steepest descent
                if cost_plus < current_cost:
                    heat_inputs[i] = heat_inputs_plus[i]
                    improved = True
                elif cost_minus < current_cost:
                    heat_inputs[i] = heat_inputs_minus[i]
                    improved = True

            if not improved:
                learning_rate *= 0.9

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
            self._state.actual_outdoor_temperature,
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

        # Ensure simulated temp stays within bounds
        self._state.simulated_temperature = max(
            self.MINIMUM_SIMULATED_TEMPERATURE,
            min(self.MAXIMUM_SIMULATED_TEMPERATURE, self._state.simulated_temperature),
        )

        return self._state.simulated_temperature
