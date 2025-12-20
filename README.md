<img src="https://raw.githubusercontent.com/etnoy/kompromiss/main/graphics/icon-1000.png" alt="https://github.com/etnoy/kompromiss" width="200"/>

**kompromiss** *(noun)* - the Swedish word for compromise and similar to **kompressor**, the Swedish word for compressor that drives our heat pumps. Heating a house will always be a compromise between comfort, cost and environmental impact, hence the name. 

---

NOTE: at this point in the project, please only use this integration to run simulations, not to control an actual heat pump.

# Warning

This tool is used at your own risk. An incorrect setup can lead to damage to your heat pump or house.

Also consider that having your heating system depend on Home Assistant and external hardware creates a dependency that may lead to your heating system not working if something goes wrong. Make sure you have a fail safe operation in place.

# Features
* Sophisticated temperature control thanks to using an Model Predictive Control (MPC) algorithm
* Simulation of outdoor temperature to control heater
* By default: heat regulation in order to stabilize indoor temperature
* If enabled, import nordpool electricity prices and optimize when heat is produced
* Fully configurable: control parameters, thermal model, weights, prediction horizon etc.
* Uses two chained 1R1C heat models where the medium flow temperature as well as the indoor temperature are taken into consideration

# Roadmap ideas
* Fail safe operation: if a sensor is unavailable or something goes wrong, the heat pump should automatically fall back on using the real outdoor sensor
* Easy for developers to add their own control algorithms
* Support for multiple indoor sensors with better weighting than just their average
* If multiple indoor sensors are used, the controller should (up to a point) ignore sensors affected by strong sunlight or a fireplace. In other words, allow specific sensors to be ignored automatically

# Requirements
* Home assistant
* Hardware, such as ohmonwifiplus
* HACS
* Nordpool integration (Official, not from HACS)
* Outdoor temperature sensor available in HA
* Indoor temperature sensor available in HA

# Installation
* Add the repository to HACS
* Download the integration from HACS
* Add the integration to Home Assistant

# Technical notes
There are tons of scientific papers on MPC control with 1R1C and similar thermal models. If you are an expert in this field, please give us your feedback.

The default simulation time step is 15 minutes

# Credits
The inspiration from this tool comes from the Ngenic Tune commercial product as well as [PumpSteer](https://github.com/JohanAlvedal/PumpSteer) by Johan Älvedal.