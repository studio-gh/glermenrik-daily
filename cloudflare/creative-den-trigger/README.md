# Creative Den Trigger (Cloudflare Worker)

This Worker keeps the GitHub credential off the public Creative Den website.

## One-time setup

1. In Cloudflare, open **Workers & Pages** and create a Worker named `creative-den-trigger`.
2. Open its editor and replace the starter code with `src/index.js` from this folder, then Deploy.
3. In the Worker settings, add these secrets/variables:
   - Secret `GITHUB_TOKEN`: a fine-grained GitHub token scoped only to `studio-gh/glermenrik-daily`, with **Actions: Read and write** and **Contents: Read-only**.
   - Variable `ALLOWED_ORIGIN`: `https://studio-gh.github.io`.
4. Copy the Worker URL. The website will use that URL as its update API endpoint.

## API

- `POST /trigger` with JSON body `{"confirm":"UPDATE_CREATIVE_DEN"}`
- `GET /status?run_id=<workflow-run-id>`

The Worker dispatches `.github/workflows/daily.yml` on `main`, then reports the run state. GitHub credentials are never sent to the browser.

## Security notes

- Do not put the GitHub token in `index.html`, repository files, or browser storage.
- Keep the token scoped to this repository only.
- If the token is revoked or rotated, update the Worker secret, not the website.
