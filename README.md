# Daily Brief Engine

A free, GitHub-native engine for building a personalized daily brief from sources you choose.

The repository currently contains the **Creative Den reference instance**, a visual culture brief created by Studio GH.

## What it does

- Collects RSS, Atom and selected HTML sources.
- Normalizes and deduplicates references.
- Scores content for freshness and editorial relevance.
- Uses a rolling 7-day window.
- Builds an editorial edition automatically.
- Preserves previous editions in `data/history/`.
- Publishes the static site through GitHub Pages.
- Runs the ingestion pipeline through GitHub Actions.
- Keeps source failures isolated and visible.
- Never invents content when a source fails.

## Current reference instance

**Creative Den**  
https://studio-gh.github.io/glermenrik-daily/

It is designed around graphic design, web, branding, typography, print, packaging, visual culture and creative tools, with additional discovery rooms for Muzli and Cosmos.

## Repository map

```
.github/workflows/
  daily.yml        Daily ingestion + edition build + Pages deploy
  pages.yml        Static site deployment for shell/config changes

config/
  brief.example.json  Proposed reusable configuration contract

data/
  sources.json      Source registry
  articles.json     Normalized content pool
  daily.json        Current edition
  history/          Historical editions

scripts/
  fetch_feeds.py    Source ingestion and normalization
  build_edition.py  Editorial scoring and edition construction

docs/
  ARCHITECTURE.md
  CUSTOMIZATION.md
  PRODUCTIZATION.md
```

## Automation

The engine checks several times per day and skips duplicate refreshes when today's edition already exists. This makes the schedule more tolerant of GitHub Actions scheduling delays.

## Pages setup

For a new instance, GitHub Pages should be configured to use **GitHub Actions**.

## Productization status

This repository is still the mature **reference implementation**, not yet the final one-click template.

The next productization pass should move personal configuration out of the engine and into a single editable config file, then provide a non-developer onboarding flow.

## License

Choose the final open-source license during productization. Do not assume a license on behalf of future contributors.
