"""Device simulator — stands in for edge-node firmware, implementing the
recipe/telemetry contract exactly (docs/architecture.md#4, #5, #7;
docs/delivery-plan.md "The integration guarantee").
"""

from agritwin_simulator.client import BackendClient, RecipePollOutcome
from agritwin_simulator.clock import VirtualClock
from agritwin_simulator.device import DeviceSimulator, FaultInjection, ZoneRuntimeConfig
from agritwin_simulator.fake_backend import FakeBackend
from agritwin_simulator.state import DeviceState

__all__ = [
    "BackendClient",
    "RecipePollOutcome",
    "VirtualClock",
    "DeviceSimulator",
    "FaultInjection",
    "ZoneRuntimeConfig",
    "FakeBackend",
    "DeviceState",
]
