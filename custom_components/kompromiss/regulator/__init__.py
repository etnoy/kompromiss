"""Abstract base class for regulators."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Regulator(ABC):
    """Abstract base class for all regulators.

    A regulator takes input values and produces output values based on
    control logic. Subclasses must implement the regulate method.
    """

    @abstractmethod
    async def async_regulate(self) -> float:
        pass
