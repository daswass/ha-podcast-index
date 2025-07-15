"""Constants for the PodcastIndex integration."""

DOMAIN = "podcast_index"

CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_SEARCH_OR_ID = "search_or_id"  # Can be a search term or a podcast ID

DEFAULT_NAME = "PodcastIndex"
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# PodcastIndex API endpoints
PODCAST_INDEX_BASE_URL = "https://api.podcastindex.org/api/1.0"
PODCAST_INDEX_SEARCH_ENDPOINT = "/search/byterm"
PODCAST_INDEX_EPISODES_ENDPOINT = "/episodes/byfeedurl"

# Sensor attributes
ATTR_TITLE = "title"
ATTR_DESCRIPTION = "description"
ATTR_PUBLISH_DATE = "publish_date"
ATTR_DURATION = "duration"
ATTR_AUDIO_URL = "audio_url"
ATTR_PODCAST_TITLE = "podcast_title"
ATTR_EPISODE_NUMBER = "episode_number"
ATTR_SEASON_NUMBER = "season_number"
ATTR_SEARCH_OR_ID = "search_or_id"
ATTR_FEED_URL = "feed_url"
ATTR_HOURS_SINCE_PUBLISH = "hours_since_publish"
ATTR_PODCAST_ICON = "podcast_icon" 