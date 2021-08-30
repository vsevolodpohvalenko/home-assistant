"""Support for 1-Wire binary sensors."""
from __future__ import annotations

from dataclasses import dataclass
import os

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    CONF_TYPE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_TYPE_OWSERVER, DOMAIN, READ_MODE_BOOL
from .onewire_entities import OneWireEntityDescription, OneWireProxyEntity
from .onewirehub import OneWireHub


@dataclass
class OneWireBinarySensorEntityDescription(
    OneWireEntityDescription, BinarySensorEntityDescription
):
    """Class describing OneWire binary sensor entities."""


DEVICE_BINARY_SENSORS: dict[str, tuple[OneWireBinarySensorEntityDescription, ...]] = {
    "12": (
        OneWireBinarySensorEntityDescription(
            key="sensed.A",
            entity_registry_enabled_default=False,
            name="Sensed A",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.B",
            entity_registry_enabled_default=False,
            name="Sensed B",
            read_mode=READ_MODE_BOOL,
        ),
    ),
    "29": (
        OneWireBinarySensorEntityDescription(
            key="sensed.0",
            entity_registry_enabled_default=False,
            name="Sensed 0",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.1",
            entity_registry_enabled_default=False,
            name="Sensed 1",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.2",
            entity_registry_enabled_default=False,
            name="Sensed 2",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.3",
            entity_registry_enabled_default=False,
            name="Sensed 3",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.4",
            entity_registry_enabled_default=False,
            name="Sensed 4",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.5",
            entity_registry_enabled_default=False,
            name="Sensed 5",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.6",
            entity_registry_enabled_default=False,
            name="Sensed 6",
            read_mode=READ_MODE_BOOL,
        ),
        OneWireBinarySensorEntityDescription(
            key="sensed.7",
            entity_registry_enabled_default=False,
            name="Sensed 7",
            read_mode=READ_MODE_BOOL,
        ),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up 1-Wire platform."""
    # Only OWServer implementation works with binary sensors
    if config_entry.data[CONF_TYPE] == CONF_TYPE_OWSERVER:
        onewirehub = hass.data[DOMAIN][config_entry.entry_id]

        entities = await hass.async_add_executor_job(get_entities, onewirehub)
        async_add_entities(entities, True)


def get_entities(onewirehub: OneWireHub) -> list[BinarySensorEntity]:
    """Get a list of entities."""
    if not onewirehub.devices:
        return []

    entities: list[BinarySensorEntity] = []

    for device in onewirehub.devices:
        family = device["family"]
        device_type = device["type"]
        device_id = os.path.split(os.path.split(device["path"])[0])[1]

        if family not in DEVICE_BINARY_SENSORS:
            continue
        device_info: DeviceInfo = {
            ATTR_IDENTIFIERS: {(DOMAIN, device_id)},
            ATTR_MANUFACTURER: "Maxim Integrated",
            ATTR_MODEL: device_type,
            ATTR_NAME: device_id,
        }
        for description in DEVICE_BINARY_SENSORS[family]:
            device_file = os.path.join(
                os.path.split(device["path"])[0], description.key
            )
            name = f"{device_id} {description.name}"
            entities.append(
                OneWireProxyBinarySensor(
                    description=description,
                    device_id=device_id,
                    device_file=device_file,
                    device_info=device_info,
                    name=name,
                    owproxy=onewirehub.owproxy,
                )
            )

    return entities


class OneWireProxyBinarySensor(OneWireProxyEntity, BinarySensorEntity):
    """Implementation of a 1-Wire binary sensor."""

    entity_description: OneWireBinarySensorEntityDescription

    @property
    def is_on(self) -> bool:
        """Return true if sensor is on."""
        return bool(self._state)
