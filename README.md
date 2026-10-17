# ResolveAI

AI-assisted IT service management: incident context, historical solutions, resolver recommendations, SLA tracking, and explicit engineer approval.

Recovered and completed from the original workspace. React + Vite frontend; Python FastAPI backend; Supabase Auth/Postgres persistence; server-side Gemini REST integration. No hosting is provisioned by this repository.

## What works

- Dashboard: active/critical incidents, SLA risks, average resolution time, category mix.
- Searchable ticket queue, ticket creation, detail view, investigation notes, status changes, and documented closure/reopening.
- 50 fictional incidents across six categories, including 20 resolved incidents and six resolver teams.
- Historical retrieval using explicit keyword overlap; resolver ranking using category, skill terms, and configured team workload. These are rules, not AI or confidence scores.
- Gemini structured analysis: tentative assessment, hypotheses, steps, source references, uncertainties, proposed category/priority.
- Engineer approval or rejection with audit history. Approval applies category and resolver only; suggested priority remains advisory. No commands execute and no ticket closes automatically.
- Supabase membership roles (requester, engineer, admin), row-level security, transactional writes, optimistic version checks, and immutable application audit records.
- Responsive layouts, keyboard-accessible forms, clear errors, and a visibly labeled local demo.

## Run locally without accounts or API charges

Prerequisites: Python 3.12 and Node 22. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd frontend
npm ci
npm run build
cd ..
DEMO_MODE=true python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-proxy-headers
```

Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs.

PowerShell: activate with `.venv\Scripts\Activate.ps1`, then set `$env:DEMO_MODE="true"` before running the same Python command without the `DEMO_MODE=true` prefix.

Demo mode has no login, runs only on loopback, and resets changes on server restart. It shifts sample dates to the current time so SLA examples remain useful. It does **not** fabricate Gemini output: Analyze reports a configuration error until a real key and the free-tier confirmation flag are supplied. Never put demo mode behind a public reverse proxy or use it with real incidents.

For frontend development, run `npm run dev` inside `frontend` in a second terminal; Vite proxies `/api` to port 8000. For normal combined serving, rebuild the frontend before starting FastAPI.

## Connect Supabase for persistent operation

Use a project on a plan you have verified incurs no charges. No paid hosting is needed to run the app on your computer.

1. Execute `supabase/migrations/001_initial.sql` once in a fresh project's SQL editor. It creates tables, grants, RLS policies and write functions in a transaction. This initial migration is not meant to be rerun over existing tables.
2. Optionally execute `supabase/seed.sql`. It adds the 50 fictional incidents and teams idempotently, without overwriting existing rows. SQL sample timestamps are fixed; older active samples will correctly appear breached. Do not load these into a real operational dataset.
3. Create a user using Supabase Authentication administration. Add membership in the SQL editor, using the actual Auth user UUID:

```sql
insert into public.members(user_id, role)
values ('REPLACE_WITH_AUTH_USER_UUID'::uuid, 'engineer');
```

Use `requester` for end users (only their own tickets and history) and `admin` for administrators. There is no automatic membership on registration. All engineers/admins share one workspace; multi-tenancy is not implemented. User provisioning remains in Supabase administration.

4. Copy `backend/.env.example` to `backend/.env`. Set `DEMO_MODE=false`, the Supabase project URL, legacy public `anon` JWT key, and legacy `service_role` JWT key. This adapter explicitly expects the legacy JWT key pair, not the newer secret key format. Keep service-role and Gemini keys exclusively in the backend environment.
5. Copy `frontend/.env.example` to `frontend/.env.local`. Set the same Supabase URL and **public anon key only**. Rebuild with `npm run build` from `frontend`.
6. Start from `backend` so the settings loader finds `backend/.env`:

```bash
cd backend
../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

On Windows use `..\.venv\Scripts\python.exe`. Remove any old `DEMO_MODE=true` shell variable first; environment variables override dotenv values. Sign in with the provisioned account. Data now persists in Supabase.

