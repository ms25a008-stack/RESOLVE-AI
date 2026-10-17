# Verification — 17 October 2026

## Recovery

Recovered existing source from `/workspace/scratch/0508196cd27a/resolve-ai`, including frontend, backend, SQL and seed data. Continued the existing implementation. GitHub README was read successfully; no GitHub writes have been made. Delivery awaits user confirmation.

## Observed results

| Check | Result |
| --- | --- |
| FastAPI/domain/HTTP integration contract tests | 26 passed |
| React form and workflow tests (Vitest/jsdom) | 4 passed |
| Vite production build | Passed |
| Built frontend served by FastAPI TestClient | Passed |
| Synthetic dataset | 50 tickets, 20 documented resolved incidents, 6 resolver teams |
| Approval behavior | Pending analysis does not mutate the ticket; approval applies routing/category only; rejection leaves ticket unchanged |
| Duplicate and stale actions | Rejected; new analyses supersede prior pending analyses |
| Missing Gemini key / disabled free-tier acknowledgement | Explicit errors; no fabricated AI result |
| Gemini HTTP contract | Mocked success, schema validation, incomplete output, malformed output, provider error, quota response |
| Supabase HTTP contract | Mocked identity/membership checks, user-token requests, restricted service-role use, error mapping |
| Frontend workflows | Intake payload, failure retention, dashboard/queue/detail navigation, search, AI error display, Escape dismissal |
| Source packaging | Dependencies, build artifacts, runtime caches and real environment files excluded |

One upstream Starlette/AnyIO deprecation warning remains; it does not fail the tests.

## Fixes and delivery additions

- Added root pytest configuration so documented test commands work.
- Hardened SQL version checks against null versions and note validation against null input.
- Added dialog keyboard handling, accessible compact navigation labels, and periodic detail refresh.
- Added backend integration contract tests and frontend workflow tests.
- Added environment templates, Dockerfile, GitHub Actions workflow, setup/run instructions and explicit MVP limits.

## Not verified here

- No live Supabase/Gemini credentials were supplied or used. Real login, cloud persistence, model availability, quota and billing status remain unverified. HTTP mocks are not proof of live integration.
- SQL migration and RLS policies were reviewed but not executed against PostgreSQL/Supabase in this environment. They must pass the acceptance checks below before real operational data is used.
- Docker image build was not executed. The native Python/Node production build path passed.
- Full browser visual/end-to-end QA was not available through the required local preview tooling. React checks use jsdom, not a real rendered browser. Figma reference screens and the PDF were inspected.
- No hosting provisioned, billing enabled, or GitHub changes pushed. No actual API credentials are included.

## Live acceptance checks after configuration

1. Apply migration in a disposable Supabase project and optional seed. Create engineer and requester memberships.
2. Verify an unauthenticated API call gets 401; an authenticated non-member gets 403.
3. Create tickets as two requesters. Each must see only their own records/history and must fail attempts to read another ticket, review recommendations or change status, including direct Supabase RPC requests.
4. As an engineer, create a ticket, add a note, restart FastAPI, and verify persistence. Verify direct authenticated table updates are denied.
5. Enable an available Gemini model only on a verified unbilled project. Analyze a synthetic ticket; inspect citations and uncertainties. Confirm the ticket remains unchanged until approval.
6. Approve once, check routing/category and audit record; repeat the decision and confirm conflict. Reject another recommendation and verify no routing change. Verify a status change invalidates pending recommendations.
7. Resolve with documented verification; confirm timestamp and SLA result. Check the same data after restart.
8. In desktop and mobile browsers, check readable layout, keyboard navigation, intake, queue filtering, login/logout, and all error states.
