from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass
class ControllerConfig:
    minimum_indoor_temperature: float
    maximum_indoor_temperature: float
    sot_min: float
    sot_max: float
    step_minutes: int
    horizon_steps: int


class SimplePriceAwareController:
    def __init__(self, cfg: ControllerConfig):
        self.cfg = cfg

    def compute(self, temps: Sequence[float], prices: Sequence[float]) -> dict:
        # temps: list of indoor temps from multiple sensors
        # prices: list of prices, len >= 1 (currency per kWh)
        if not temps:
            return {"sot": None, "virtual_temp": None, "coldest": None, "hottest": None}

        t_avg = sum(temps) / len(temps)
        t_cold = min(temps)
        t_hot = max(temps)

        # Price-aware target inside comfort band
        p0 = prices[0] if prices else 0.0
        # Percentiles require horizon; fallback thresholds
        if len(prices) >= 4:
            sorted_p = sorted(prices[: min(len(prices), 16)])
            q25 = sorted_p[len(sorted_p) // 4]
            q75 = sorted_p[(3 * len(sorted_p)) // 4]
        else:
            q25 = p0 * 0.9
            q75 = p0 * 1.1

        if p0 <= q25:
            t_target = min(self.cfg.maximum_indoor_temperature, self.cfg.maximum_indoor_temperature - 0.2)
        elif p0 >= q75:
            t_target = max(self.cfg.minimum_indoor_temperature, self.cfg.minimum_indoor_temperature + 0.2)
        else:
            t_target = (self.cfg.minimum_indoor_temperature + self.cfg.maximum_indoor_temperature) / 2.0

        # Simple proportional rule to set SOT: colder if below target, warmer if above
        error = t_target - t_avg
        # Map error [-2, +2] C to u [0,1]
        u = 0.5 + 0.25 * error  # small gain; tune later
        u = max(0.0, min(1.0, u))

        # Linear map u -> SOT
        sot = self.cfg.sot_max - u * (self.cfg.sot_max - self.cfg.sot_min)
        sot = max(self.cfg.sot_min, min(self.cfg.sot_max, sot))

        return {
            "sot": round(sot, 2),
            "virtual_temp": round(t_avg, 2),
            "coldest": round(t_cold, 2),
            "hottest": round(t_hot, 2),
        }
