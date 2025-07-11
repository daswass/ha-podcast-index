"""The PodcastIndex integration."""
from __future__ import annotations

import logging
from typing import Any
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_API_SECRET,
    CONF_SEARCH_OR_ID,
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
)
from .podcast_index_api import PodcastIndexAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PodcastIndex from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get API credentials from secrets.yaml
    api_key = None
    api_secret = None
    
    try:
        api_key = hass.data.get("secrets", {}).get("podcast_index_api_key")
        api_secret = hass.data.get("secrets", {}).get("podcast_index_api_secret")
        if not api_key or not api_secret:
            secrets = await hass.async_add_executor_job(
                _load_secrets, hass.config.path("secrets.yaml")
            )
            api_key = secrets.get("podcast_index_api_key")
            api_secret = secrets.get("podcast_index_api_secret")
        if not api_key or not api_secret:
            _LOGGER.error("PodcastIndex API credentials not found in secrets.yaml")
            raise ConfigEntryNotReady("API credentials not found")
    except Exception as ex:
        _LOGGER.error("Failed to load API credentials from secrets: %s", ex)
        raise ConfigEntryNotReady from ex

    search_or_id_raw = entry.data[CONF_SEARCH_OR_ID]
    name = entry.data.get(CONF_NAME, "PodcastIndex")

    # Split comma-separated list, strip whitespace, remove empty
    search_or_id_list = [s.strip() for s in search_or_id_raw.split(",") if s.strip()]

    # Store API and coordinators per term/id
    hass.data[DOMAIN][entry.entry_id] = {
        "api": PodcastIndexAPI(api_key, api_secret, None),  # None, will be set per call
        "name": name,
        "coordinators": {},
        "search_or_id_list": search_or_id_list,
    }

    # Create a DataUpdateCoordinator for each term/id
    for term in search_or_id_list:
        api = PodcastIndexAPI(api_key, api_secret, term)
        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{name} {term} Latest Episode",
            update_method=lambda t=term, a=api: a.get_latest_episode(t),
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        await coordinator.async_config_entry_first_refresh()
        hass.data[DOMAIN][entry.entry_id]["coordinators"][term] = coordinator

    # Register only the search_and_play service
    async def async_search_and_play(call: ServiceCall) -> None:
        """Search for a podcast and play its latest episode."""
        entity_id = call.data.get("entity_id")
        search_term = call.data.get("search_term")
        if not entity_id:
            _LOGGER.error("No entity_id provided")
            return
        if not search_term:
            _LOGGER.error("No search_term provided")
            return
        # Use the API for this entry
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        try:
            episode = await api.get_latest_episode(search_term)
            if not episode or not episode.get("audio_url"):
                _LOGGER.error("No audio URL found for search term: %s", search_term)
                return
            await hass.services.async_call(
                "media_player",
                "play_media",
                {
                    "entity_id": entity_id,
                    "media_content_id": episode["audio_url"],
                    "media_content_type": "music",
                },
            )
            _LOGGER.info("Playing latest episode for '%s' on %s", search_term, entity_id)
        except Exception as ex:
            _LOGGER.error("Failed to search and play episode: %s", ex)

    hass.services.async_register(
        DOMAIN, "search_and_play", async_search_and_play
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
        hass.services.async_remove(DOMAIN, "search_and_play")
    return unload_ok

def _load_secrets(secrets_path: str) -> dict[str, Any]:
    """Load secrets from secrets.yaml file."""
    import yaml
    import os
    if not os.path.exists(secrets_path):
        return {}
    try:
        with open(secrets_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file) or {}
    except Exception as ex:
        _LOGGER.error("Failed to load secrets.yaml: %s", ex)
        return {} 