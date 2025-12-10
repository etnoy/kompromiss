"""
Constants for the Kompromiss integration.
"""

DOMAIN = "kompromiss"
PLATFORMS: list[str] = ["sensor"]

CONF_TEMPERATURE_SENSOR = "temperature_sensor"
CONF_ELECTRICITY_PRICE_SENSOR = "electricity_price_sensor"

CONF_MINIMUM_INDOOR_TEMPERATURE = "minimum_indoor_temperature"
CONF_MAXIMUM_INDOOR_TEMPERATURE = "maximum_indoor_temperature"
CONF_LOWEST_SIMULATED_TEMPERATURE = "lowest_simulated_temperature"
CONF_HIGHEST_SIMULATED_TEMPERATURE = "highest_simulated_temperature"
CONF_STEP_MINUTES = "step_minutes"
CONF_HORIZON_STEPS = "horizon_steps"
CONF_ENABLED = "enabled"

DEFAULT_T_MIN = 19.5
DEFAULT_T_MAX = 22.5
DEFAULT_LOWEST_SIMULATED_TEMPERATURE = -40.0
# 20 degrees is often where summer mode kicks in, so let's put 19 as the max
DEFAULT_HIGHEST_SIMULATED_TEMPERATURE = 19.0
# Electricity price usually updates every 15 minutes, so align with that
DEFAULT_STEP_MINUTES = 15
DEFAULT_HORIZON_STEPS = 8
DEFAULT_ENABLED = True

DATA_COORDINATOR = "coordinator"

ATTR_COMPUTED_SOT = "computed_sot"
ATTR_VIRTUAL_TEMP = "virtual_temp"
ATTR_COLDEST = "coldest"
ATTR_HOTTEST = "hottest"
ATTR_PRICE_NOW = "price_now"
