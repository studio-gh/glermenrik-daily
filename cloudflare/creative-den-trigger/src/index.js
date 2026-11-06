/**
 * Creative Den secure edition trigger.
 *
 * Deploy as a Cloudflare Worker and configure:
 *   GITHUB_TOKEN: fine-grained token with Actions: read/write on this repo
 *   ALLOWED_ORIGIN: https://studio-gh.github.io
 *
 * Routes:
 *   POST /trigger -> dispatches .github/workflows/daily.yml
 *   GET  /status?run_id=<id> -> returns the workflow run state
 */
const OWNER = "studio-gh";
const REPO = "glermenrik-daily";
const WORKFLOW = "daily.yml";
const API = "https://api.github.com";

function cors(origin, env) {
  const allowed = env.ALLOWED_ORIGIN || "https://studio-gh.github.io";
  if (origin && origin !== allowed) return {};
  return {
    "Access-Control-Allow-Origin": allowed,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin"
  };
}

function json(data, status, headers) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...headers }
  });
}

async function github(path, env, init = {}) {
  if (!env.GITHUB_TOKEN) throw new Error("Worker secret GITHUB_TOKEN is missing");
  const response = await fetch(API + path, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": "Bearer " + env.GITHUB_TOKEN,
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "CreativeDen-Edition-Trigger",
      ...(init.headers || {})
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error("GitHub API " + response.status + ": " + detail.slice(0, 400));
  }
  if (response.status === 204) return null;
  return response.json();
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const headers = cors(origin, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (origin && origin !== (env.ALLOWED_ORIGIN || "https://studio-gh.github.io")) {
      return json({ error: "Origin not allowed" }, 403, headers);
    }

    const url = new URL(request.url);
    try {
      if (request.method === "POST" && url.pathname === "/trigger") {
        const body = await request.json().catch(() => ({}));
        if (body.confirm !== "UPDATE_CREATIVE_DEN") return json({ error: "Invalid request" }, 400, headers);

        const before = await github(
          "/repos/" + OWNER + "/" + REPO + "/actions/workflows/" + WORKFLOW + "/runs?branch=main&per_page=1",
          env
        );
        const previousId = before.workflow_runs?.[0]?.id || 0;

        await github(
          "/repos/" + OWNER + "/" + REPO + "/actions/workflows/" + WORKFLOW + "/dispatches",
          env,
          { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ref: "main" }) }
        );

        // GitHub's dispatch endpoint is asynchronous and returns 204.
        // Resolve the newly-created run with a short bounded poll.
        for (let attempt = 0; attempt < 8; attempt++) {
          await new Promise(resolve => setTimeout(resolve, 1500));
          const latest = await github(
            "/repos/" + OWNER + "/" + REPO + "/actions/workflows/" + WORKFLOW + "/runs?branch=main&per_page=1",
            env
          );
          const run = latest.workflow_runs?.[0];
          if (run && run.id !== previousId && run.event === "workflow_dispatch") {
            return json({ ok: true, run_id: run.id, status: run.status, html_url: run.html_url }, 202, headers);
          }
        }
        return json({ ok: true, run_id: null, status: "queued", message: "Workflow dispatched; run is being registered." }, 202, headers);
      }

      if (request.method === "GET" && url.pathname === "/status") {
        const runId = url.searchParams.get("run_id");
        if (!runId || !/^\d+$/.test(runId)) return json({ error: "A valid run_id is required" }, 400, headers);
        const run = await github("/repos/" + OWNER + "/" + REPO + "/actions/runs/" + runId, env);
        return json({
          ok: true,
          status: run.status,
          conclusion: run.conclusion,
          updated_at: run.updated_at,
          html_url: run.html_url
        }, 200, headers);
      }

      return json({ error: "Not found" }, 404, headers);
    } catch (error) {
      return json({ error: error.message || "Unexpected error" }, 502, headers);
    }
  }
};
