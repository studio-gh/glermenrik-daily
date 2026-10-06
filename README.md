# Glermenrik Daily

A living visual culture desk for Glermenrik.

## Architecture
The frontend is a static GitHub Pages site. GitHub Actions is the daily ingestion engine. It reads the source registry, fetches RSS/Atom feeds, normalizes and deduplicates items, and writes `data/articles.json`.

## Run
The workflow runs daily and can also be triggered manually from GitHub Actions.

## Pages
Enable Settings → Pages → Source: GitHub Actions.

## No fabrication
The system only displays material returned by configured feeds. A failed source is logged and does not generate invented content.
