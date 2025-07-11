"""PodcastIndex sensor platform."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_AUDIO_URL,
    ATTR_DESCRIPTION,
    ATTR_DURATION,
    ATTR_EPISODE_NUMBER,
    ATTR_PODCAST_TITLE,
    ATTR_PUBLISH_DATE,
    ATTR_SEASON_NUMBER,
    ATTR_TITLE,
    ATTR_SEARCH_TERM,
    ATTR_FEED_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PodcastIndex sensor platform."""
    api = hass.data[DOMAIN][config_entry.entry_id]["api"]
    name = hass.data[DOMAIN][config_entry.entry_id]["name"]

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{name} Latest Episode",
        update_method=api.get_latest_episode,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([PodcastIndexSensor(coordinator, name)], True)


class PodcastIndexSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PodcastIndex sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, name: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = f"{name} Latest Episode"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_latest_episode"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get(ATTR_TITLE, "No episode found")
        return "No episode found"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        if not self.coordinator.data:
            return {}

        episode = self.coordinator.data
        
        # Convert publish date from timestamp to readable format
        publish_date = episode.get(ATTR_PUBLISH_DATE)
        if publish_date:
            try:
                publish_date = datetime.fromtimestamp(publish_date).isoformat()
            except (ValueError, TypeError):
                publish_date = None

        # Convert duration from seconds to readable format
        duration = episode.get(ATTR_DURATION)
        if duration:
            try:
                duration = str(timedelta(seconds=duration))
            except (ValueError, TypeError):
                duration = None

        return {
            ATTR_TITLE: episode.get(ATTR_TITLE, ""),
            ATTR_DESCRIPTION: episode.get(ATTR_DESCRIPTION, ""),
            ATTR_PUBLISH_DATE: publish_date,
            ATTR_DURATION: duration,
            ATTR_AUDIO_URL: episode.get(ATTR_AUDIO_URL, ""),
            ATTR_PODCAST_TITLE: episode.get(ATTR_PODCAST_TITLE, ""),
            ATTR_EPISODE_NUMBER: episode.get(ATTR_EPISODE_NUMBER),
            ATTR_SEASON_NUMBER: episode.get(ATTR_SEASON_NUMBER),
            ATTR_SEARCH_TERM: episode.get(ATTR_SEARCH_TERM, ""),
            ATTR_FEED_URL: episode.get(ATTR_FEED_URL, ""),
            "guid": episode.get("guid", ""),
            "link": episode.get("link", ""),
        }

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:podcast" 