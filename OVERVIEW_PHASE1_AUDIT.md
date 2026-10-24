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

## Semester-wise academic performance — data audit and component

### Data audit findings

- `StudentProfile.cgpa` is a nullable `Numeric(4, 2)` field representing current CGPA. The schema does not document it as a semester-by-semester history and it must not be plotted as SGPA.
- `StudentAcademicRecord` stores `semester` as optional text, `grade_value`, `grade_max`, and `grading_scale`, linked to a student profile. These are general academic-record fields; the inspected model does not define the value as SGPA or define a canonical semester-result record.
- `GET /students/me/dashboard` returns dashboard, portfolio, internship and report aggregates, not semester grades.
- `GET /institutions/{institution_id}/students` and student detail routes expose institution-admin student context, including current CGPA, but no authorized semester-grade-history endpoint.
- `GET /faculty/me/dashboard` and `GET /institutions/{institution_id}/dashboard` return operational counts, not semester-level academic aggregates.
- The existing mentorship service supports institution-admin-managed faculty/student mentorship records. No faculty-authorized mentee grade-history endpoint or cohort/department/school semester aggregation endpoint was found.
- `PLATFORM_ADMIN` and `INSTITUTION_ADMIN` must remain distinct. The inspected institution dashboard uses `InstitutionService.require_admin(institution_id, account_id)`; there is no verified platform-admin cross-institution academic aggregate endpoint.

### Implemented in this pass

- Added `src/views/dashboards/modern/SemesterPerformanceChart.tsx` as a **reusable, typed presentation component** using the existing shadcn `ChartContainer`, `ChartConfig`, `ChartTooltip`, `ChartTooltipContent`, card primitives, Recharts `AreaChart`, `Area`, `CartesianGrid`, `XAxis`, and `YAxis`.
- The component accepts typed data and state through props; it has loading, populated, empty, error/retry, partial-data, stable gradient ID, and sample-count-ready point fields. It does not fetch data or embed example grades.
- Latest-versus-previous change is shown only when both values exist and both points explicitly declare the same metric scale.
- The chart is intentionally **not mounted into role dashboards yet**. The earlier proposed `/analytics/semester-performance` URL was not an existing backend contract and has been removed from the component/dashboard integration. This avoids a guaranteed failing request and prevents UI controls from implying permissions the API does not enforce.

### Required API contract before role integration

- Student: authenticated self-only semester result history; no student ID accepted from the client.
- Faculty: authorized individual-student result history, faculty-assigned mentee aggregate, assigned cohort/batch aggregate, and explicitly permitted department/school aggregate. Server must verify faculty/student/cohort/organization relationships for every request.
- Institution administrator: aggregates only within the institution for which `require_admin` succeeds, with school/department/cohort filtering validated server-side.
- Platform administrator: separate explicit platform-admin authorization and aggregate-only cross-institution responses; no implicit reuse of institution-admin permissions.
- Response must define the actual metric, scale/grade system, semester identity/label, valid sample count, and null/missing-result semantics. Group averages must exclude missing values and must not combine incompatible grading scales.
- Until those endpoints and tests exist, the role-specific views and live selectors are **not complete**. Do not infer SGPA from CGPA or present generic `grade_value` records as semester results without a documented semantic contract.

### Verification status

- Relevant models, route registration, routers, services, and UI chart primitives inspected on `release-branch`.
- No local TypeScript/Vite build, lint, backend tests, live API tests, or browser permission tests were run in this environment. The chart component and docs are committed, but the end-to-end academic analytics feature is not complete.

## Recommended next module

After resolving the documented API gaps and verifying the overview build, implement the **report submission and review workflow** next. It is shared by students, faculty, and institution administrators and currently has explicit report requirements, submission, version, submit, and review routes.
