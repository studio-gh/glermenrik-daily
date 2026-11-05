# Customization Guide

The long-term goal is that a new user can create a personal Daily Brief without touching application code.

## What should be configurable

### Identity
- Brief name
- Small desk label
- Description
- Logo or text mark
- Favicon

### Editorial
- Rolling window size
- Timezone
- Sections
- Editorial territories
- Positive keywords
- Exclusion keywords
- Source priorities

### Visual
- Background
- Paper
- Text
- Accent
- Typography scale
- Density

### Support
- Buy Me a Coffee or another support URL
- Optional support button label

## Current repository

The current Creative Den is the reference instance. Its mature editorial logic lives in `scripts/` and its current source registry lives in `data/sources.json`.

`config/brief.example.json` is the proposed configuration contract for the reusable version.

Do not treat the example file as active configuration until the productization pass wires the engine and frontend to it.
