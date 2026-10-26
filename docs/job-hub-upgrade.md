# Kairos Job Hub upgrade notes

## Native discovery

The public `GET /api/v1/jobs` endpoint continues to serve only active, published, not-yet-expired opportunities from active employer organizations. It now supports the existing keyword, location, opportunity-kind, and workplace filters plus:

- `employment_type`: `FULL_TIME`, `PART_TIME`, `INTERNSHIP`, `CONTRACT`, or `TEMPORARY`.
- `sort_by`: `newest` (default) or `relevance`. Relevance prioritizes title and company-name matches, then publication freshness.
- `posted_within_days`: optional integer from 1 to 365, based on the native listing's `created_at` timestamp.

The UI exposes these filters and retains the selected filters in the URL so search results can be shared.

## Saved jobs

Student saved jobs are persisted in `saved_jobs` and scoped to the authenticated account:

- `GET /api/v1/students/saved-jobs`
- `POST /api/v1/students/saved-jobs/{opportunity_id}`
- `DELETE /api/v1/students/saved-jobs/{opportunity_id}`

The backend checks the student's actual Kairos role and permits saving only currently published opportunities from active, verified employer organizations. A database unique constraint prevents duplicate saves. The list omits listings that are no longer available; save records are removed when their account or opportunity is deleted.

## HiringCafe external discovery

The UI provides a clearly identified outbound link to [HiringCafe](https://hiringcafe.com/). Kairos does not claim to import HiringCafe listings or submit external applications. HiringCafe's official MCP documentation describes read-only search and detail tools and says heavy automated use is unsupported. Before adding server-side calls, confirm provider permission for this commercial use case and agree on a supported operational limit. Until then, native Kairos listings remain independent of the external site.

External links open in a new tab with `rel="noopener noreferrer"`. Native applications continue to use the existing Kairos application workflow.

## Migration and deployment

A new additive Alembic revision, `20261025_31`, creates the `saved_jobs` table and its unique/index constraints. It follows `20261025_30_preferences_account_key`. The older `20261022_13_institution_registration.py` revision had been fully commented out, which prevented Alembic from identifying the revision; its existing idempotent institution-field migration body has been restored so the revision graph can be traversed. No production database was accessed or modified during this repository change.

Apply the repository's normal migration process in a reviewed deployment window before enabling saved-job actions in a deployed environment. No new provider credentials or environment variables are required for the link-out fallback.

## Verification status

Repository-level source changes and API contract tests were added. GitHub Actions runs the repository's frontend build, registration-selector test, backend pytest suite, and isolated MySQL schema compatibility check on pushes to `release-v1`. ESLint is skipped by the existing workflow because the repository has no flat ESLint configuration. The final CI results are linked in the implementation report; the backend suite currently includes unrelated pre-existing schema/fixture failures, so a green backend suite is not claimed.


## HiringCafe provider boundary (October 2026)

Kairos keeps HiringCafe external discovery disabled until a production-suitable API/feed and written permission for multi-user SaaS use are available. The official [HiringCafe ChatGPT integration documentation](https://hiringcafe.com/documentation/hiringcafe-chatgpt-app) documents the Streamable HTTP MCP endpoint at `https://hiringcafe.com/api/chatgpt/mcp`, with read-only search and detail tools and no authentication. It also explicitly says heavy automated use is unsupported. That conversational MCP endpoint is therefore not called by Kairos's backend and must not be enabled as a general SaaS search API.

The provider boundary exposes status and validates the documented subset of search filters, but returns a stable `503 provider_unavailable` response for external search/detail requests while disabled. The Job Hub source selector distinguishes Kairos listings from HiringCafe and explains this disabled state; students may visit HiringCafe directly. No provider data is fabricated, cached, persisted, or mirrored. Native search, saved jobs, application records, and recruiter workflows remain independent.

To enable live listings, obtain HiringCafe's explicit permission and an API/feed contract intended for commercial multi-user use, including documented request/response schemas, usage limits, attribution, caching/retention rules, and detail/application URL semantics. Then implement and test that approved adapter. Do not set the provider enabled merely because the ChatGPT MCP endpoint is reachable.
