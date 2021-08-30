"""Support for Vallox ventilation unit sensors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    DEVICE_CLASS_CO2,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_TIMESTAMP,
    PERCENTAGE,
    TEMP_CELSIUS,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN, METRIC_KEY_MODE, SIGNAL_VALLOX_STATE_UPDATE, ValloxStateProxy

_LOGGER = logging.getLogger(__name__)


class ValloxSensor(SensorEntity):
    """Representation of a Vallox sensor."""

    _attr_should_poll = False
    entity_description: ValloxSensorEntityDescription

    def __init__(
        self,
        name: str,
        state_proxy: ValloxStateProxy,
        description: ValloxSensorEntityDescription,
    ) -> None:
        """Initialize the Vallox sensor."""
        self._state_proxy = state_proxy

        self.entity_description = description

        self._attr_name = f"{name} {description.name}"
        self._attr_available = False

    async def async_added_to_hass(self):
        """Call to update."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_VALLOX_STATE_UPDATE, self._update_callback
            )
        )

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    async def async_update(self):
        """Fetch state from the ventilation unit."""
        try:
            self._attr_native_value = self._state_proxy.fetch_metric(
                self.entity_description.metric_key
            )
            self._attr_available = True

        except (OSError, KeyError) as err:
            self._attr_available = False
            _LOGGER.error("Error updating sensor: %s", err)


class ValloxProfileSensor(ValloxSensor):
    """Child class for profile reporting."""

    async def async_update(self):
        """Fetch state from the ventilation unit."""
        try:
            self._attr_native_value = self._state_proxy.get_profile()
            self._attr_available = True

        except OSError as err:
            self._attr_available = False
            _LOGGER.error("Error updating sensor: %s", err)


# There seems to be a quirk with respect to the fan speed reporting. The device
# keeps on reporting the last valid fan speed from when the device was in
# regular operation mode, even if it left that state and has been shut off in
# the meantime.
#
# Therefore, first query the overall state of the device, and report zero
# percent fan speed in case it is not in regular operation mode.
class ValloxFanSpeedSensor(ValloxSensor):
    """Child class for fan speed reporting."""

    async def async_update(self):
        """Fetch state from the ventilation unit."""
        try:
            # If device is in regular operation, continue.
            if self._state_proxy.fetch_metric(METRIC_KEY_MODE) == 0:
                await super().async_update()
            else:
                # Report zero percent otherwise.
                self._attr_native_value = 0
                self._attr_available = True

        except (OSError, KeyError) as err:
            self._attr_available = False
            _LOGGER.error("Error updating sensor: %s", err)


class ValloxFilterRemainingSensor(ValloxSensor):
    """Child class for filter remaining time reporting."""

    async def async_update(self):
        """Fetch state from the ventilation unit."""
        try:
            days_remaining = int(
                self._state_proxy.fetch_metric(self.entity_description.metric_key)
            )
            days_remaining_delta = timedelta(days=days_remaining)

            # Since only a delta of days is received from the device, fix the
            # time so the timestamp does not change with every update.
            now = datetime.utcnow().replace(hour=13, minute=0, second=0, microsecond=0)

            self._attr_native_value = (now + days_remaining_delta).isoformat()
            self._attr_available = True

        except (OSError, KeyError) as err:
            self._attr_available = False
            _LOGGER.error("Error updating sensor: %s", err)


@dataclass
class ValloxSensorEntityDescription(SensorEntityDescription):
    """Describes Vallox sensor entity."""

    metric_key: str | None = None
    sensor_type: type[ValloxSensor] = ValloxSensor


SENSORS: tuple[ValloxSensorEntityDescription, ...] = (
    ValloxSensorEntityDescription(
        key="current_profile",
        name="Current Profile",
        icon="mdi:gauge",
        sensor_type=ValloxProfileSensor,
    ),
    ValloxSensorEntityDescription(
        key="fan_speed",
        name="Fan Speed",
        metric_key="A_CYC_FAN_SPEED",
        icon="mdi:fan",
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        sensor_type=ValloxFanSpeedSensor,
    ),
    ValloxSensorEntityDescription(
        key="remaining_time_for_filter",
        name="Remaining Time For Filter",
        metric_key="A_CYC_REMAINING_TIME_FOR_FILTER",
        device_class=DEVICE_CLASS_TIMESTAMP,
        sensor_type=ValloxFilterRemainingSensor,
    ),
    ValloxSensorEntityDescription(
        key="extract_air",
        name="Extract Air",
        metric_key="A_CYC_TEMP_EXTRACT_AIR",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    ValloxSensorEntityDescription(
        key="exhaust_air",
        name="Exhaust Air",
        metric_key="A_CYC_TEMP_EXHAUST_AIR",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    ValloxSensorEntityDescription(
        key="outdoor_air",
        name="Outdoor Air",
        metric_key="A_CYC_TEMP_OUTDOOR_AIR",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    ValloxSensorEntityDescription(
        key="supply_air",
        name="Supply Air",
        metric_key="A_CYC_TEMP_SUPPLY_AIR",
        device_class=DEVICE_CLASS_TEMPERATURE,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=TEMP_CELSIUS,
    ),
    ValloxSensorEntityDescription(
        key="humidity",
        name="Humidity",
        metric_key="A_CYC_RH_VALUE",
        device_class=DEVICE_CLASS_HUMIDITY,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ValloxSensorEntityDescription(
        key="efficiency",
        name="Efficiency",
        metric_key="A_CYC_EXTRACT_EFFICIENCY",
        icon="mdi:gauge",
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
    ValloxSensorEntityDescription(
        key="co2",
        name="CO2",
        metric_key="A_CYC_CO2_VALUE",
        device_class=DEVICE_CLASS_CO2,
        state_class=STATE_CLASS_MEASUREMENT,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensors."""
    if discovery_info is None:
        return

    name = hass.data[DOMAIN]["name"]
    state_proxy = hass.data[DOMAIN]["state_proxy"]

    async_add_entities(
        [
            description.sensor_type(name, state_proxy, description)
            for description in SENSORS
        ],
        update_before_add=False,
    )
