"""
Constants for the Kompromiss integration.
"""

DOMAIN = "kompromiss"

DATA_COORDINATOR = "coordinator"

# Simulated Outdoor Temperature
CONF_SOT_NUMBER = "sot_number"
CONF_TEMPERATURE_SENSORS = "temperature_sensors"
CONF_PRICE_SENSOR = "price_sensor"

CONF_MINIMUM_INDOOR_TEMPERATURE = "t_min"
CONF_MAXIMUM_INDOOR_TEMPERATURE = "t_max"
CONF_SOT_MIN = "sot_min"
CONF_SOT_MAX = "sot_max"
CONF_STEP_MINUTES = "step_minutes"
CONF_HORIZON_STEPS = "horizon_steps"
CONF_ENABLED = "enabled"

DEFAULT_T_MIN = 19.5
DEFAULT_T_MAX = 22.5
DEFAULT_SOT_MIN = -40.0
DEFAULT_SOT_MAX = 22.0
DEFAULT_STEP_MINUTES = 15
DEFAULT_HORIZON_STEPS = 8
DEFAULT_ENABLED = True

DATA_COORDINATOR = "coordinator"

ATTR_COMPUTED_SOT = "computed_sot"
ATTR_VIRTUAL_TEMP = "virtual_temp"
ATTR_COLDEST = "coldest"
ATTR_HOTTEST = "hottest"
ATTR_PRICE_NOW = "price_now"
