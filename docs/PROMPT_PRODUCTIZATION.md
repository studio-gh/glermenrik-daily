# Master Prompt: Turn Daily Brief Engine into a Reusable Product

You are an expert product engineer, UX designer and GitHub Actions engineer.

You are working on the repository `studio-gh/glermenrik-daily`, which currently contains a mature reference implementation called Creative Den.

## Primary goal

Transform the current reference implementation into a reusable, free-to-host **Daily Brief Engine** that lets a non-developer create their own personalized daily brief with as little friction as possible.

Do not rebuild the editorial engine from scratch. Preserve the strongest parts of the current implementation and refactor them into a clean reusable architecture.

The final product should allow someone to:

1. Fork or use the repository as a template.
2. Open one configuration file or a very small setup UI.
3. Set the brief name, description, timezone, visual theme and optional support link.
4. Choose from built-in source presets or add their own RSS/Atom/HTML source.
5. Commit the configuration.
6. Have GitHub Actions collect the sources automatically.
7. Generate a rolling daily editorial edition.
8. Publish the result automatically to GitHub Pages.
9. See a clear edition date, generation timestamp and covered window.
10. Never need paid hosting, a database or a server for the core product.

## Non-negotiable constraints

- Keep the core stack static HTML/CSS/JavaScript + Python.
- Use GitHub Actions for automation.
- Use GitHub Pages for hosting.
- No paid infrastructure.
- No mandatory backend.
- No API keys for the core source ingestion flow.
- Never fabricate source content.
- Never silently discard a source failure. Surface source health clearly.
- Keep source configuration as data, not Python code.
- Keep personal Creative Den identity and links out of the reusable engine.
- Preserve the current Creative Den reference instance as a working example.
- Do not expose or commit secrets.
- Do not break the current published Creative Den while refactoring.

## Product architecture

Refactor toward this structure:

