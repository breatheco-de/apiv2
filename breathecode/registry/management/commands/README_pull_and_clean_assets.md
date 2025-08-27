# Registry Management Commands

This directory contains Django management commands for managing registry assets. There are two main commands for asset processing:

## 1. Pull and Clean Assets Command

This Django management command (`pull_and_clean_assets`) pulls assets from GitHub and cleans them asynchronously using Celery tasks, with built-in throttling to respect GitHub API rate limits.

### Overview

The command processes assets in batches and queues two Celery tasks for each asset:
1. `async_pull_from_github` - Pulls the latest content from GitHub
2. `async_regenerate_asset_readme` - Cleans and regenerates the README content

### Usage

#### Basic Usage

```bash
# Process assets that haven't been synced in the last 24 hours
python manage.py pull_and_clean_assets

# Process all assets (ignore last sync time)
python manage.py pull_and_clean_assets --all

# Force processing even for recently synced assets
python manage.py pull_and_clean_assets --force
```

#### Filtering Options

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

#### Rate Limiting and Batching

```bash
# Custom delay between API calls (default: 1.0 seconds)
python manage.py pull_and_clean_assets --delay 2.0

# Custom batch size (default: 10 assets per batch)
python manage.py pull_and_clean_assets --batch-size 5

# Process with 2 second delays and batches of 3
python manage.py pull_and_clean_assets --delay 2.0 --batch-size 3
```

#### Testing and Debugging

```bash
# Dry run - show what would be processed without actually processing
python manage.py pull_and_clean_assets --dry-run

# Show help
python manage.py pull_and_clean_assets --help
```

### Command Options

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

### How It Works

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

### Rate Limiting Considerations

- **Default Delay**: 1 second between API calls (configurable with `--delay`)
- **Batch Delays**: Additional delay between batches (2x the configured delay)
- **GitHub Limits**: GitHub's API allows 5,000 requests per hour for authenticated users
- **Recommended Settings**: 
  - For production: `--delay 1.0` (1 second)
  - For aggressive processing: `--delay 0.5` (0.5 seconds)
  - For conservative processing: `--delay 2.0` (2 seconds)

### Examples

#### Production Usage
```bash
# Process assets with conservative rate limiting
python manage.py pull_and_clean_assets --delay 2.0 --batch-size 20
```

#### Development/Testing
```bash
# Quick test with minimal assets
python manage.py pull_and_clean_assets --asset-type PROJECT --batch-size 3 --delay 0.5
```

#### Emergency Sync
```bash
# Force sync all assets (use with caution)
python manage.py pull_and_clean_assets --all --force --delay 1.0
```

#### Language-Specific Processing
```bash
# Process only Spanish assets
python manage.py pull_and_clean_assets --lang es --delay 1.5
```

### Error Handling

- Individual asset failures don't stop the entire process
- Errors are logged and displayed in the console
- Failed assets are reported but the command continues with remaining assets

### Monitoring

The command provides detailed output including:
- Number of assets found
- Progress updates every 5 assets
- Batch processing information
- Success/failure status for each asset
- Total processing time

### Dependencies

- Requires Celery workers to be running to process the queued tasks
- Assets must have valid GitHub URLs in the `readme_url` field
- Assets should have an `owner` user with GitHub credentials for authentication

---

## 2. Clean Assets Command

This Django management command (`clean_assets`) cleans assets asynchronously without pulling from GitHub. This command is useful when you only need to regenerate asset README content, clean formatting, and update metadata without fetching new content from external repositories.

### Overview

The command processes assets in batches and queues one Celery task for each asset:
1. `async_regenerate_asset_readme` - Regenerates and cleans asset README content

### Usage

#### Basic Usage

```bash
# Clean assets that haven't been cleaned in the last 24 hours
python manage.py clean_assets

# Clean all assets regardless of when they were last cleaned
python manage.py clean_assets --all

# Force processing even if recently cleaned
python manage.py clean_assets --force
```

#### Filtering Options

```bash
# Clean only PROJECT type assets
python manage.py clean_assets --asset-type PROJECT

# Clean only PUBLISHED assets
python manage.py clean_assets --status PUBLISHED

# Clean only English language assets
python manage.py clean_assets --lang en

# Combine multiple filters
python manage.py clean_assets --asset-type PROJECT --status PUBLISHED --lang en
```

#### Rate Limiting and Batching

```bash
# Custom delay between API calls (default: 2.0 seconds)
python manage.py clean_assets --delay 1.0

# Custom batch size (default: 10 assets per batch)
python manage.py clean_assets --batch-size 5

# Process with 1 second delays and batches of 3
python manage.py clean_assets --delay 1.0 --batch-size 3
```

