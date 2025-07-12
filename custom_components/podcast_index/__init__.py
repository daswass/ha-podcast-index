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

    # Register services
    async def async_search_and_play(call: ServiceCall) -> None:
        """Search for a podcast and play its latest episode."""
        entity_id = call.data.get("entity_id")
        search_term = call.data.get("search_term")
        volume = call.data.get("volume")
        
        if not entity_id:
            _LOGGER.error("No entity_id provided")
            return
        if not search_term:
            _LOGGER.error("No search_term provided")
            return
            
        # Use the API for this entry
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        try:
            # First, unjoin all speakers
            await hass.services.async_call(
                "media_player",
                "unjoin",
                {"entity_id": entity_id},
            )
            _LOGGER.info("Unjoined speakers for %s", entity_id)
            
            # Set volume if provided
            if volume is not None:
                await hass.services.async_call(
                    "media_player",
                    "volume_set",
                    {
                        "entity_id": entity_id,
                        "volume_level": volume / 100.0,  # Convert percentage to 0-1 scale
                    },
                )
                _LOGGER.info("Set volume to %s%% for %s", volume, entity_id)
            
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

    async def async_add_search_term(call: ServiceCall) -> None:
        """Add a new search term to the existing configuration."""
        search_term = call.data.get("search_term")
        target_entry_id = call.data.get("entry_id")
        
        if not search_term:
            _LOGGER.error("No search_term provided")
            return
            
        search_term = search_term.strip()
        if not search_term:
            _LOGGER.error("Empty search term provided")
            return
        
        # Check if this service call is meant for this entry
        if target_entry_id and target_entry_id != entry.entry_id:
            # This service call is not meant for this entry, ignore it
            return
        
        # Check if term already exists
        entry_name = hass.data[DOMAIN][entry.entry_id]["name"]
        if search_term in hass.data[DOMAIN][entry.entry_id]["search_or_id_list"]:
            _LOGGER.warning("Search term '%s' already exists in integration '%s'", search_term, entry_name)
            return
            
        try:
            # Test the API connection with the new term
            api = PodcastIndexAPI(api_key, api_secret, search_term)
            await api.test_connection()
            await api.close()
            
            # Get current search terms and add the new one
            current_terms = hass.data[DOMAIN][entry.entry_id]["search_or_id_list"]
            new_terms = current_terms + [search_term]
            
            # Update the config entry with the new search terms
            new_data = entry.data.copy()
            new_data[CONF_SEARCH_OR_ID] = ", ".join(new_terms)
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            
            # Reload the integration to pick up the new search term
            await hass.config_entries.async_reload(entry.entry_id)
            
            _LOGGER.info("Added new search term '%s' to integration '%s' and reloaded", search_term, entry_name)
                
        except Exception as ex:
            _LOGGER.error("Failed to add search term '%s': %s", search_term, ex)

    async def async_remove_search_term(call: ServiceCall) -> None:
        """Remove a search term from the existing configuration."""
        search_term = call.data.get("search_term")
        target_entry_id = call.data.get("entry_id")
        
        if not search_term:
            _LOGGER.error("No search_term provided")
            return
            
        search_term = search_term.strip()
        if not search_term:
            _LOGGER.error("Empty search term provided")
            return
        
        # Check if this service call is meant for this entry
        if target_entry_id and target_entry_id != entry.entry_id:
            # This service call is not meant for this entry, ignore it
            return
        
        # Check if term exists
        entry_name = hass.data[DOMAIN][entry.entry_id]["name"]
        if search_term not in hass.data[DOMAIN][entry.entry_id]["search_or_id_list"]:
            _LOGGER.warning("Search term '%s' does not exist in integration '%s'", search_term, entry_name)
            return
            
        try:
            # Get current search terms and remove the specified one
            current_terms = hass.data[DOMAIN][entry.entry_id]["search_or_id_list"]
            new_terms = [term for term in current_terms if term != search_term]
            
            if not new_terms:
                _LOGGER.error("Cannot remove the last search term. At least one search term is required.")
                return
            
            # Update the config entry with the new search terms
            new_data = entry.data.copy()
            new_data[CONF_SEARCH_OR_ID] = ", ".join(new_terms)
            
            hass.config_entries.async_update_entry(entry, data=new_data)
            
            # Reload the integration to pick up the changes
            await hass.config_entries.async_reload(entry.entry_id)
            
            _LOGGER.info("Removed search term '%s' from integration '%s' and reloaded", search_term, entry_name)
                
        except Exception as ex:
            _LOGGER.error("Failed to remove search term '%s': %s", search_term, ex)

    hass.services.async_register(
        DOMAIN, "search_and_play", async_search_and_play
    )
    
    hass.services.async_register(
        DOMAIN, "add_search_term", async_add_search_term
    )
    
    hass.services.async_register(
        DOMAIN, "remove_search_term", async_remove_search_term
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