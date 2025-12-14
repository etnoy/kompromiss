"""Passthrough regulator that returns input as output without modification."""

from __future__ import annotations

from . import Regulator


class PassthroughRegulator(Regulator):
    """A regulator that just passes through input values unchanged.

    This is useful for testing and as a baseline regulator that doesn't
    perform any control logic.
    """

    def __init__(self) -> None:
        self._state: float | None = None
        self._output: float | None = None
        super().__init__()

    async def set_state(self, state: float | None) -> None:
        self._state = state

    async def get_output(self) -> float | None:
        return self._output

    async def async_regulate(self) -> float:
        if self._state is None:
            self._output = None

        # This is a passthrough regulator, so output equals input
        self._output = self._state
