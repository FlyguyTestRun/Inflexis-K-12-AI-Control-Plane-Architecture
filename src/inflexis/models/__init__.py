"""Plane 5: the model gateway.

This is the only package permitted to import a vendor SDK. Everything else
depends on the protocols in :mod:`inflexis.contracts.model`.
"""

from .echo import EchoModelProvider
from .gateway import ModelGateway
from .registry import ModelRegistry, ModelRoutingError

__all__ = [
    "ModelRegistry",
    "ModelRoutingError",
    "ModelGateway",
    "EchoModelProvider",
]
