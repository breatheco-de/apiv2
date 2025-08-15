# Pull and Clean Assets Management Command

This Django management command (`pull_and_clean_assets`) pulls assets from GitHub and cleans them asynchronously using Celery tasks, with built-in throttling to respect GitHub API rate limits.

## Overview

The command processes assets in batches and queues two Celery tasks for each asset:
1. `async_pull_from_github` - Pulls the latest content from GitHub
2. `async_regenerate_asset_readme` - Cleans and regenerates the README content

## Usage

### Basic Usage

```bash
# Process assets that haven't been synced in the last 24 hours
python manage.py pull_and_clean_assets

# Process all assets (ignore last sync time)
python manage.py pull_and_clean_assets --all

# Force processing even for recently synced assets
python manage.py pull_and_clean_assets --force
```

### Filtering Options

```bash
# Process only PROJECT assets
python manage.py pull_and_clean_assets --asset-type PROJECT

# Process only PUBLISHED assets
python manage.py pull_and_clean_assets --status PUBLISHED

# Process only Spanish language assets
python manage.py pull_and_clean_assets --lang es

# Combine multiple filters
python manage.py pull_and_clean_assets --asset-type PROJECT --status PUBLISHED --lang en
```

### Rate Limiting and Batching

```bash
# Custom delay between API calls (default: 1.0 seconds)
python manage.py pull_and_clean_assets --delay 2.0

# Custom batch size (default: 10 assets per batch)
python manage.py pull_and_clean_assets --batch-size 5

# Process with 2 second delays and batches of 3
python manage.py pull_and_clean_assets --delay 2.0 --batch-size 3
```

### Testing and Debugging

```bash
# Dry run - show what would be processed without actually processing
python manage.py pull_and_clean_assets --dry-run

# Show help
python manage.py pull_and_clean_assets --help
```

## Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--all` | flag | False | Process all assets instead of just those needing updates |
| `--asset-type` | string | None | Filter by asset type (PROJECT, EXERCISE, LESSON, QUIZ, VIDEO) |
| `--status` | string | None | Filter by asset status (PUBLISHED, DRAFT, NOT_STARTED) |
| `--lang` | string | None | Filter by language (en, es, it) |
| `--delay` | float | 1.0 | Delay between API calls in seconds |
| `--batch-size` | integer | 10 | Number of assets to process in each batch |
| `--dry-run` | flag | False | Show what would be processed without processing |
| `--force` | flag | False | Force processing even if recently updated |

## How It Works

1. **Asset Selection**: The command identifies assets that need processing based on:
   - Must have a `readme_url` (GitHub URL)
   - Haven't been synced in the last 24 hours (unless `--all` or `--force` is used)
   - Match any specified filters (asset type, status, language)

2. **Batching**: Assets are processed in configurable batches to manage memory and provide progress feedback.

3. **Throttling**: A configurable delay is applied between each API call to respect GitHub's rate limits.

4. **Task Queuing**: For each asset, two Celery tasks are queued:
   - `async_pull_from_github.delay(asset_slug, user_id, override_meta)`
   - `async_regenerate_asset_readme.delay(asset_slug)`

5. **Progress Tracking**: The command provides real-time feedback on processing progress.

## Rate Limiting Considerations

- **Default Delay**: 1 second between API calls (configurable with `--delay`)
- **Batch Delays**: Additional delay between batches (2x the configured delay)
- **GitHub Limits**: GitHub's API allows 5,000 requests per hour for authenticated users
- **Recommended Settings**: 
  - For production: `--delay 1.0` (1 second)
  - For aggressive processing: `--delay 0.5` (0.5 seconds)
  - For conservative processing: `--delay 2.0` (2 seconds)

## Examples

### Production Usage
```bash
# Process assets with conservative rate limiting
python manage.py pull_and_clean_assets --delay 2.0 --batch-size 20
```

### Development/Testing
```bash
# Quick test with minimal assets
python manage.py pull_and_clean_assets --asset-type PROJECT --batch-size 3 --delay 0.5
```

### Emergency Sync
```bash
# Force sync all assets (use with caution)
python manage.py pull_and_clean_assets --all --force --delay 1.0
```

### Language-Specific Processing
```bash
# Process only Spanish assets
python manage.py pull_and_clean_assets --lang es --delay 1.5
```

## Error Handling

- Individual asset failures don't stop the entire process
- Errors are logged and displayed in the console
- Failed assets are reported but the command continues with remaining assets

## Monitoring

The command provides detailed output including:
- Number of assets found
- Progress updates every 5 assets
- Batch processing information
- Success/failure status for each asset
- Total processing time

## Dependencies

- Requires Celery workers to be running to process the queued tasks
- Assets must have valid GitHub URLs in the `readme_url` field
- Assets should have an `owner` user with GitHub credentials for authentication
