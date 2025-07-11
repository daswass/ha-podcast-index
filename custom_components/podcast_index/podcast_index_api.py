"""PodcastIndex API client."""
from __future__ import annotations

import hashlib
import time
from typing import Any
import aiohttp
import logging

from .const import PODCAST_INDEX_BASE_URL, PODCAST_INDEX_EPISODES_ENDPOINT

_LOGGER = logging.getLogger(__name__)


class PodcastIndexAPI:
    """PodcastIndex API client."""

    def __init__(self, api_key: str, api_secret: str, podcast_feed_url: str) -> None:
        """Initialize the PodcastIndex API client."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.podcast_feed_url = podcast_feed_url
        self.session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    def _generate_auth_headers(self) -> dict[str, str]:
        """Generate authentication headers for PodcastIndex API."""
        # PodcastIndex uses a custom authentication method
        # They require User-Agent, Authorization, and X-Auth-Date headers
        timestamp = str(int(time.time()))
        
        # Create the authorization string
        auth_string = f"{self.api_key}{self.api_secret}{timestamp}"
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()
        
        return {
            "User-Agent": "HomeAssistant-PodcastIndex-Integration/1.0",
            "Authorization": auth_hash,
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": timestamp,
        }

    async def test_connection(self) -> bool:
        """Test the connection to PodcastIndex API."""
        try:
            # Try to get episodes to test the connection
            await self.get_latest_episode()
            return True
        except Exception as ex:
            _LOGGER.error("Failed to test PodcastIndex API connection: %s", ex)
            raise

    async def get_latest_episode(self) -> dict[str, Any] | None:
        """Get the latest episode of the configured podcast."""
        session = await self._get_session()
        
        params = {
            "url": self.podcast_feed_url,
            "max": 1,  # Get only the latest episode
        }
        
        headers = self._generate_auth_headers()
        
        try:
            async with session.get(
                f"{PODCAST_INDEX_BASE_URL}{PODCAST_INDEX_EPISODES_ENDPOINT}",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("status") == "true" and data.get("episodes"):
                    episode = data["episodes"][0]  # Get the first (latest) episode
                    return self._parse_episode(episode)
                else:
                    _LOGGER.warning("No episodes found or API returned error: %s", data)
                    return None
                    
        except aiohttp.ClientError as ex:
            _LOGGER.error("Failed to fetch latest episode: %s", ex)
            raise
        except Exception as ex:
            _LOGGER.error("Unexpected error fetching latest episode: %s", ex)
            raise

    def _parse_episode(self, episode_data: dict[str, Any]) -> dict[str, Any]:
        """Parse episode data from PodcastIndex API response."""
        return {
            "title": episode_data.get("title", ""),
            "description": episode_data.get("description", ""),
            "publish_date": episode_data.get("datePublished", 0),
            "duration": episode_data.get("duration", 0),
            "audio_url": episode_data.get("enclosureUrl", ""),
            "podcast_title": episode_data.get("feedTitle", ""),
            "episode_number": episode_data.get("episode", None),
            "season_number": episode_data.get("season", None),
            "guid": episode_data.get("guid", ""),
            "link": episode_data.get("link", ""),
        }

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None 