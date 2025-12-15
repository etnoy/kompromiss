from homeassistant.const import Platform

DOMAIN = "kompromiss"
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

ACTUAL_OUTDOOR_TEMPERATURE_SENSOR = "actual_outdoor_temperature_sensor"
SIMULATED_OUTDOOR_TEMPERATURE_SENSOR = "simulated_outdoor_temperature_sensor"
TEMPERATURE_OFFSET_SENSOR = "temperature_offset_sensor"
INDOOR_TEMPERATURE_SENSOR = "indoor_temperature_sensor"

TARGET_TEMPERATURE = "target_temperature"
DEFAULT_TARGET_TEMPERATURE = 21.0
MINIMUM_INDOOR_TEMPERATURE = "minimum_indoor_temperature"
DEFAULT_MINIMUM_INDOOR_TEMPERATURE = 19.5
MAXIMUM_INDOOR_TEMPERATURE = "maximum_indoor_temperature"
DEFAULT_MAXIMUM_INDOOR_TEMPERATURE = 22.5

TEMPERATURE_DEVIATION_PENALTY = "temperature_deviation_penalty"
DEFAULT_TEMPERATURE_DEVIATION_PENALTY = 100.0

COMFORT_BAND_VIOLATION_PENALTY = "comfort_band_violation_penalty"
DEFAULT_COMFORT_BAND_VIOLATION_PENALTY = 10000.0

THERMAL_RESISTANCE = "thermal_resistance"
DEFAULT_THERMAL_RESISTANCE = 0.005
THERMAL_CAPACITANCE = "thermal_capacitance"
DEFAULT_THERMAL_CAPACITANCE = 3.6e6

MEDIUM_TO_BUILDING_THERMAL_RESISTANCE = "medium_to_building_thermal_resistance"
DEFAULT_MEDIUM_TO_BUILDING_THERMAL_RESISTANCE = 0.0035
MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE = "medium_to_outdoor_thermal_resistance"
DEFAULT_MEDIUM_TO_OUTDOOR_THERMAL_RESISTANCE = 0.2
MEDIUM_THERMAL_CAPACITY = "medium_thermal_capacity"
DEFAULT_MEDIUM_THERMAL_CAPACITY = 2.5e5

HEATER_THERMAL_POWER = "heater_thermal_power"
DEFAULT_HEATER_THERMAL_POWER = 10000.0
HEAT_CURVE_SLOPE = "heat_curve_slope"
DEFAULT_HEAT_CURVE_SLOPE = -0.7
HEAT_CURVE_INTERCEPT = "heat_curve_intercept"
DEFAULT_HEAT_CURVE_INTERCEPT = 35.0
HEATER_TRANSFER_COEFFICIENT = "heater_transfer_coefficient"
DEFAULT_HEATER_TRANSFER_COEFFICIENT = (
    500.0  # W/K gain from return setpoint to medium heat
)

MINIMUM_MEDIUM_RETURN_TEMPERATURE = "minimum_medium_return_temperature"
DEFAULT_MINIMUM_MEDIUM_RETURN_TEMPERATURE = 20.0
MAXIMUM_MEDIUM_RETURN_TEMPERATURE = "maximum_medium_return_temperature"
DEFAULT_MAXIMUM_MEDIUM_RETURN_TEMPERATURE = 65.0

PREDICTION_HORIZON = "prediction_horizon"
DEFAULT_PREDICTION_HORIZON = 12 * 4
TIME_STEP = "time_step"
DEFAULT_TIME_STEP = 900.0
OUTDOOR_RAMP_LIMIT = "outdoor_ramp_limit"
DEFAULT_OUTDOOR_RAMP_LIMIT = 4.0

ENERGY_COST_PENALTY = "energy_cost_penalty"
DEFAULT_ENERGY_COST_PENALTY = 5.0

LOWEST_SIMULATED_TEMPERATURE = "lowest_simulated_temperature"
DEFAULT_LOWEST_SIMULATED_TEMPERATURE = -30.0
HIGHEST_SIMULATED_TEMPERATURE = "highest_simulated_temperature"
# 20 degrees is often where summer mode kicks in, so let's put 19 as the max
DEFAULT_HIGHEST_SIMULATED_TEMPERATURE = 19.0
SIMULATED_OUTDOOR_MOVE_PENALTY = "simulated_outdoor_move_penalty"
DEFAULT_SIMULATED_OUTDOOR_MOVE_PENALTY = 50.0

# Signals for MPC parameter changes
SIGNAL_MPC_WEIGHT_TEMP_DEVIATION_CHANGED = (
    "kompromiss_mpc_weight_temp_deviation_changed"
)
SIGNAL_MPC_WEIGHT_COMFORT_VIOLATION_CHANGED = (
    "kompromiss_mpc_weight_comfort_violation_changed"
)

# Electricity price usually updates every 15 minutes, so align with that
DEFAULT_STEP_MINUTES = 15
DEFAULT_HORIZON_STEPS = 8
DEFAULT_ENABLED = True
