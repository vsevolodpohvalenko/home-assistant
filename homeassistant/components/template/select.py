"""Support for selects which integrates with other components."""
from __future__ import annotations

import contextlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.select import SelectEntity
from homeassistant.components.select.const import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import CONF_NAME, CONF_OPTIMISTIC, CONF_STATE, CONF_UNIQUE_ID
from homeassistant.core import Config, HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.script import Script
from homeassistant.helpers.template import Template, TemplateError

from . import TriggerUpdateCoordinator
from .const import CONF_AVAILABILITY
from .template_entity import TemplateEntity
from .trigger_entity import TriggerEntity

_LOGGER = logging.getLogger(__name__)

CONF_SELECT_OPTION = "select_option"

DEFAULT_NAME = "Template Select"
DEFAULT_OPTIMISTIC = False

SELECT_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.template,
        vol.Required(CONF_STATE): cv.template,
        vol.Required(CONF_SELECT_OPTION): cv.SCRIPT_SCHEMA,
        vol.Required(ATTR_OPTIONS): cv.template,
        vol.Optional(CONF_AVAILABILITY): cv.template,
        vol.Optional(CONF_OPTIMISTIC, default=DEFAULT_OPTIMISTIC): cv.boolean,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def _async_create_entities(
    hass: HomeAssistant, entities: list[dict[str, Any]], unique_id_prefix: str | None
) -> list[TemplateSelect]:
    """Create the Template select."""
    for entity in entities:
        unique_id = entity.get(CONF_UNIQUE_ID)

        if unique_id and unique_id_prefix:
            unique_id = f"{unique_id_prefix}-{unique_id}"

        return [
            TemplateSelect(
                hass,
                entity.get(CONF_NAME, DEFAULT_NAME),
                entity[CONF_STATE],
                entity.get(CONF_AVAILABILITY),
                entity[CONF_SELECT_OPTION],
                entity[ATTR_OPTIONS],
                entity.get(CONF_OPTIMISTIC, DEFAULT_OPTIMISTIC),
                unique_id,
            )
        ]


async def async_setup_platform(
    hass: HomeAssistant,
    config: Config,
    async_add_entities: AddEntitiesCallback,
    discovery_info: dict[str, Any] | None = None,
) -> None:
    """Set up the template select."""
    if discovery_info is None:
        _LOGGER.warning(
            "Template number entities can only be configured under template:"
        )
        return

    if "coordinator" in discovery_info:
        async_add_entities(
            TriggerSelectEntity(hass, discovery_info["coordinator"], config)
            for config in discovery_info["entities"]
        )
        return

    async_add_entities(
        await _async_create_entities(
            hass, discovery_info["entities"], discovery_info["unique_id"]
        )
    )


class TemplateSelect(TemplateEntity, SelectEntity):
    """Representation of a template select."""

    def __init__(
        self,
        hass: HomeAssistant,
        name_template: Template | None,
        value_template: Template,
        availability_template: Template | None,
        command_select_option: dict[str, Any],
        options_template: Template,
        optimistic: bool,
        unique_id: str | None,
    ) -> None:
        """Initialize the select."""
        super().__init__(availability_template=availability_template)
        self._attr_name = DEFAULT_NAME
        name_template.hass = hass
        with contextlib.suppress(TemplateError):
            self._attr_name = name_template.async_render(parse_result=False)
        self._name_template = name_template
        self._value_template = value_template
        domain = __name__.split(".")[-2]
        self._command_select_option = Script(
            hass, command_select_option, self._attr_name, domain
        )
        self._options_template = options_template
        self._attr_assumed_state = self._optimistic = optimistic
        self._attr_unique_id = unique_id
        self._attr_options = None
        self._attr_current_option = None

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.add_template_attribute(
            "_attr_current_option",
            self._value_template,
            validator=cv.string,
            none_on_template_error=True,
        )
        self.add_template_attribute(
            "_attr_options",
            self._options_template,
            validator=vol.All(cv.ensure_list, [cv.string]),
            none_on_template_error=True,
        )
        if self._name_template and not self._name_template.is_static:
            self.add_template_attribute("_attr_name", self._name_template, cv.string)
        await super().async_added_to_hass()

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self._optimistic:
            self._attr_current_option = option
            self.async_write_ha_state()
        await self._command_select_option.async_run(
            {ATTR_OPTION: option}, context=self._context
        )


class TriggerSelectEntity(TriggerEntity, SelectEntity):
    """Select entity based on trigger data."""

    domain = SELECT_DOMAIN
    extra_template_keys = (CONF_STATE,)
    extra_template_keys_complex = (ATTR_OPTIONS,)

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TriggerUpdateCoordinator,
        config: dict,
    ) -> None:
        """Initialize the entity."""
        super().__init__(hass, coordinator, config)
        domain = __name__.split(".")[-2]
        self._command_select_option = Script(
            hass,
            config[CONF_SELECT_OPTION],
            self._rendered.get(CONF_NAME, DEFAULT_NAME),
            domain,
        )

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        return self._rendered.get(CONF_STATE)

    @property
    def options(self) -> list[str]:
        """Return the list of available options."""
        return self._rendered.get(ATTR_OPTIONS, [])

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        if self._config[CONF_OPTIMISTIC]:
            self._attr_current_option = option
            self.async_write_ha_state()
        await self._command_select_option.async_run(
            {ATTR_OPTION: option}, context=self._context
        )
