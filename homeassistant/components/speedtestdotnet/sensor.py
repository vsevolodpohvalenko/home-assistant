"""Support for Speedtest.net internet speed testing sensor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.components.speedtestdotnet import SpeedTestDataCoordinator
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_BYTES_RECEIVED,
    ATTR_BYTES_SENT,
    ATTR_SERVER_COUNTRY,
    ATTR_SERVER_ID,
    ATTR_SERVER_NAME,
    ATTRIBUTION,
    DEFAULT_NAME,
    DOMAIN,
    ICON,
    SENSOR_TYPES,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Speedtestdotnet sensors."""
    speedtest_coordinator = hass.data[DOMAIN]
    async_add_entities(
        SpeedtestSensor(speedtest_coordinator, description)
        for description in SENSOR_TYPES
    )


class SpeedtestSensor(CoordinatorEntity, RestoreEntity, SensorEntity):
    """Implementation of a speedtest.net sensor."""

    coordinator: SpeedTestDataCoordinator

    _attr_icon = ICON

    def __init__(
        self,
        coordinator: SpeedTestDataCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        self._attr_name = f"{DEFAULT_NAME} {description.name}"
        self._attr_unique_id = description.key
        self._attrs = {ATTR_ATTRIBUTION: ATTRIBUTION}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if self.coordinator.data:
            self._attrs.update(
                {
                    ATTR_SERVER_NAME: self.coordinator.data["server"]["name"],
                    ATTR_SERVER_COUNTRY: self.coordinator.data["server"]["country"],
                    ATTR_SERVER_ID: self.coordinator.data["server"]["id"],
                }
            )

            if self.entity_description.key == "download":
                self._attrs[ATTR_BYTES_RECEIVED] = self.coordinator.data[
                    "bytes_received"
                ]
            elif self.entity_description.key == "upload":
                self._attrs[ATTR_BYTES_SENT] = self.coordinator.data["bytes_sent"]

        return self._attrs

    async def async_added_to_hass(self) -> None:
        """Handle entity which will be added."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state:
            self._attr_native_value = state.state

        @callback
        def update() -> None:
            """Update state."""
            self._update_state()
            self.async_write_ha_state()

        self.async_on_remove(self.coordinator.async_add_listener(update))
        self._update_state()

    def _update_state(self):
        """Update sensors state."""
        if self.coordinator.data:
            if self.entity_description.key == "ping":
                self._attr_native_value = self.coordinator.data["ping"]
            elif self.entity_description.key == "download":
                self._attr_native_value = round(
                    self.coordinator.data["download"] / 10 ** 6, 2
                )
            elif self.entity_description.key == "upload":
                self._attr_native_value = round(
                    self.coordinator.data["upload"] / 10 ** 6, 2
                )
