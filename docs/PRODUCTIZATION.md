# From Creative Den to Daily Brief

## Goal

Turn this reference implementation into a reusable, free-to-host product where someone can create their own personalized daily brief with minimal technical work.

## Desired onboarding

1. Fork or use the template repository.
2. Open one configuration file.
3. Enter the brief name, timezone and optional support link.
4. Choose or add sources.
5. Commit.
6. GitHub Actions builds the first edition.
7. GitHub Pages publishes the brief automatically.

## Product requirements

- Zero paid infrastructure required.
- GitHub Pages for hosting.
- GitHub Actions for scheduled ingestion.
- No backend required for the core experience.
- Source registry stored as editable data.
- Rolling editorial window, configurable per instance.
- Clear edition timestamp and window on the frontend.
- Automatic deduplication.
- Graceful source failures.
- No fabricated content.
- Mobile-friendly static frontend.
- Optional support button.
- Documentation written for non-developers.

## Recommended future structure

```
/
├── app/
│   └── index.html
├── config/
│   ├── brief.json
│   └── sources.json
├── engine/
│   ├── fetch.py
│   ├── normalize.py
│   ├── editorial.py
│   └── build.py
├── data/
│   ├── articles.json
│   ├── daily.json
│   └── history/
├── docs/
├── .github/
│   └── workflows/
└── README.md
```

The productization prompt in the project conversation should be used to perform this refactor as one coherent pass rather than piecemeal edits.
