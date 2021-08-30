"""Base classes for Renault entities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Optional, TypeVar, cast

from renault_api.kamereon.models import KamereonVehicleDataAttributes

from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .renault_vehicle import RenaultVehicleProxy


@dataclass
class RenaultRequiredKeysMixin:
    """Mixin for required keys."""

    coordinator: str


@dataclass
class RenaultEntityDescription(EntityDescription, RenaultRequiredKeysMixin):
    """Class describing Renault entities."""


ATTR_LAST_UPDATE = "last_update"

T = TypeVar("T", bound=KamereonVehicleDataAttributes)


class RenaultDataEntity(CoordinatorEntity[Optional[T]], Entity):
    """Implementation of a Renault entity with a data coordinator."""

    entity_description: RenaultEntityDescription

    def __init__(
        self,
        vehicle: RenaultVehicleProxy,
        description: RenaultEntityDescription,
    ) -> None:
        """Initialise entity."""
        super().__init__(vehicle.coordinators[description.coordinator])
        self.vehicle = vehicle
        self.entity_description = description
        self._attr_device_info = self.vehicle.device_info
        self._attr_unique_id = f"{self.vehicle.details.vin}_{description.key}".lower()

    def _get_data_attr(self, key: str) -> StateType:
        """Return the attribute value from the coordinator data."""
        if self.coordinator.data is None:
            return None
        return cast(StateType, getattr(self.coordinator.data, key))

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        """Return the state attributes of this entity."""
        if self.entity_description.coordinator == "battery":
            last_update = self._get_data_attr("timestamp")
            if last_update:
                return {ATTR_LAST_UPDATE: last_update}
        return None
