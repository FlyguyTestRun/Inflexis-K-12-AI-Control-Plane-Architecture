"""Plane 5: the model gateway.

This is the only package permitted to import a vendor SDK. Everything else
depends on the protocols in :mod:`inflexis.contracts.model`.
"""

from .registry import ModelRegistry, ModelRoutingError
from .gateway import ModelGateway
from .echo import EchoModelProvider

__all__ = [
    "ModelRegistry",
    "ModelRoutingError",
    "ModelGateway",
    "EchoModelProvider",
]
