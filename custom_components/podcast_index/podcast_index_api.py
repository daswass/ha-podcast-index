"""PodcastIndex API client."""
from __future__ import annotations

import hashlib
import time
from typing import Any
import aiohttp
import logging

from .const import (
    PODCAST_INDEX_BASE_URL,
    PODCAST_INDEX_SEARCH_ENDPOINT,
    PODCAST_INDEX_EPISODES_ENDPOINT,
    CONF_SEARCH_OR_ID,
    ATTR_SEARCH_OR_ID,
)

_LOGGER = logging.getLogger(__name__)


class PodcastIndexAPI:
    """PodcastIndex API client."""

    def __init__(self, api_key: str, api_secret: str, search_term: str) -> None:
        """Initialize the PodcastIndex API client."""
        self.api_key = api_key
        self.api_secret = api_secret
        self.search_term = search_term
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
            # Try to search for a podcast to test the connection
            await self.search_podcasts("test")
            return True
        except Exception as ex:
            _LOGGER.error("Failed to test PodcastIndex API connection: %s", ex)
            raise

    async def search_podcasts(self, search_term: str | None = None) -> dict[str, Any] | None:
        """Search for podcasts by term."""
        session = await self._get_session()
        
        term = search_term or self.search_term
        params = {
            "q": term,
            "max": 1,  # Get only the top result
        }
        
        headers = self._generate_auth_headers()
        
        try:
            async with session.get(
                f"{PODCAST_INDEX_BASE_URL}{PODCAST_INDEX_SEARCH_ENDPOINT}",
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                if data.get("status") == "true" and data.get("feeds"):
                    podcast = data["feeds"][0]  # Get the first (top) result
                    return self._parse_podcast(podcast)
                else:
                    _LOGGER.warning("No podcasts found or API returned error: %s", data)
                    return None
                    
        except aiohttp.ClientError as ex:
            _LOGGER.error("Failed to search podcasts: %s", ex)
            raise
        except Exception as ex:
            _LOGGER.error("Unexpected error searching podcasts: %s", ex)
            raise

    async def get_latest_episode(self, search_term: str | None = None) -> dict[str, Any] | None:
        """Get the latest episode of the top podcast matching the search term or by podcast id."""
        # If the search term is numeric, treat it as a podcast id
        term = search_term or self.search_term
        if term and term.isdigit():
            # First, get the podcast feed information to get the title
            session = await self._get_session()
            params = {
                "id": term,
            }
            headers = self._generate_auth_headers()
            try:
                # Get podcast feed information
                async with session.get(
                    f"{PODCAST_INDEX_BASE_URL}/podcasts/byfeedid",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    feed_data = await response.json()
                    
                    if feed_data.get("status") == "true" and feed_data.get("feed"):
                        podcast = self._parse_podcast(feed_data["feed"])
                    else:
                        _LOGGER.warning("No podcast feed found for ID: %s", term)
                        podcast = None
                        
            except aiohttp.ClientError as ex:
                _LOGGER.error("Failed to fetch podcast feed by ID: %s", ex)
                podcast = None
            except Exception as ex:
                _LOGGER.error("Unexpected error fetching podcast feed by ID: %s", ex)
                podcast = None
            
            # Now get the latest episode
            params = {
                "id": term,
                "max": 1,  # Get only the latest episode
            }
            try:
                async with session.get(
                    f"{PODCAST_INDEX_BASE_URL}/episodes/byfeedid",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    episodes = data.get("episodes") or data.get("items")
                    if data.get("status") == "true" and episodes:
                        episode = episodes[0]
                        episode_data = self._parse_episode(episode)
                        # Add podcast information if available
                        if podcast:
                            episode_data.update({
                                "podcast_title": podcast.get("title", ""),
                                "feed_url": podcast.get("feed_url", ""),
                            })
                        episode_data.update({
                            "podcast_id": term,
                            "search_term": term,
                        })
                        return episode_data
                    else:
                        _LOGGER.warning("No episodes found or API returned error: %s", data)
                        return None
            except aiohttp.ClientError as ex:
                _LOGGER.error("Failed to fetch latest episode by podcast id: %s", ex)
                raise
            except Exception as ex:
                _LOGGER.error("Unexpected error fetching latest episode by podcast id: %s", ex)
                raise
        # Otherwise, use the search term as before
        # First, search for the podcast
        podcast = await self.search_podcasts(term)
        if not podcast or not podcast.get("feed_url"):
            _LOGGER.warning("No podcast found for search term: %s", term)
            return None
        
        # Then get the latest episode
        session = await self._get_session()
        
        params = {
            "url": podcast["feed_url"],
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
                episodes = data.get("episodes") or data.get("items")
                if data.get("status") == "true" and episodes:
                    episode = episodes[0]  # Get the first (latest) episode
                    episode_data = self._parse_episode(episode)
                    # Add podcast and search term info
                    episode_data.update({
                        "podcast_title": podcast.get("title", ""),
                        "feed_url": podcast.get("feed_url", ""),
                        "search_term": term,
                    })
                    return episode_data
                else:
                    _LOGGER.warning("No episodes found or API returned error: %s", data)
                    return None
                    
        except aiohttp.ClientError as ex:
            _LOGGER.error("Failed to fetch latest episode: %s", ex)
            raise
        except Exception as ex:
            _LOGGER.error("Unexpected error fetching latest episode: %s", ex)
            raise

    def _parse_podcast(self, podcast_data: dict[str, Any]) -> dict[str, Any]:
        """Parse podcast data from PodcastIndex API response."""
        return {
            "title": podcast_data.get("title", ""),
            "description": podcast_data.get("description", ""),
            "feed_url": podcast_data.get("url", ""),
            "website": podcast_data.get("link", ""),
            "language": podcast_data.get("language", ""),
            "author": podcast_data.get("author", ""),
            "categories": podcast_data.get("categories", {}),
            "image": podcast_data.get("image", ""),
            "last_updated": podcast_data.get("lastUpdateTime", 0),
        }

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