```
/
├── app/
│   ├── index.html
│   ├── assets/
│   └── ...
├── config/
│   ├── brief.json
│   ├── sources.json
│   └── presets/
│       ├── design.json
│       ├── tech.json
│       ├── culture.json
│       ├── marketing.json
│       └── custom.json
├── engine/
│   ├── fetch.py
│   ├── normalize.py
│   ├── classify.py
│   ├── editorial.py
│   └── build.py
├── data/
│   ├── articles.json
│   ├── daily.json
│   └── history/
├── docs/
├── tests/
├── .github/
│   └── workflows/
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

You may adjust the structure when there is a strong technical reason, but keep the separation between:

- reusable engine
- instance configuration
- source registry
- generated data
- frontend
- documentation

## Configuration contract

Create one authoritative `config/brief.json`.

It should control at minimum:

```json
{
  "name": "My Daily Brief",
  "deskLabel": "Daily Intelligence Desk",
  "description": "A personalized editorial brief.",
  "timezone": "America/Sao_Paulo",
  "windowDays": 7,
  "locale": "en-US",
  "theme": {
    "background": "#102B46",
    "paper": "#EFE8DA",
    "text": "#132235",
    "accent": "#FF961A"
  },
  "branding": {
    "logo": "",
    "favicon": ""
  },
  "editorial": {
    "sections": [
      "EDITOR'S CUT",
      "SIGNALS",
      "DESIGN",
      "VISUAL FEAST",
      "TOOL WATCH",
      "AI IMPACT",
      "WILD"
    ],
    "positiveKeywords": [],
    "negativeKeywords": [],
    "focusAreas": []
  },
  "support": {
    "enabled": false,
    "label": "☕ Buy me a coffee",
    "url": ""
  }
}
```

The frontend and engine must actually read this file. Do not create a decorative config that is ignored by the application.

## Source registry

Create a clean `config/sources.json` schema.

Each source should support:

- name
- url
- feed
- mode
- kind
- role
- priority
- territories
- designScope
- designFocus
- accessPolicy
- enabled

Example:

```json
{
  "name": "Example Source",
  "url": "https://example.com/",
  "feed": "https://example.com/feed.xml",
  "mode": "rss",
  "kind": "culture",
  "role": "editorial",
  "priority": 5,
  "territories": ["DESIGN"],
  "designScope": "graphic",
  "designFocus": ["DESIGN", "TYPE"],
  "accessPolicy": "free",
  "enabled": true
}
```

A user should be able to disable a source with one boolean.

Create a small set of source presets that make onboarding easy.

## Editorial engine

Preserve the current engine's strengths:

- rolling window
- timezone-aware edition date
- source diversity
- source priority
- recency scoring
- image preference
- graphic-design filtering
- negative topic filtering
- paywall/access filtering
- duplicate prevention
- historical editions
- source health

Make all editorial rules configurable where practical.

Do not hardcode Creative Den-specific source names or categories inside the engine.

The reusable engine should still support specialized briefs such as:

- design
- creative culture
- technology
- marketing
- productivity
- news
- personal research
- custom mixed brief

## Reliable scheduling

The current project has already experienced delayed scheduled workflows.

Build a resilient scheduler:

- run several times per day
- calculate today's edition in the configured timezone
- skip execution when today's edition already exists
- prevent concurrent edition builds
- do not publish two different editions for the same date
- make a missed schedule recover automatically
- make manual catch-up possible through `workflow_dispatch`

Use GitHub Actions concurrency groups correctly.

## Frontend

The frontend should remain editorial and visual, but become generic.

Requirements:

- responsive
- mobile-first
- static
- no build step required for the final site
- clear edition date
- generation timestamp
- exact rolling-window dates
- source health indicator
- search
- saved library
- section navigation
- optional discovery links
- optional support button
- graceful empty states
- graceful loading and error states

The current Creative Den visual language can remain the reference theme, but it must be possible to replace the theme through config.

Do not remove the current Creative Den design quality just to make the project generic.

## Setup experience

The main product problem to solve is onboarding.

Build the simplest possible path for a non-developer.

Preferred approach:

### Option A: setup page

Create `/setup/` or a lightweight setup screen that lets the user:

- name their brief
- choose timezone
- choose a preset
- add/remove sources
- choose colors
- optionally add Buy Me a Coffee
- generate the configuration
- explain exactly what to commit

If a setup UI makes the project meaningfully more complicated, create an extremely clear one-file setup instead.

Do not create a fake wizard that still requires manual code editing in five places.

## Documentation

Rewrite the README for someone who has never seen the repository.

It should answer:

- What is this?
- What does it cost?
- How do I create my own?
- Where do I edit my sources?
- How does the daily update work?
- How do I troubleshoot a failed edition?
- How do I publish on GitHub Pages?
- What is safe to customize?
- What files are generated automatically?

Add:

- `docs/QUICKSTART.md`
- `docs/CONFIGURATION.md`
- `docs/SOURCES.md`
- `docs/ARCHITECTURE.md`
- `docs/TROUBLESHOOTING.md`

## Testing

Add automated checks for:

1. valid configuration
2. invalid configuration
3. source registry validation
4. date/window calculation
5. timezone conversion
6. duplicate removal
7. blocked source filtering
8. editorial scoring
9. same-day duplicate run prevention

Add a simple smoke test that builds an edition from fixture data without accessing the internet.

## GitHub hygiene

Clean the repository.

Remove:

- temporary files
- obsolete workflows
- duplicated deployment logic
- personal-only comments
- unused code
- stale docs
- accidental debug files

Keep:

- one authoritative engine workflow
- one Pages deployment workflow only when necessary
- clear commit history going forward
- concise README
- docs
- config examples
- tests

Do not delete historical generated editions.

## Reference instance preservation

The current Creative Den should remain functional and recognizable.

Before changing the architecture:

- identify the current working behavior
- preserve the current public URL
- preserve the current Creative Den configuration
- preserve current data history
- preserve current visual identity
- preserve Muzli and Cosmos discovery room links
- preserve the support button behavior
- preserve favicon behavior

Move Creative Den-specific values into instance configuration rather than deleting them.

## Deliverables

When finished, the repository should provide:

### A. A working Creative Den reference instance

It should behave exactly as a valid instance of the reusable engine.

### B. A reusable Daily Brief template

A person can fork it, configure it and publish a personal brief.

### C. Documentation

A non-developer should be able to follow the instructions without guessing.

### D. Tests

The core logic should be covered by deterministic tests.

### E. Product-ready GitHub repository

The repository should look like an intentional open-source project, not a personal prototype.

## Working method

Work incrementally but commit coherent changes.

Before editing:

1. inspect the repository
2. inspect workflow history
3. inspect current generated data
4. identify personal vs reusable logic
5. identify duplicated or obsolete deployment paths

Then:

1. create/refactor configuration
2. refactor engine
3. refactor frontend
4. harden scheduling
5. add tests
6. rewrite documentation
7. run the full smoke test
8. verify the Creative Den reference instance
9. verify GitHub Pages deployment
10. report exactly what changed

Do not claim success without verifying the generated edition and the GitHub Actions deployment.

## Acceptance test

The project is successful only when all of these are true:

- I can fork the repo.
- I can configure a new brief without editing Python.
- I can choose or add sources without editing Python.
- I can publish it on GitHub Pages for free.
- The brief updates automatically.
- A missed scheduled run is recovered.
- Two runs cannot publish conflicting editions for the same date.
- The frontend clearly states what edition and 7-day window the reader is seeing.
- Source failures do not crash the whole edition.
- The current Creative Den still works as a reference instance.

Start by auditing the current repository and then implement the transformation. Do not ask unnecessary questions. Make the smallest coherent set of changes that achieves the architecture above.
