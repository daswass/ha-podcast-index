"""Config flow for PodcastIndex integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_SEARCH_TERM, DOMAIN
from .podcast_index_api import PodcastIndexAPI

_LOGGER = logging.getLogger(__name__)


class PodcastIndexConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PodcastIndex."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        super().__init__()
        self._api_key: str | None = None
        self._api_secret: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        # Get API credentials from secrets.yaml
        hass: HomeAssistant = self.hass
        try:
            self._api_key = hass.data.get("secrets", {}).get("podcast_index_api_key")
            self._api_secret = hass.data.get("secrets", {}).get("podcast_index_api_secret")
            
            if not self._api_key or not self._api_secret:
                # Try to load from secrets.yaml file
                secrets = await hass.async_add_executor_job(
                    self._load_secrets, hass.config.path("secrets.yaml")
                )
                self._api_key = secrets.get("podcast_index_api_key")
                self._api_secret = secrets.get("podcast_index_api_secret")

            if not self._api_key or not self._api_secret:
                errors["base"] = "missing_credentials"
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({}),
                    errors=errors,
                )

        except Exception as ex:
            _LOGGER.error("Failed to load API credentials from secrets: %s", ex)
            errors["base"] = "secrets_error"

        if user_input is not None:
            try:
                # Test the API connection
                api = PodcastIndexAPI(
                    self._api_key,
                    self._api_secret,
                    user_input[CONF_SEARCH_TERM],
                )
                await api.test_connection()
                await api.close()

                # Create the config entry
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, "PodcastIndex"),
                    data={
                        CONF_SEARCH_TERM: user_input[CONF_SEARCH_TERM],
                        CONF_NAME: user_input.get(CONF_NAME, "PodcastIndex"),
                    },
                )

            except Exception as ex:  # pylint: disable=broad-except
                _LOGGER.error("Failed to connect to PodcastIndex API: %s", ex)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SEARCH_TERM): str,
                    vol.Optional(CONF_NAME, default="PodcastIndex"): str,
                }
            ),
            errors=errors,
        )

    def _load_secrets(self, secrets_path: str) -> dict[str, Any]:
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