The browser uses the public anon key for login. FastAPI verifies the session with Supabase Auth on every protected request; normal database reads/writes use that user's token and RLS. Only saving validated AI recommendations uses the backend service-role key after verifying engineer membership. Requesters cannot approve recommendations or change status.

## Enable Gemini

Set `GEMINI_API_KEY` in `backend/.env`, select a model available to your project using `GEMINI_MODEL`, and set `GEMINI_FREE_TIER_CONFIRMED=true` **only after you verify the project's billing/tier settings**. The default model is `gemini-2.5-flash`; availability and free quotas depend on your account. This flag is an operator acknowledgement, not a billing API check. Do not enable billing to bypass a quota error.

Gemini receives the selected ticket's title, description, category and priority, plus up to five matching resolved incidents and their solutions. Avoid secrets and personal information in tickets; obtain the appropriate organizational approval before using real support data. A synthetic demo dataset is supplied for this reason.

The app limits analysis attempts to three per user per minute and two concurrent Gemini requests per process. HTTP 429 and malformed, incomplete or uncited output produce explicit errors; there is no paid fallback. Validate advice manually: source-ID validation is not proof of claim accuracy, and prompt-injection defenses are not a guarantee. AI has no tool or command execution capability.

## Build and container delivery

The Dockerfile builds React and serves it with FastAPI as one service:

```bash
docker build --build-arg VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co --build-arg VITE_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY -t resolve-ai .
docker run --rm -p 127.0.0.1:8000:8000 --env-file backend/.env resolve-ai
```

Only the public browser configuration goes into build arguments. Supply backend secrets at runtime. Docker mode is intended for `DEMO_MODE=false`; loopback-only demo checks reject normal Docker bridge clients. No cloud deployment has been created. If later hosted, use HTTPS, one worker, explicit trusted proxy settings, the correct `FRONTEND_ORIGIN`, and verify the chosen platform has no charges. Do not expose demo mode.

## Tests

From the repository root:

```bash
python -m pytest -q
cd frontend
npm test -- --maxWorkers=2
npm run build
```

`pytest.ini` provides the backend import path. `.github/workflows/tests.yml` repeats the tests and build on GitHub after delivery. Tests use synthetic data and mocked cloud responses; no secrets or paid calls are required.

See `VERIFICATION.md` for observed results and unverified integration limits.

## Architecture and MVP boundaries

`frontend/src/main.jsx` holds the UI; `api.js` adds the authenticated bearer token. `backend/app/main.py` exposes the API; `domain.py` implements SLA/retrieval/scoring rules; `ai.py` validates Gemini output; `store.py` selects Supabase or the explicit demo store. SQL functions keep decisions and state changes atomic. `scripts/generate_seed.py` reproducibly generates JSON and SQL samples.

SLA budgets: P1 4h, P2 8h, P3 24h, P4 72h; waiting does not pause the clock. Risk is at most 60 minutes remaining or at least 75% elapsed; an expired deadline is breached. Resolver score: category 60 + matching skill terms up to 20 + spare configured capacity up to 20. Team capacity is not live shift/individual availability.

The PDF's human-in-the-loop intelligence layer and Figma dashboard/queue/detail/historical/planner concepts are implemented as a focused MVP. The planner and assistant are consolidated into ticket detail. Jira/ServiceNow ingestion, individual agent calendars, major-incident bridges, external notifications, autonomous remediation, vector search, enterprise SSO, and comprehensive product analytics are future work, not simulated integrations. The Figma prototype is a design reference rather than a pixel-exact implementation.

This is a single-workspace, small-volume prototype. Queries page through up to 10,000 visible records per table, then fail explicitly; production scale needs filtered server-side queries. Rate limiting is per process, so use one worker until adding a shared limiter. Health reports configuration, not cloud connectivity. Credentials, account configuration, and actual cloud persistence must be verified before operational use.

## References

- Project: supplied `ResolveAI_Intelligence_Layer(1).pdf`
- Prototype: https://vector-slogan-49213530.figma.site/
- Gemini structured output: https://ai.google.dev/gemini-api/docs/structured-output
- Supabase RLS: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase keys: https://supabase.com/docs/guides/getting-started/api-keys