#### Testing and Debugging

```bash
# Dry run - show what would be processed without actually processing
python manage.py clean_assets --dry-run

# Show help
python manage.py clean_assets --help
```

### Command Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--all` | flag | False | Process all assets instead of just those needing cleaning |
| `--asset-type` | string | None | Filter by asset type (PROJECT, EXERCISE, LESSON, QUIZ, VIDEO) |
| `--status` | string | None | Filter by asset status (PUBLISHED, DRAFT, NOT_STARTED) |
| `--lang` | string | None | Filter by language (en, es, it) |
| `--delay` | float | 2.0 | Delay between API calls in seconds |
| `--batch-size` | integer | 10 | Number of assets to process in each batch |
| `--dry-run` | flag | False | Show what would be processed without processing |
| `--force` | flag | False | Force processing even if recently cleaned |

### How It Works

1. **Asset Selection**: The command identifies assets that need cleaning based on:
   - Must have README content (`readme` field is not null or empty)
   - Haven't been cleaned in the last 24 hours (unless `--all` or `--force` is used)
   - Match any specified filters (asset type, status, language)

2. **Batching**: Assets are processed in configurable batches to manage memory and provide progress feedback.

3. **Throttling**: A configurable delay is applied between each API call to avoid overwhelming the system.

4. **Task Queuing**: For each asset, one Celery task is queued:
   - `async_regenerate_asset_readme.delay(asset_slug)`

5. **Progress Tracking**: The command provides real-time feedback on processing progress.

### Rate Limiting Considerations

- **Default Delay**: 2 seconds between API calls (configurable with `--delay`)
- **Batch Delays**: Additional delay between batches (2x the configured delay)
- **System Load**: Since this doesn't hit external APIs, the delay is mainly to prevent overwhelming the system
- **Recommended Settings**: 
  - For production: `--delay 2.0` (2 seconds)
  - For aggressive processing: `--delay 1.0` (1 second)
  - For conservative processing: `--delay 3.0` (3 seconds)

### Examples

#### Production Usage
```bash
# Clean assets with conservative rate limiting
python manage.py clean_assets --delay 3.0 --batch-size 20
```

#### Development/Testing
```bash
# Quick test with minimal assets
python manage.py clean_assets --asset-type PROJECT --batch-size 3 --delay 1.0
```

#### Force Clean All
```bash
# Force clean all assets (use with caution)
python manage.py clean_assets --all --force --delay 2.0
```

#### Language-Specific Cleaning
```bash
# Clean only Spanish assets
python manage.py clean_assets --lang es --delay 2.5
```

### Error Handling

- Individual asset failures don't stop the entire process
- Errors are logged and displayed in the console
- Failed assets are reported but the command continues with remaining assets

### Monitoring

The command provides detailed output including:
- Number of assets found
- Progress updates every 5 assets
- Batch processing information
- Success/failure status for each asset
- Total processing time

### Dependencies

- Requires Celery workers to be running to process the queued tasks
- Assets must have README content in the `readme` field
- No external API dependencies (unlike pull_and_clean_assets)

---

## When to Use Which Command

### Use `pull_and_clean_assets` when:
- You need to fetch the latest content from GitHub repositories
- Assets have GitHub URLs that need to be synced
- You want to update both content and formatting
- You have GitHub credentials configured

### Use `clean_assets` when:
- You only need to clean and format existing README content
- You don't need to fetch new content from external sources
- You want to regenerate metadata and formatting
- You want faster processing (no external API calls)
- You're working with assets that don't have GitHub URLs

### Performance Comparison

| Command | Speed | External Dependencies | Use Case |
|---------|-------|----------------------|----------|
| `pull_and_clean_assets` | Slower | GitHub API | Full sync with external content |
| `clean_assets` | Faster | None | Local content cleaning only |

---

## Other Available Commands

The registry app also provides several other specialized management commands:

### `generate_asset_context`
Generates asset context for all assets that don't have context yet.

```bash
python manage.py generate_asset_context
python manage.py generate_asset_context --all true
```

### `import_blog_registry`
Imports blog posts from the 4Geeks Academy blog repository.

```bash
python manage.py import_blog_registry
python manage.py import_blog_registry --override
```

### `create_asset_thumbnail`
Creates thumbnails for assets.

```bash
python manage.py create_asset_thumbnail
```

### `test_asset_integrity`
Tests the integrity of assets.

```bash
python manage.py test_asset_integrity
```

### `assign_asset_academy`
Assigns assets to academies.

```bash
python manage.py assign_asset_academy
```

For more detailed information about these commands, use the `--help` flag:

```bash
python manage.py [command_name] --help
```
