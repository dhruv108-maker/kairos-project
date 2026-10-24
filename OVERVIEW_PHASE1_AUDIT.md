# Kairos Overview — Phase 1 Product and API Audit

**Branch:** `release-branch`  
**Scope:** Shared workspace shell and the four role-specific overview experiences only.

## Source audit

The requested consolidated `kairos.md` was not present in the repository tree at the time of implementation. This audit therefore uses the existing README, route definitions, SQLAlchemy models, API routers/services, and current frontend as evidence. The product document should be added or its canonical path identified before later modules are designed.

## Role-to-screen matrix

| Workspace | Data evidenced in repository | Overview treatment | Known gap |
|---|---|---|---|
| Student | `GET /students/me/dashboard`; `GET /reports/requirements/me`; `GET /reports/me`; offer response endpoint `POST /students/applications/{application_id}/offers/{offer_id}/respond` | API-backed internship/application/report summary and report-requirement list, with loading and failure states | The current API does not provide a consolidated upcoming-deadlines/interviews feed. Review and report schema compatibility still needs live verification. |
| Faculty | `GET /faculty/me/dashboard`; evaluation read endpoints under `/evaluations` | API-backed supervision, pending-review, mentorship, and assessment counts; explains that no row-level assigned review queue was found | Current analytics service references stale `ReportSubmission.placement_id` and `.status` fields against the deployed report schema; fix and verify before relying on faculty counts. |
| Higher Authority | `GET /institutions/{institution_id}/dashboard`; institution report-requirement and recruitment-drive routes | Institution metrics only when authorized institution scope resolves; no fabricated compliance/deadline queue | Current account response does not include a selected institution. Dashboard service includes stale report joins and must be reconciled with the live schema. |
| Recruiter | Organization-scoped interview and offer routes under `/employers/organizations/{organization_id}/applications/{application_id}/...`; campus recruitment routes | Dedicated recruiter overview state explains which data source is missing rather than showing fake counts | No consolidated organization-scoped interview/offer feed and no organization context in the current `/auth/me` response. A recruiter listing must not query across organizations. |

## Shared shell and design decisions

- Retain the existing React, Vite, Tailwind, shadcn/ui, React Router, and authenticated API client.
- Use a near-white canvas, neutral borders, restrained primary accents, consistent cards, and responsive grids.
- Keep the existing sidebar and profile controls. The header now uses a route-aware breadcrumb/title and removes the template's global search and notifications controls from the shell because corresponding Kairos API behavior was not verified.
- Overview metrics are API-derived. Unavailable values use an em dash or a clear dependency message; the UI does not substitute sample counts.
- Session and endpoint errors are surfaced. A retry reloads the page, and existing authentication code clears expired tokens after 401 responses.

## Permission and product limitations

- Frontend role visibility is not authorization. Backend endpoints remain the authority for access control.
- The recruiter organization context and consolidated recruiter overview endpoint are missing from the frontend's known contracts.
- Faculty report queue data is not exposed as a dedicated listing in the inspected report router.
- The requested `kairos.md` source-of-truth document was not found; role naming beyond the explicit roles in account/API code remains provisional.
- No UI action is presented as a successful write unless a real supported endpoint is called.

## Verification status

- Repository and relevant routes/models/services inspected through GitHub on `release-branch`.
- Changes committed: role-aware overview page and header shell refinements.
- A local TypeScript/Vite build, browser accessibility pass, live API verification, and populated/empty/error-state end-to-end test were **not run** in this environment.
- Before production release, run `npm ci`, `npm run build`, `npm run lint`, and the relevant backend tests in the project environment; then verify each role with real test accounts and institution/employer scopes.

## Recommended next module

After resolving the documented API gaps and verifying the overview build, implement the **report submission and review workflow** next. It is shared by students, faculty, and institution administrators and currently has explicit report requirements, submission, version, submit, and review routes.
