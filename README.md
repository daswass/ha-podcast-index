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

1. **Search Term**: A search term to find podcasts (e.g., "tech news", "comedy", "science")
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
- **Attributes**:
  - `title`: Episode title
  - `description`: Episode description
  - `publish_date`: When the episode was published
  - `duration`: Episode duration in HH:MM:SS format
  - `audio_url`: Direct link to the audio file
  - `podcast_title`: Name of the podcast
  - `episode_number`: Episode number (if available)
  - `season_number`: Season number (if available)
  - `search_term`: The search term used to find the podcast
  - `feed_url`: The RSS feed URL of the podcast

### Service

The integration provides a single service for playing episodes:

#### Search and Play

**Service**: `podcast_index.search_and_play`

**Parameters**:

- `entity_id`: The media player entity to play the episode on
- `search_term`: The search term to find the podcast

**Example**:

```yaml
# Search for "tech news" and play the latest episode
service: podcast_index.search_and_play
target:
  entity_id: media_player.kitchen_speaker
data:
  search_term: "tech news"
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
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to PodcastIndex API"**

   - Verify your API credentials are correctly set in secrets.yaml
   - Check that the search term is valid
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

   - The search term might not return any results
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
