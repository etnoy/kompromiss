"""Config flow for the Kompromiss integration."""

from __future__ import annotations

from typing import Any, Final
import logging

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigEntry,
    OptionsFlow,
    ConfigFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DEFAULT_HEAT_CURVE_INTERCEPT,
    DEFAULT_HEAT_CURVE_SLOPE,
    DEFAULT_HEATER_THERMAL_POWER,
    DEFAULT_HEATER_TRANSFER_COEFFICIENT,
    DEFAULT_HIGHEST_SIMULATED_TEMPERATURE,
    DEFAULT_LOWEST_SIMULATED_TEMPERATURE,
    DEFAULT_MEDIUM_THERMAL_CAPACITY,
    DEFAULT_MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
    DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
    DEFAULT_PREDICTION_HORIZON,
    DEFAULT_THERMAL_CAPACITANCE,
    DEFAULT_THERMAL_RESISTANCE,
    DEFAULT_TIME_STEP,
    DOMAIN,
    ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
    HEAT_CURVE_INTERCEPT,
    HEAT_CURVE_SLOPE,
    HEATER_THERMAL_POWER,
    HEATER_TRANSFER_COEFFICIENT,
    HIGHEST_SIMULATED_TEMPERATURE,
    INDOOR_TEMPERATURE_SENSOR,
    DEFAULT_COMFORT_BAND_VIOLATION_PENALTY,
    DEFAULT_ENERGY_COST_PENALTY,
    LOWEST_SIMULATED_TEMPERATURE,
    MEDIUM_THERMAL_CAPACITY,
    MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
    MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
    PREDICTION_HORIZON,
    TEMPERATURE_DEVIATION_PENALTY,
    DEFAULT_TEMPERATURE_DEVIATION_PENALTY,
    COMFORT_BAND_VIOLATION_PENALTY,
    ENERGY_COST_PENALTY,
    SIMULATED_OUTDOOR_MOVE_PENALTY,
    DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY,
    THERMAL_CAPACITANCE,
    THERMAL_RESISTANCE,
    TIME_STEP,
)

_LOGGER: Final = logging.getLogger(__name__)


class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kompromiss."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(title="Kompromiss", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(
                    ACTUAL_OUTDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
                vol.Required(
                    INDOOR_TEMPERATURE_SENSOR,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor"], device_class="temperature"
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry):
        """Get the options flow for this handler."""
        return KompromissOptionsFlowHandler()

    def is_matching(self, other_flow) -> bool:
        return True


class KompromissOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Kompromiss integration."""

    def __init__(self) -> None:
        """Initialize options flow."""
        self._conf_app_id: str | None = None

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options - main menu."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["mpc", "heater", "output", "thermal"],
        )

    async def async_step_mpc(self, user_input: dict[str, Any] | None = None):
        """Handle MPC tuning parameters."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    PREDICTION_HORIZON,
                    default=self.config_entry.options.get(
                        PREDICTION_HORIZON,
                        DEFAULT_PREDICTION_HORIZON,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    TIME_STEP,
                    default=self.config_entry.options.get(
                        TIME_STEP,
                        DEFAULT_TIME_STEP,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=7200,
                        step=10,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    TEMPERATURE_DEVIATION_PENALTY,
                    default=self.config_entry.options.get(
                        TEMPERATURE_DEVIATION_PENALTY,
                        DEFAULT_TEMPERATURE_DEVIATION_PENALTY,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000000.0,
                        step=100.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    COMFORT_BAND_VIOLATION_PENALTY,
                    default=self.config_entry.options.get(
                        COMFORT_BAND_VIOLATION_PENALTY,
                        DEFAULT_COMFORT_BAND_VIOLATION_PENALTY,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000000.0,
                        step=100.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    ENERGY_COST_PENALTY,
                    default=self.config_entry.options.get(
                        ENERGY_COST_PENALTY, DEFAULT_ENERGY_COST_PENALTY
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=1.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    SIMULATED_OUTDOOR_MOVE_PENALTY,
                    default=self.config_entry.options.get(
                        SIMULATED_OUTDOOR_MOVE_PENALTY,
                        DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=1000.0,
                        step=5.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="mpc",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
            description_placeholders={"description": "MPC control parameters."},
        )

    async def async_step_heater(self, user_input: dict[str, Any] | None = None):
        """Handle heater parameters."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    HEATER_THERMAL_POWER,
                    default=self.config_entry.options.get(
                        HEATER_THERMAL_POWER,
                        DEFAULT_HEATER_THERMAL_POWER,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0,
                        max=100000.0,
                        step=100.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    HEAT_CURVE_SLOPE,
                    default=self.config_entry.options.get(
                        HEAT_CURVE_SLOPE,
                        DEFAULT_HEAT_CURVE_SLOPE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-1,
                        max=-0.1,
                        step=0.05,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    HEAT_CURVE_INTERCEPT,
                    default=self.config_entry.options.get(
                        HEAT_CURVE_INTERCEPT,
                        DEFAULT_HEAT_CURVE_INTERCEPT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=100,
                        step=0.5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    HEATER_TRANSFER_COEFFICIENT,
                    default=self.config_entry.options.get(
                        HEATER_TRANSFER_COEFFICIENT,
                        DEFAULT_HEATER_TRANSFER_COEFFICIENT,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=100.0,
                        max=5000.0,
                        step=10.0,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="heater",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
            description_placeholders={"description": "Heater parameters."},
        )

    async def async_step_output(self, user_input: dict[str, Any] | None = None):
        """Handle output parameters."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    LOWEST_SIMULATED_TEMPERATURE,
                    default=self.config_entry.options.get(
                        LOWEST_SIMULATED_TEMPERATURE,
                        DEFAULT_LOWEST_SIMULATED_TEMPERATURE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-50,
                        max=10,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    HIGHEST_SIMULATED_TEMPERATURE,
                    default=self.config_entry.options.get(
                        HIGHEST_SIMULATED_TEMPERATURE,
                        DEFAULT_HIGHEST_SIMULATED_TEMPERATURE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=50,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    SIMULATED_OUTDOOR_MOVE_PENALTY,
                    default=self.config_entry.options.get(
                        SIMULATED_OUTDOOR_MOVE_PENALTY,
                        DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=10,
                        max=200,
                        step=1,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="output",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
            description_placeholders={
                "description": "Simulated Outdoor Temperature Options."
            },
        )

    async def async_step_thermal(self, user_input: dict[str, Any] | None = None):
        """Handle thermal model parameters."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    THERMAL_RESISTANCE,
                    default=self.config_entry.options.get(
                        THERMAL_RESISTANCE,
                        DEFAULT_THERMAL_RESISTANCE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.001,
                        max=0.1,
                        step=0.001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    THERMAL_CAPACITANCE,
                    default=self.config_entry.options.get(
                        THERMAL_CAPACITANCE,
                        DEFAULT_THERMAL_CAPACITANCE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1e6,
                        max=5e7,
                        step=1e5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
                    default=self.config_entry.options.get(
                        MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
                        DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.001,
                        max=0.1,
                        step=0.001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
                    default=self.config_entry.options.get(
                        MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
                        DEFAULT_MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.001,
                        max=10.0,
                        step=0.001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional(
                    MEDIUM_THERMAL_CAPACITY,
                    default=self.config_entry.options.get(
                        MEDIUM_THERMAL_CAPACITY,
                        DEFAULT_MEDIUM_THERMAL_CAPACITY,
                    ),
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1e5,
                        max=5e7,
                        step=1e5,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="thermal",
            data_schema=self.add_suggested_values_to_schema(
                schema, self.config_entry.options
            ),
            description_placeholders={"description": "Thermal model parameters."},
        )
