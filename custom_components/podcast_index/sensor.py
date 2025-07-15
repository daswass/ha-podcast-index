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
    ATTR_SEARCH_OR_ID,
    ATTR_FEED_URL,
    ATTR_HOURS_SINCE_PUBLISH,
    ATTR_PODCAST_ICON,
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
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    name = entry_data["name"]
    coordinators = entry_data["coordinators"]
    search_or_id_list = entry_data["search_or_id_list"]

    entities = []
    for term in search_or_id_list:
        coordinator = coordinators[term]
        entities.append(PodcastIndexSensor(coordinator, name, term))

    async_add_entities(entities, True)


class PodcastIndexSensor(CoordinatorEntity, SensorEntity):
    """Representation of a PodcastIndex sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, name: str, term: str
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._term = term
        self._base_name = name
        self._attr_name = f"{name} {term} Latest Episode"
        self._attr_unique_id = f"{name.lower().replace(' ', '_')}_{term.lower().replace(' ', '_')}_latest_episode"

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        if self.coordinator.data and self.coordinator.data.get(ATTR_PODCAST_TITLE):
            podcast_title = self.coordinator.data.get(ATTR_PODCAST_TITLE)
            return f"{self._base_name} {podcast_title} Latest Episode"
        return f"{self._base_name} {self._term} Latest Episode"

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

        # Calculate hours since publish
        hours_since_publish = None
        publish_timestamp = episode.get(ATTR_PUBLISH_DATE)
        if publish_timestamp:
            try:
                publish_datetime = datetime.fromtimestamp(publish_timestamp)
                current_datetime = datetime.now()
                time_difference = current_datetime - publish_datetime
                hours_since_publish = round(time_difference.total_seconds() / 3600, 1)
            except (ValueError, TypeError):
                hours_since_publish = None

        return {
            ATTR_TITLE: episode.get(ATTR_TITLE, ""),
            ATTR_DESCRIPTION: episode.get(ATTR_DESCRIPTION, ""),
            ATTR_PUBLISH_DATE: publish_date,
            ATTR_DURATION: duration,
            ATTR_AUDIO_URL: episode.get(ATTR_AUDIO_URL, ""),
            ATTR_PODCAST_TITLE: episode.get(ATTR_PODCAST_TITLE, ""),
            ATTR_EPISODE_NUMBER: episode.get(ATTR_EPISODE_NUMBER),
            ATTR_SEASON_NUMBER: episode.get(ATTR_SEASON_NUMBER),
            ATTR_SEARCH_OR_ID: self._term,
            ATTR_FEED_URL: episode.get(ATTR_FEED_URL, ""),
            ATTR_HOURS_SINCE_PUBLISH: hours_since_publish,
            ATTR_PODCAST_ICON: episode.get(ATTR_PODCAST_ICON, ""),
            "guid": episode.get("guid", ""),
            "link": episode.get("link", ""),
        }

    @property
    def icon(self) -> str:
        """Return the icon of the sensor."""
        return "mdi:podcast" 