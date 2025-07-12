# PodcastIndex Home Assistant Integration

A Home Assistant integration that connects to the PodcastIndex API to fetch the latest episode of a podcast and provides functionality to play it on media players.

## Features

- Fetches the latest episode from any podcast feed via PodcastIndex API
- Displays episode information as a sensor with rich attributes
- Provides a service to search for and play the latest episode of any podcast on any media player
- Automatic updates every 5 minutes
- Proper authentication with PodcastIndex API

## Installation

### Manual Installation

1. Copy the `custom_components/podcast_index` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Integrations**
4. Click the **+ ADD INTEGRATION** button
5. Search for "PodcastIndex" and select it

### Configuration

You'll need the following information:

1. **Search Term or Podcast ID**: Enter a search term (e.g., "tech news", "comedy", "science") or a numeric PodcastIndex podcast ID.
2. **API Credentials**: Your PodcastIndex API credentials (stored in secrets.yaml)

### Setting up API Credentials

1. Go to [podcastindex.org](https://podcastindex.org)
2. Create an account or sign in
3. Navigate to your account settings
4. Generate API credentials (key and secret)
5. Add the credentials to your `secrets.yaml` file:

```yaml
# Add these lines to your secrets.yaml file
podcast_index_api_key: "your_api_key_here"
podcast_index_api_secret: "your_api_secret_here"
```

## Usage

### Sensor

The integration creates a sensor that shows:

- **State**: The title of the latest episode
- **Name**: The sensor name will show the podcast title when available (e.g., "PodcastIndex Tech News Latest Episode"), or fall back to the search term/ID if the title isn't available
- **Attributes**:
  - `title`: Episode title
  - `description`: Episode description
  - `publish_date`: When the episode was published
  - `duration`: Episode duration in HH:MM:SS format
  - `audio_url`: Direct link to the audio file
  - `podcast_title`: Name of the podcast (now properly populated for both search terms and podcast IDs)
  - `episode_number`: Episode number (if available)
  - `season_number`: Season number (if available)
  - `search_or_id`: The search term or podcast ID used to find the podcast
  - `feed_url`: The RSS feed URL of the podcast

### Services

The integration provides several services for managing podcasts and playing episodes:

#### Search and Play

**Service**: `podcast_index.search_and_play`

**Parameters**:

- `entity_id`: The media player entity to play the episode on
- `search_term`: The search term or podcast ID to find the podcast (numeric values are treated as PodcastIndex podcast IDs)
- `volume` (optional): Volume level (0-100) to set before playing. If not provided, the current volume is maintained.

#### Add Search Term

**Service**: `podcast_index.add_search_term`

**Parameters**:

- `search_term`: The new search term to add (e.g., "tech news" or a podcast ID)

This service allows you to add additional podcast search terms to an existing PodcastIndex integration after the initial configuration. The integration will automatically reload to pick up the new search term and create a new sensor for it.

#### Remove Search Term

**Service**: `podcast_index.remove_search_term`

**Parameters**:

- `search_term`: The search term to remove (must match exactly)

This service allows you to remove a podcast search term from an existing PodcastIndex integration. The integration will automatically reload to reflect the changes. Note: You cannot remove the last search term as at least one is required.

**Example**:

```yaml
# Search for "tech news" and play the latest episode
service: podcast_index.search_and_play
target:
  entity_id: media_player.kitchen_speaker
data:
  search_term: "tech news"

# Play the latest episode from a specific podcast by PodcastIndex ID
service: podcast_index.search_and_play
target:
  entity_id: media_player.kitchen_speaker
data:
  search_term: "1234567"

# Play with volume set to 50%
service: podcast_index.search_and_play
target:
  entity_id: media_player.kitchen_speaker
data:
  search_term: "tech news"
  volume: 50
```

### Automation Examples

```yaml
# Search and play different podcasts based on time
automation:
  - alias: "Morning Tech News"
    trigger:
      platform: time
      at: "08:00:00"
    action:
      - service: podcast_index.search_and_play
        target:
          entity_id: media_player.bedroom_speaker
        data:
          search_term: "tech news"

  - alias: "Evening Comedy"
    trigger:
      platform: time
      at: "19:00:00"
    action:
      - service: podcast_index.search_and_play
        target:
          entity_id: media_player.living_room_speaker
        data:
          search_term: "comedy"

  - alias: "Play by Podcast ID"
    trigger:
      platform: time
      at: "21:00:00"
    action:
      - service: podcast_index.search_and_play
        target:
          entity_id: media_player.office_speaker
        data:
          search_term: "1234567"

  - alias: "Evening News with Volume"
    trigger:
      platform: time
      at: "18:00:00"
    action:
      - service: podcast_index.search_and_play
        target:
          entity_id: media_player.living_room_speaker
        data:
          search_term: "evening news"
          volume: 75

# Managing search terms dynamically
automation:
  - alias: "Add Weekend Podcast"
    trigger:
      platform: time
      at: "06:00:00"
      days_of_week: ["sat", "sun"]
    action:
      - service: podcast_index.add_search_term
        target:
          entity_id: sensor.podcastindex_tech_news_latest_episode
        data:
          search_term: "weekend edition"

  - alias: "Remove Weekend Podcast"
    trigger:
      platform: time
      at: "23:00:00"
      days_of_week: ["sun"]
    action:
      - service: podcast_index.remove_search_term
        target:
          entity_id: sensor.podcastindex_tech_news_latest_episode
        data:
          search_term: "weekend edition"

  - alias: "Add New Podcast from Input"
    trigger:
      platform: state
      entity_id: input_text.new_podcast_search
    condition:
      condition: not
      conditions:
        - condition: template
          value_template: "{{ states('input_text.new_podcast_search') == '' }}"
    action:
      - service: podcast_index.add_search_term
        target:
          entity_id: sensor.podcastindex_tech_news_latest_episode
        data:
          search_term: "{{ states('input_text.new_podcast_search') }}"
      - service: input_text.set_value
        target:
          entity_id: input_text.new_podcast_search
        data:
          value: ""
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to PodcastIndex API"**

   - Verify your API credentials are correctly set in secrets.yaml
   - Check that the search term or podcast ID is valid
   - Ensure your internet connection is working

2. **"PodcastIndex API credentials not found in secrets.yaml"**

   - Add the required credentials to your secrets.yaml file:
     ```yaml
     podcast_index_api_key: "your_api_key_here"
     podcast_index_api_secret: "your_api_secret_here"
     ```
   - Ensure the secrets.yaml file is in your Home Assistant config directory
   - Restart Home Assistant after adding the credentials

3. **"No episodes found"**

   - The search term or podcast ID might not return any results
   - The podcast might not have any episodes
   - The podcast might be private or require authentication

4. **Media player doesn't play the episode**
   - Ensure the media player supports the audio format
   - Check that the audio URL is accessible
   - Verify the media player entity ID is correct

### Logs

Enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.podcast_index: debug
```

## Development

This integration is built using the latest Home Assistant patterns:

- Uses `DataUpdateCoordinator` for efficient data updates
- Implements proper async/await patterns
- Follows Home Assistant's entity naming conventions
- Uses modern config flow for setup
- Includes proper error handling and logging

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
