from homeassistant.const import Platform

DOMAIN = "kompromiss"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

CONF_ACTUAL_OUTDOOR_TEMPERATURE_SENSOR = "actual_outdoor_temperature_sensor"
CONF_SIMULATED_OUTDOOR_TEMPERATURE_SENSOR = "simulated_outdoor_temperature_sensor"
CONF_TEMPERATURE_OFFSET_SENSOR = "temperature_offset_sensor"
CONF_INDOOR_TEMPERATURE_SENSOR = "indoor_temperature_sensor"
CONF_ELECTRICITY_PRICE_SENSOR = "electricity_price_sensor"

CONF_LOWEST_SIMULATED_TEMPERATURE = "lowest_simulated_temperature"
CONF_HIGHEST_SIMULATED_TEMPERATURE = "highest_simulated_temperature"
CONF_STEP_MINUTES = "step_minutes"
CONF_HORIZON_STEPS = "horizon_steps"
CONF_ENABLED = "enabled"

DEFAULT_MINIMUM_INDOOR_TEMPERATURE = 19.5
DEFAULT_MAXIMUM_INDOOR_TEMPERATURE = 22.5
DEFAULT_LOWEST_SIMULATED_TEMPERATURE = -40.0
# 20 degrees is often where summer mode kicks in, so let's put 19 as the max
DEFAULT_HIGHEST_SIMULATED_TEMPERATURE = 19.0
# Electricity price usually updates every 15 minutes, so align with that
DEFAULT_STEP_MINUTES = 15
DEFAULT_HORIZON_STEPS = 8
DEFAULT_ENABLED = True
