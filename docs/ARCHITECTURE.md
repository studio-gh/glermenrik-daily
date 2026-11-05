# Creative Den Engine Architecture

Creative Den is a static editorial frontend plus a small Python ingestion/build pipeline.

## Current flow

1. `data/sources.json` defines the source registry.
2. `scripts/fetch_feeds.py` fetches RSS, Atom and selected HTML sources.
3. The fetcher normalizes titles, links, images, categories and source metadata.
4. `scripts/build_edition.py` applies the rolling 7-day window and editorial filters.
5. `data/articles.json` stores the normalized reference pool.
6. `data/daily.json` stores the current editorial edition.
7. `data/history/YYYY-MM-DD.json` preserves each edition.
8. GitHub Pages serves the static site.
9. GitHub Actions runs the ingestion and publication pipeline.

## Productization target

The public project should separate three layers:

### Engine
Reusable Python logic for ingestion, scoring, filtering and edition generation.

### Instance configuration
A single small config file should control the user's name, title, timezone, window, visual theme, editorial territories, support link and section labels.

### Content registry
Sources should remain data, not code. A user should be able to add, remove or reorder sources without editing Python.

## Principle

The engine should never contain personal brand names, personal links, private credentials or personal editorial assumptions.

The site should fail gracefully when a source is unavailable and should never fabricate missing content.
