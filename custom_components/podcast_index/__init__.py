"""The PodcastIndex integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONF_API_SECRET,
    CONF_SEARCH_TERM,
    DOMAIN,
)
from .podcast_index_api import PodcastIndexAPI

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# CONFIG_SCHEMA removed: Only config flow (UI) is supported

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PodcastIndex from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get API credentials from secrets.yaml
    api_key = None
    api_secret = None
    
    try:
        # Try to get from hass.data first (if already loaded)
        api_key = hass.data.get("secrets", {}).get("podcast_index_api_key")
        api_secret = hass.data.get("secrets", {}).get("podcast_index_api_secret")
        
        if not api_key or not api_secret:
            # Load from secrets.yaml file
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

    search_term = entry.data[CONF_SEARCH_TERM]
    name = entry.data.get(CONF_NAME, "PodcastIndex")

    api = PodcastIndexAPI(api_key, api_secret, search_term)

    try:
        # Test the API connection
        await api.test_connection()
    except Exception as ex:
        _LOGGER.error("Failed to connect to PodcastIndex API: %s", ex)
        raise ConfigEntryNotReady from ex

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "name": name,
    }

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

        try:
            # Get the latest episode for the search term
            episode = await api.get_latest_episode(search_term)
            if not episode or not episode.get("audio_url"):
                _LOGGER.error("No audio URL found for search term: %s", search_term)
                return

            # Play the episode on the media player
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
        # Unregister services
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