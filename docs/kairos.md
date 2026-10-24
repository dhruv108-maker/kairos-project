# KAIROS — Product, Roles, Features, Workflows & Architecture Guide

> **Purpose:** This is the consolidated product and workflow reference for Kairos. It brings together the supplied module documents into one guide covering user journeys, role responsibilities, major features, API workflows, data boundaries, integrations, and known limitations.
>
> **Source and status rule:** This document describes behavior reported by the supplied Kairos module documents. It does not prove that every feature is deployed, that every migration has been applied, that every UI is complete, or that production has been verified. Where the source documents identify a limitation, it is preserved here rather than silently filled with assumptions.

---

## 1. Product overview

Kairos is an academic and career workflow platform intended to connect students, faculty, academic institutions, platform operators, and employers through institution-aware academic records and career opportunities.

The documented product areas include:

- Authentication, account verification, password reset, and profile management.
- Institution onboarding and institution-scoped academic administration.
- Academic hierarchy management: schools, departments, programmes, academic years, and cohorts.
- Student and faculty dashboards.
- Student academic profile, portfolio, CV/resume, and academic context.
- Internship opportunities, applications, placements, reports, and evaluations.
- Faculty mentorship and assessment assignments.
- Campus recruitment drives and employer participation.
- Employer organization onboarding, job listings, and recruiter pipelines.
- Workflow email notifications.
- Audit events for selected sensitive operations.
- An external Griffin evaluation integration boundary.
- Optional identity verification, currently unavailable for live Aadhaar verification through the documented provider.

Kairos is built around a canonical account identity with role/profile records and domain-specific academic and career data. The frontend is documented as React + Vite + Shadcn UI + Tailwind CSS. The backend is FastAPI with SQLAlchemy 2.x and Alembic, and the intended primary database is MySQL 8-compatible or TiDB-compatible. Resend is the documented transactional email provider. Griffin is an external service boundary and must remain isolated from Kairos's database.

## 2. Important interpretation of this document

### 2.1 Implemented, partial, and future behavior

The source documents describe a mixture of implemented API behavior, architecture plans, current limitations, and future work. Do not interpret a feature's appearance in this guide as proof that it is fully operational in production.

Use these distinctions when planning or reporting work:

- **Documented behavior:** A supplied module document describes the route or behavior.
- **Partial / limited:** The source explicitly records a constraint, missing workflow, or incomplete integration.
- **Requires verification:** Runtime behavior, deployed schema, migration ancestry, UI integration, provider configuration, or CI results must be checked.
- **Future work:** The source says the capability is not currently implemented or needs a further contract/schema/design.

### 2.2 API prefixes

Most documented API routes use `/api/v1`. Some module documents describe legacy routes while the modularization guide describes newer opt-in module routes. Inspect the actual router registration before relying on a path. Preserve legacy URLs and payload/status semantics when refactoring unless a reviewed API migration explicitly changes them.

### 2.3 Source documents contain schema and migration caveats

The supplied documents explicitly warn that the checked-in DDL, newer ORM/model expectations, and deployed database may not always match. Before applying a migration or changing an ORM query:

1. Inspect the actual model and migration files.
2. Inspect the deployed schema and `alembic_version` only through authorized, reviewed access.
3. Confirm migration ancestry and the expected starting schema.
4. Test upgrades against an isolated MySQL-compatible database.
5. Preserve existing records and relationships.
6. Never claim production migration or runtime verification without evidence.

---

## 3. Roles and access model

Kairos contains several distinct role scopes. These must not be collapsed into one global role check.

### 3.1 Student

A student account is created through the student registration flow. The server assigns the `STUDENT` role. The student profile includes an enrollment number and cohort relation. Student access should be limited to the student's own profile, academic context, portfolio, submissions, applications, and other authorized records.

Typical capabilities documented in the source modules:

- Register and verify institutional email.
- Sign in after account verification and active-account checks.
- Read and update permitted fields in their own profile.
- Retrieve academic context derived from their cohort.
- Manage supported academic portfolio and resume data.
- Browse internships and eligible campus recruitment drives.
- Apply for opportunities, view their own applications, and withdraw where allowed.
- View placement/report/evaluation states and feedback where the relevant workflow supports it.
- View their own dashboard and academic history derived from persisted records.

A student must not assign their own role, change official academic placement through ordinary profile editing, verify their own academic records, or submit another student's identity to access restricted records.

### 3.2 Faculty

Faculty registration creates a `FACULTY` role but starts with an inactive and unverified account under the documented onboarding policy. Email verification alone does not activate a faculty account; institutional approval is required.

Documented capabilities, subject to role and resource authorization:

- Maintain permitted basic profile fields and view the currently modelled department affiliation.
- View a faculty dashboard with supervised placements, reports pending review, active mentorships, and pending assessment assignments.
- Review reports for placements they supervise.
- Initiate or inspect Griffin evaluation records only when assigned as the placement supervisor.
- Manage assessment assignments assigned to them.
- Publish internship opportunities where the relevant legacy route permits faculty.
- Participate in student mentorship through institution-scoped administration workflows.
- Access only the students, courses, submissions, and records allowed by their actual institutional assignments and permissions.

**Known limitation:** the supplied academic-administration document states that a dedicated teaching-assignment model does not exist in that stage. Do not assume that full course-level teaching assignments are supported. The current faculty affiliation endpoint exposes the primary department and documents a schema limitation.

### 3.3 Institution administrator (`INSTITUTION_ADMIN`)

An institution administrator manages one institution through an active membership and an active institution. The role is institution-scoped, not a license to administer every institution.

Documented capabilities include:

- Manage institution academic hierarchy: schools, departments, programmes, academic years, and cohorts.
- Invite verified accounts to the institution and manage memberships.
- Search institution students and faculty.
- Inspect student academic context and portfolio summary.
- Assign a student to a cohort belonging to the same institution.
- Verify eligible academic records and portfolio entries.
- Update faculty department, designation, or activation through authorized routes.
- Create and end faculty-student mentorships.
- Create and manage campus recruitment drives.
- Manage institution-scoped assessment campaigns and assignments where the relevant route allows it.
- View institution dashboards and audit events.
- View institution aggregate metrics and pending work.

Membership revocation is documented to block institution-scoped service operations immediately. However, the source also notes that not every legacy route has yet been retrofitted with institution-scoped authorization. Do not claim platform-wide tenant isolation without testing all relevant routes.

### 3.4 Platform administrator (`PLATFORM_ADMIN`)

The platform administrator is a privileged global role and must never be self-assigned through public registration.

Documented capabilities include:

- Create institutions and manage their platform-level status.
- Approve or reject institution registrations.
- Assign the initial institution administrator membership.
- Manage institution membership bootstrap.
- Review employer organization verification/approval decisions and platform-level status transitions.
- Perform other platform-level operations explicitly protected by platform-admin authorization.

Bootstrap the first platform administrator only through a trusted, reviewed administrative operation or a separately secured deployment bootstrap procedure. Never expose a public route that lets a user grant themselves this role.

### 3.5 Employer organization roles

Employer access uses **organization-scoped memberships**, not global account roles. The documented membership roles include `OWNER`, `ADMIN`, `RECRUITER`, and `VIEWER`; invitation creation can invite an email as `ADMIN`, `RECRUITER`, or `VIEWER`.

- **OWNER:** owns the organization and has elevated membership administration rights.
- **ADMIN:** manages authorized organization-level operations.
- **RECRUITER:** can perform recruiting actions permitted by the organization APIs.
- **VIEWER:** is an invited membership role; exact read-only surface must be verified in implementation.

Only active, authorized employer members may manage the organization's recruiting resources. Only owners may grant the admin role or remove administrators; the owner cannot be removed through ordinary membership administration.

### 3.6 Legacy/global academic roles

Some legacy internship endpoints document roles such as `SYSTEM_ADMIN`, `DEAN`, `DEPT_HEAD`, and `FACULTY`. These legacy role checks are not identical to the newer institution membership model. Preserve the actual route authorization until a reviewed migration unifies it. Do not infer that a `DEAN` or `DEPT_HEAD` role automatically implies `INSTITUTION_ADMIN` membership.

---

## 4. Authentication and account lifecycle

### 4.1 Student registration

Documented route: `POST /api/v1/auth/register/student`

Expected flow:

1. Student submits registration details.
2. Email is normalized by trimming and lower-casing.
3. The server assigns the `STUDENT` role; clients cannot submit a role to self-promote.
4. The student profile is created with a unique enrollment number and an existing cohort ID.
5. The account starts active but unverified under the documented policy.
6. A signed email verification token is issued and emailed when Resend is configured.
7. The student verifies the email before login is allowed.
8. The student can sign in only if the account is verified and active.

Passwords require at least 12 characters and are hashed using Argon2 through `pwdlib`. Duplicate email, enrollment number, and employee code conditions are documented as conflicts (`409`). Invalid request data or unknown cohort/department can return `422`.

**Frontend contract rule:** the UI must use readable labels for school, department, programme, and cohort selections while submitting the actual identifier type and field names required by the backend. Password confirmation should normally be validated client-side and omitted from the API payload unless the actual endpoint schema requires it.

### 4.2 Faculty registration

Documented route: `POST /api/v1/auth/register/faculty`

Expected flow:

1. Faculty submits their profile details, including an existing active department and unique employee code.
2. The server assigns the `FACULTY` role.
3. The account starts inactive and unverified.
4. Email verification confirms control of the email address.
5. An authorized institutional approval process activates the account.
6. Login is allowed only after all required account-state conditions are satisfied.

Email verification **does not** itself activate faculty. No public registration route should activate a faculty account.

### 4.3 Email verification and resend

Documented routes:

- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/verification/resend`

Verification tokens are signed, expire after 30 minutes, are single-use, and are stored as SHA-256 hashes in the documented token field. Resend responses should avoid disclosing whether an email is registered. Delivery uses `RESEND_API_KEY` and `RESEND_FROM_EMAIL`.

A registration may be persisted even if email delivery fails; the response should report delivery failure without exposing provider details. Users can retry through the resend route.

### 4.4 Login, current identity, and logout

Documented routes:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`

Access tokens are JWT bearer tokens and have a documented default expiry of 30 minutes via `ACCESS_TOKEN_EXPIRE_MINUTES`. Invalid credentials and pending/disabled accounts share a generic `401` response.

The source documents describe a token-version implementation in which logout increments the account token version and older access tokens are rejected. A separate earlier authentication note describes client-side token disposal only because the original schema lacked a session table. Treat the token-version behavior and its migration as the newer documented behavior, but verify the current branch and deployed schema before relying on it.

A shared IP-based login/reset rate limiter is not documented as complete. Apply suitable rate limiting at the gateway/reverse proxy and/or shared application middleware before production.

### 4.5 Password reset

Documented routes:

- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`

Flow:

1. User submits an email address.
2. API returns a generic response regardless of whether an eligible account exists.
3. A secure signed, expiring reset token is generated and sent through Resend when configured.
4. The token is checked against its stored SHA-256 digest.
5. Successful confirmation consumes the token, changes the password using the existing password hasher, and increments the account token version.
6. Previously issued tokens are rejected according to the token-version implementation.

The stored unexpired reset token is documented as an account-level cooldown. Shared IP-based rate limiting remains a hardening item. Never log reset tokens or disclose whether the email belongs to an account.

### 4.6 Profile APIs

Documented routes:

- `GET/PATCH /api/v1/students/me`
- `GET /api/v1/students/me/enrollments`
- `GET/PATCH /api/v1/faculty/me`
- `GET /api/v1/faculty/me/affiliations`

Only permitted profile fields should be editable by the account owner. Official enrollment, cohort, department, role, account activation, and academic outcomes must be changed through their authorized workflows, not generic profile editing.

### 4.7 Common authentication errors

The supplied module notes describe the following general error semantics:

- `401`: missing/invalid/expired token or invalid credentials.
- `403`: authenticated account lacks required permission/role.
- `404`: profile or academic context not found.
- `409`: duplicate email, enrollment number, employee code, or conflicting state transition.
- `422`: invalid request or unknown academic reference.
- `503`: explicitly unavailable external integration, such as the currently unavailable identity-verification provider or unconfigured Griffin dispatch adapter.

Actual endpoint-specific behavior must be checked against current code.

---

## 5. Institution registration and onboarding

### 5.1 Platform-provisioned institution

Documented lifecycle:

1. A platform administrator creates an institution in `PENDING`.
2. A platform administrator activates the institution.
3. A platform administrator assigns the initial `INSTITUTION_ADMIN` membership.
4. The institution administrator configures the academic hierarchy.
5. Memberships and invitations are managed through institution-scoped routes.

Institution creation and membership bootstrap are privileged operations. The first platform administrator must be provisioned through a reviewed, trusted process.

### 5.2 Institution self-service registration

Documented route: `POST /api/v1/institutions/register`

Preconditions: the registering account must be authenticated, active, and verified.

Flow:

1. Account submits institution details.
2. Institution is created in `PENDING_APPROVAL`.
3. The registrant receives a pending `INSTITUTION_ADMIN` membership.
4. Pending membership does not authorize institution administration.
5. The registrant checks status using `GET /api/v1/institutions/{institution_id}/registration-status`.
6. A platform administrator approves through `PATCH /api/v1/institutions/{institution_id}/status` with `{"status":"ACTIVE"}`, which also enables the original registrant's pending membership, or rejects the registration with `{"status":"REJECTED"}`.

Supported registration profile fields include institution type, legal/registration number, contact email, website, address, country, state, city, postal code, and description. A registration number and slug may be unique. Submitted email domains or registration numbers are not proof of legal ownership; this is platform review, not external legal verification.

### 5.3 Institution membership invitations

Documented routes include:

- `POST /api/v1/institutions/{institution_id}/invitations`
- `GET /api/v1/institutions/{institution_id}/invitations`
- `DELETE /api/v1/institutions/{institution_id}/invitations/{invitation_id}`
- `POST /api/v1/institutions/invitations/accept`

Invitations expire after seven days, store only a token hash, and can be accepted once by the invited email account. Acceptance requires the invitee to have an active, verified Kairos account. Faculty invitations additionally require an existing faculty profile in the target institution.

### 5.4 Academic hierarchy

The hierarchy is:

```text
Institution
└── School
    └── Department
        └── Programme
            └── Cohort
                └── Student profile
```

Academic years are institution-scoped where supported and cohorts link programmes to academic years. Exact schema relationships should be read from the current models and migrations.

Institution administrators can create/list and, in the documented stage, PATCH/update or guarded-delete schools, departments, programmes, academic years, and cohorts. Parent-child moves are validated against the institution. Deletion is rejected while dependent records still reference the entity. Academic-year start/end dates are validated, and changing the current academic year clears the previous current-year flag.

**Registration UI behavior:** resolve the institution from the authenticated/verified domain flow when supported; display the institution as read-only; load schools, then departments, then programmes/cohorts using dependent dropdowns. Show names to users, retain identifiers internally, clear child selections when a parent changes, and distinguish a genuine empty result from a failed API request. Never show “no schools configured” when the request actually returned a server error.

### 5.5 Tenant isolation caveat

The source documents note that older school and academic-year rows can have nullable institution keys and that some legacy student/faculty/internship routes have not all been retrofitted with institution-scoped authorization. Review and repair this systematically before claiming complete multi-tenant isolation.

---

## 6. Student experience and workflow

### 6.1 Student dashboard

Documented route: `GET /api/v1/students/me/dashboard`

The dashboard returns persisted aggregate data, including:

- Portfolio completeness.
- Internship application and placement counts.
- Report and evaluation status counts.

The dashboard uses aggregate queries rather than loading all underlying records. Griffin completion remains zero until validated results are accepted through the integration workflow.

### 6.2 Student academic context

`GET /api/v1/students/me/enrollments` returns academic context derived from the student's cohort. The supplied schema does not establish a separate `student_enrollments` table in the documented stage. Do not fabricate a separate enrollment history table or claim multiple historical enrollments unless a reviewed schema supports it.

### 6.3 Student portfolio and CV

The backend architecture audit documents a `StudentPortfolioService` responsible for student-scoped academic-record, typed-entry, resume CRUD, completeness, summary, CV, and timeline aggregation. Exact entry types and upload routes should be confirmed from the current API code.

Portfolio/academic verification is an institution-admin-controlled operation where those routes exist. Students must not verify their own records. Portfolio visibility and access to files should follow the current authorization rules.

### 6.4 Student internship journey

1. Student signs in with an active, verified account.
2. Student browses active opportunities.
3. Student opens an opportunity detail.
4. Student applies before the deadline.
5. Duplicate applications are rejected.
6. Student views their own applications.
7. Student may withdraw while the application is `APPLIED` or `SHORTLISTED`.
8. Authorized staff move the application through valid states.
9. A placement can be created only after the application reaches `OFFERED`.
10. Student participates in the placement/report workflow and views authorized review/evaluation outcomes.

Legacy internship routes are documented under `/api/v1/internships`:

- `GET /opportunities`
- `GET /opportunities/{opportunity_id}`
- `POST /opportunities/{opportunity_id}/applications`
- `GET /applications/me`
- `POST /applications/{application_id}/withdraw`

The exact router registration and authorization must be verified in the current branch.

### 6.5 Student report and evaluation journey

The documented system includes report submissions, version records, file metadata, review/status transitions, and an external evaluation boundary.

Expected domain flow where implemented:

1. Student uploads or selects a report file through the authorized report/storage workflow.
2. Kairos stores file metadata and verifies file integrity according to the storage implementation.
3. A report version is associated with a submission.
4. Student submits the version.
5. The assigned faculty supervisor receives a best-effort email notification after the database commit.
6. The authorized supervisor reviews the report and may update the review/status according to supported transitions.
7. A supervisor may request Griffin evaluation for a submitted version.
8. Evaluation attempts and status are recorded in Kairos.
9. Only validated external results may be represented as completed evaluation results.
10. Student sees authorized status and feedback.

Do not infer that every evaluation stage in the high-level database specification is already implemented. Use the current API and model state.

### 6.6 Student campus recruitment journey

1. Institution administrator creates a recruitment drive and configures target programmes, cohorts, and/or graduation years.
2. Drive is published and activated through allowed lifecycle transitions.
3. Eligible employers are invited or associated.
4. Employers associate suitable opportunities with the drive.
5. Student opens the student-scoped recruitment-drive list.
6. Server evaluates eligibility from the authenticated student's persisted academic relationships.
7. Student views eligible opportunities and applies through the canonical application workflow.
8. Eligibility is checked again at application submission.

Documented student endpoints include:

- `GET /api/v1/students/recruitment-drives`
- `GET /api/v1/students/recruitment-drives/{drive_id}/eligibility`
- `GET /api/v1/students/recruitment-drives/{drive_id}/opportunities`
- `GET /api/v1/students/opportunities/{opportunity_id}/eligibility`

No client-supplied student identity is accepted for eligibility. The server derives the student from the authenticated account.

---

## 7. Faculty experience and workflow

### 7.1 Faculty dashboard

Documented route: `GET /api/v1/faculty/me/dashboard`

Returns persisted aggregate data for:

- Supervised placements.
- Reports pending review.
- Active mentorships.
- Pending assessment assignments.

Metrics must not be fabricated and must respect the faculty member's actual assignments and access scope.

### 7.2 Faculty report review

Where report review routes are implemented:

1. Faculty opens a report assigned to them.
2. Faculty reviews the current submitted version and relevant metadata.
3. Faculty records the supported review decision, status, or feedback.
4. Kairos commits the domain update.
5. A best-effort email notification may be sent to the student after the commit.
6. The action is included in audit records where instrumentation exists.

A faculty member must not inspect reports for placements they are not authorized to supervise.

### 7.3 Griffin evaluation request

Documented routes:

- `POST /api/v1/evaluations/report-versions/{version_id}`
- `GET /api/v1/evaluations/{evaluation_id}`
- `GET /api/v1/evaluations/{evaluation_id}/attempts`

Only the faculty supervisor assigned to the placement may initiate or inspect these evaluation records.

Kairos creates its own evaluation row and attempt. It requires a validated external `job_id` before marking a request as processing. Failed dispatches are recorded as failed attempts and must not be presented as completed evaluations.

**External dependency blocker:** the source does not establish Griffin's authoritative base URL, authentication, endpoint paths, payload schema, callback/polling contract, or result schema. The default adapter intentionally fails closed with `503` after recording the failed attempt. Do not invent an endpoint, send speculative requests, or fabricate scores/results. Live dispatch requires the authoritative contract, credentials, validation, idempotency, retries, callback authentication, correlation, timeout handling, and integration tests. A database uniqueness constraint is still needed for race-safe idempotency under concurrent requests.

### 7.4 Faculty assessment assignments

The documented assessment outcome endpoint is:

`PATCH /api/v1/institutions/{institution_id}/assessment-campaigns/{campaign_id}/assignments/{assignment_id}`

Lifecycle:

```text
PENDING → IN_PROGRESS → SUBMITTED
```

Institution administrators may also expire pending or in-progress assignments. Submission requires a score from 0 to 100; feedback and submission timestamps are optional. Assigned faculty can update only their own assignment. Institution administrators can manage assignments within their institution.

The current model records one outcome per faculty assignment. Campaign participant/team scoring workflows beyond these outcomes remain future work. The source does not establish that assessment question/attempt tracking is complete.

### 7.5 Mentorship

Documented institution-scoped routes:

- `POST/GET /api/v1/institutions/{institution_id}/mentorships`
- `PATCH /api/v1/institutions/{institution_id}/mentorships/{mentorship_id}/end`

Mentorship assignment requires both student and faculty profiles to belong to the institution and rejects a second active mentor. Mentorship history is stored in `faculty_student_mentorships`.

The source notes no dedicated teaching-assignment model in the documented stage. Do not use mentorship as a substitute for a formal course-teaching assignment.

---

## 8. Institution administrator experience

### 8.1 Institution dashboard

Documented route:

`GET /api/v1/institutions/{institution_id}/dashboard`

Restricted to active institution administrators. Returns aggregate counts for students, faculty, schools, departments, placements, pending reports, and active campaigns. Queries should use aggregate counts and enforce institution scoping.

### 8.2 Student administration

Documented routes:

- `GET /api/v1/institutions/{institution_id}/students`
- `GET /api/v1/institutions/{institution_id}/students/{student_id}`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/cohort`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/academic-records/{record_id}/verification`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/portfolio/{entry_id}/verification`

Student search is paginated and supports name, email, or enrollment number. Student detail provides academic context and portfolio summary. Cohort assignment must choose a cohort belonging to the same institution. Verification actions are service-enforced and cannot be performed by the student on their own record.

### 8.3 Faculty administration

Documented routes:

- `GET /api/v1/institutions/{institution_id}/faculty`
- `PATCH /api/v1/institutions/{institution_id}/faculty/{faculty_id}`

Search is paginated. Authorized administrators may update department, designation, or account activation. Verify the active membership and institution status before allowing these actions.

### 8.4 Recruitment-drive administration

Institution administrators create draft drives, configure targets, publish/activate them, and complete/cancel/archive them according to the lifecycle. Drives are institution-owned and require an active institution and active institution-admin membership.

Drive lifecycle:

```text
DRAFT → PUBLISHED → ACTIVE → COMPLETED → ARCHIVED
```

Cancellation is permitted from `DRAFT`, `PUBLISHED`, or `ACTIVE`; cancelled drives can then be archived. Completed/cancelled drives cannot be reactivated.

Targeting semantics:

- Programme values within one dimension are ORed.
- Cohort values within one dimension are ORed.
- Graduation-year values within one dimension are ORed.
- Configured dimensions combine with AND.
- Every configured dimension is a mandatory filter.
- If all target lists are empty, the drive is institution-wide, but students must still belong to that institution.
- Cohorts/programmes must match the institution's academic hierarchy.

### 8.5 Audit events

Documented route:

`GET /api/v1/institutions/{institution_id}/audit-events`

Supports `action`, `entity_type`, `limit`, and `offset`. Only an active institution administrator can read the institution's events.

Audit records are append-only and are written in the same database transaction as selected sensitive operations, including institution status/membership changes, academic hierarchy creation, cohort assignment, academic/portfolio verification, faculty profile changes, mentorship changes, report lifecycle events, team membership, assessment campaign/assignment changes, and file upload/download/deletion.

Event details are restricted to operational metadata. Raw file contents, credentials, password-reset tokens, and report contents are not recorded. Coverage is not exhaustive across all legacy internship/authentication routes; do not claim that every sensitive action is audited.

---

## 9. Employer and recruiter experience

### 9.1 Employer onboarding

Documented routes:

- `POST /api/v1/employers/register`
- `GET /api/v1/employers/me/organizations`
- `GET/PATCH /api/v1/employers/organizations/{organization_id}`
- `GET /api/v1/employers/organizations/{organization_id}/registration-status`
- `POST /api/v1/employers/organizations/{organization_id}/submit-for-verification`
- `PATCH /api/v1/employers/organizations/{organization_id}/status` (platform administrator)
- `POST /api/v1/employers/organizations/{organization_id}/verification-decision?decision=ACTIVE|REJECTED&notes=...` (platform administrator)

Employer administration requires an authenticated, verified Kairos account and an active organization membership. Registration creates a pending employer organization and initial owner membership, while retaining legacy internship provider functionality by linking the provider row.

Organization lifecycle:

```text
PENDING_VERIFICATION → PENDING_APPROVAL → ACTIVE
                                      └→ REJECTED
```

Publishing opportunities requires an `ACTIVE` organization. Platform review is not the same as third-party legal verification.

### 9.2 Employer members and invitations

Documented routes include:

- `GET /api/v1/employers/organizations/{organization_id}/members`
- `POST /api/v1/employers/organizations/{organization_id}/invitations`
- `GET /api/v1/employers/organizations/{organization_id}/invitations`
- `DELETE /api/v1/employers/organizations/{organization_id}/invitations/{invitation_id}`
- `POST /api/v1/employer-invitations/accept`
- `PATCH /api/v1/employers/organizations/{organization_id}/members/{account_id}/role`
- `DELETE /api/v1/employers/organizations/{organization_id}/members/{account_id}`

Invitations expire after seven days and use hashed, single-use tokens. If invitation email delivery fails, the invitation is revoked and the response reports `delivery_sent: false`. The owner cannot be removed through ordinary membership administration.

### 9.3 Jobs and opportunities

Documented endpoints include:

- `POST /api/v1/employers/organizations/{organization_id}/jobs`
- `GET /api/v1/employers/organizations/{organization_id}/jobs`
- `GET/PATCH /api/v1/employers/organizations/{organization_id}/jobs/{job_id}`
- Lifecycle actions: publish, pause, resume, close, reopen, archive.
- Public discovery: `GET /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`
- Company discovery: `GET /api/v1/companies/{organization_id}` and `/jobs`
- Employer dashboard: `GET /api/v1/employers/organizations/{organization_id}/dashboard`

Jobs and internships reuse `internship_opportunities` and `internship_applications`, rather than creating a parallel application store. Public discovery returns only published, unexpired listings from active employer organizations. Campus-linked jobs are excluded from generic discovery and surfaced through eligible student drive endpoints.

### 9.4 Recruiter pipeline

Documented endpoints include:

- `GET /api/v1/employers/organizations/{organization_id}/applications`
- `GET /api/v1/employers/organizations/{organization_id}/applications/{application_id}`
- `POST /api/v1/employers/organizations/{organization_id}/applications/{application_id}/stage`
- `GET /api/v1/employers/organizations/{organization_id}/applications/{application_id}/notes`
- `POST /api/v1/employers/organizations/{organization_id}/applications/{application_id}/notes`

Recruitment stage history records actor, transition, timestamp, and optional transition note. Internal recruiter notes are returned only through organization-authorized endpoints. A compatibility mapping preserves the existing application status field for legacy student and placement workflows.

The employer module's `HIRED` recruitment stage does not automatically create an academic placement. The established placement flow remains authoritative.

---

## 10. Internship and placement lifecycle

The documented legacy internship module uses:

- `internship_providers`
- `internship_opportunities`
- `internship_applications`
- `internship_placements`

All documented `/api/v1/internships` routes require an active, verified bearer-token account.

### 10.1 Application states

The supplied canonical schema and module document define:

```text
APPLIED → SHORTLISTED → OFFERED
   │          │           │
   ├→ REJECTED ├→ REJECTED └→ REJECTED
   └→ WITHDRAWN (student may withdraw while APPLIED or SHORTLISTED)
```

More precisely:

- `APPLIED → SHORTLISTED` or `REJECTED`
- `SHORTLISTED → OFFERED` or `REJECTED`
- `OFFERED → REJECTED`
- Owning student may withdraw from `APPLIED` or `SHORTLISTED`.
- A placement can be created only after an application reaches `OFFERED`.

The supplied schema enum is `APPLIED`, `SHORTLISTED`, `OFFERED`, `REJECTED`, `WITHDRAWN`. It does not define `ACCEPTED`. Do not emit `ACCEPTED` unless a reviewed schema migration adds that state.

### 10.2 Integrity rules

- Duplicate applications are rejected and protected by a database uniqueness constraint.
- Inactive or expired opportunities cannot be applied to.
- Invalid state transitions return `409`.
- Placement student identity is derived from the application, not client input.
- Faculty supervisor IDs are validated against faculty profiles.
- The source notes that finer department-scoped permissions, provider ownership, and audit logging need schema support or approved changes in the legacy internship module.

---

## 11. Reports, file storage, and evaluations

### 11.1 File storage

The high-level architecture specification describes VPS local filesystem storage under `/var/kairos/storage/`, with metadata in `storage_files`, including SHA-256 hash, MIME type, relative path, and file size. Report files are associated with report submissions and immutable version records.

Security requirements for any implementation:

- Resolve file paths within the configured storage root.
- Validate file type, size, and access rights.
- Verify checksums when appropriate.
- Do not expose arbitrary filesystem paths.
- Authorize every download against the associated report/placement and requesting user.
- Record upload/download/deletion events where audit instrumentation is implemented.
- Keep raw file content out of audit-event payloads.

Confirm exact upload/download routes and the deployed storage configuration in the current source before implementing or documenting additional routes.

### 11.2 Report lifecycle

The supplied DDL describes report submission states:

`DRAFT`, `SUBMITTED`, `UNDER_EVALUATION`, `REVISION_REQUIRED`, `APPROVED`, `REJECTED`

Report submissions have version records, and the database design aims to preserve version history. Follow the current service state machine and tests rather than adding unsupported transitions.

### 11.3 Griffin boundary

Griffin is an external evaluation engine with its own SQLite-backed data store. Kairos and Griffin must not share cross-database foreign keys. Correlation is maintained through application-level identifiers and validated external keys.

Kairos may persist its own evaluation request and attempt state, but it must not mark evaluation as processing without a validated external `job_id`, and must not mark it completed without validated result data. The current documented adapter intentionally fails closed because the authoritative Griffin API contract is missing.

---

## 12. Assessment outcomes

The documented faculty-assessment assignment lifecycle is:

`PENDING → IN_PROGRESS → SUBMITTED`

Institution administrators can expire pending or in-progress assignments. Submission requires a score from 0 to 100, and may include feedback and a submission timestamp. Assigned faculty can update only their own assignment; institution administrators can manage assignments within their institution.

Migration `20261022_08` is documented as adding score, feedback, and submission timestamp fields. Verify actual migration ancestry before applying it.

The current model records one outcome per faculty assignment. Do not assume campaign participant/team scoring or complete question/attempt tracking is implemented.

---

## 13. Notifications and email delivery

### 13.1 Provider

Resend is the documented transactional email provider. Authentication configuration includes:

- `RESEND_API_KEY`
- `RESEND_FROM_EMAIL`
- `FRONTEND_URL` for verification links

Secrets must be stored in environment/secret management, not committed to Git or exposed in frontend bundles.

### 13.2 Documented email-triggered workflows

- Account email verification and verification resend.
- Password reset.
- Report submission to the assigned faculty supervisor.
- Report review/status change to the student.
- Faculty assessment assignment.
- Employer invitation delivery through the configured notification provider.

The high-level architecture specification also describes intended notification events for account activation, placement offer/acceptance, report submission confirmation, Griffin evaluation completion, and faculty assessment assignment. Treat any event not confirmed by the actual implementation as a planned/needs-verification event, not a guaranteed live email.

### 13.3 Delivery reliability limitation

Workflow notifications are documented as best-effort and sent after the database transaction commits. A provider timeout must not roll back the underlying business operation or falsely change the domain record to success/failure. At the documented stage there is no transactional outbox, retry worker, or delivery receipt table, so some failed workflow emails can be missed. Do not claim durable at-least-once delivery until that infrastructure exists and is tested.

---

## 14. Optional identity verification

Kairos documents an optional authenticated identity-verification status/initiation API:

- `GET /api/v1/identity-verification/status`
- `POST /api/v1/identity-verification/initiate`

Initiation requires explicit consent and a consent-notice version. The authenticated account ID comes from the bearer token, not a client-supplied user ID. Verification is optional and must not block registration, login, roles, memberships, or ordinary access.

**Live Aadhaar identity verification is not currently available through the documented TheVerifico product.** The source says its public offering describes OCR/extraction, which is not identity verification. Kairos must not upload Aadhaar images, request Aadhaar numbers/OTPs, call a guessed endpoint, or mark a user verified based on OCR, frontend flags, or initiation responses.

The adapter intentionally fails closed with `503` until an authorized, documented identity-verification flow and authenticity mechanism are available. Store only workflow metadata; do not persist Aadhaar numbers, OTPs, identity images, raw provider payloads, or secrets. Use “Identity verified” only after a genuine provider result has been independently validated.

---

## 15. Database and architecture principles

### 15.1 Documented stack

- Frontend: React, Vite, Shadcn UI, Tailwind CSS.
- Backend: FastAPI, Python 3.11+ in the architecture specification, SQLAlchemy 2.x, Alembic.
- Database: MySQL 8-compatible, TiDB Cloud, or compatible AWS RDS MySQL deployment.
- Email: Resend.
- Storage: configured local/VPS storage for report and file metadata.
- External evaluation: Griffin, with isolated storage and API boundary.

The backend architecture audit mentions an async SQLAlchemy engine/session factory, centralized API router registration, domain services for identity, academics, student portfolio, and internships, plus shared exceptions/repository primitives.

### 15.2 Modular backend conventions

The modularization guide specifies the following responsibilities:

- **Router:** HTTP input, authentication/authorization, validation, HTTP exception mapping, serialization.
- **Service:** business use cases, domain invariants, state transitions, transaction ownership, concurrency conflict handling.
- **Repository:** meaningful persistence/query operations using SQLAlchemy async APIs.
- **Schemas:** Pydantic v2 request/response contracts; write schemas should reject unexpected fields where appropriate.
- **Exceptions:** domain exceptions with stable error codes, not leaked SQL or integration internals.

Recommended module structure:

```text
app/modules/<domain>/
├── router.py
├── schemas.py
├── service.py
├── repository.py
└── exceptions.py
```

Keep the shared ORM in `app/models/`, maintain one model-registration path, and avoid a flag-day rewrite. New modular endpoints may be added under `/api/v1/modules/<domain>` while legacy `/api/v1/*` routes remain stable. Legacy routes should delegate to new services only after response/authorization parity tests pass.

### 15.3 Transaction and state-machine rules

- A service owns commit/rollback for a use case.
- Do not call `session.begin()` after a read has already autobegun a transaction.
- Use conditional updates against both the resource ID and expected status for state transitions.
- Treat zero-row conditional updates as concurrency conflicts.
- Catch known integrity errors, roll back, and translate them into stable domain errors.
- Use database constraints as the final protection against duplicate applications or concurrent invalid operations.
- Avoid N+1 queries and full-history loads for dashboard aggregates.

### 15.4 Schema and migration safety

The source docs mention migration revisions including `20261022_01` through later revisions such as `20261022_16` in separate module notes. This does not establish that the full chain is present in every branch or applied in production.

Before a migration:

1. Inspect actual Alembic files and `down_revision` ancestry.
2. Inspect deployed `alembic_version` and schema through authorized read-only procedures.
3. Reconcile column names, types, nullability, and foreign keys with the actual ORM.
4. Test upgrade and downgrade in an isolated compatible database.
5. Prefer additive, forward-only production changes where appropriate.
6. Do not use `create_all` as a substitute for production migrations.
7. Never rewrite historical migration meaning or assume a partial migration test proves production safety.

---

## 16. Dashboards and analytics

### 16.1 Student dashboard

`GET /api/v1/students/me/dashboard`

Documented metrics: portfolio completeness, internship application/placement counts, and report/evaluation status counts.

### 16.2 Faculty dashboard

`GET /api/v1/faculty/me/dashboard`

Documented metrics: supervised placements, reports pending review, active mentorships, and pending assessment assignments.

### 16.3 Institution dashboard

`GET /api/v1/institutions/{institution_id}/dashboard`

Documented metrics: aggregate student/faculty/school/department counts, placements, pending reports, and active campaigns. Access requires an active institution administrator.

### 16.4 Employer dashboard

`GET /api/v1/employers/organizations/{organization_id}/dashboard`

The endpoint is documented in the employer module; inspect the response schema to determine exact metrics.

All dashboard numbers must come from persisted records. A count must not be hardcoded, inferred from an incomplete integration, or shown as complete when the underlying workflow has not produced a validated result.

---

## 17. UI and frontend implementation rules

The supplied product requirement for the Kairos frontend is to use Shadcn UI consistently. When implementing or changing frontend flows:

- Inspect the current Shadcn configuration, aliases, Tailwind version, theme tokens, and existing components first.
- Use installed Shadcn components for standard buttons, cards, forms, inputs, selects, tabs, dialogs, menus, tables, badges, progress indicators, skeletons, and tooltips.
- Use the project's existing Lucide icon conventions where present.
- Do not introduce Bootstrap, Material UI, Ant Design, Chakra UI, or a competing dashboard kit.
- Do not reimplement an existing Shadcn primitive as a custom dropdown/modal/tab when the appropriate component is available.
- Preserve accessibility: keyboard interaction, focus states, semantic labels, readable contrast, and text in addition to status color.
- Keep the UI responsive and aligned with Kairos's existing design tokens.
- Use real API-backed data. Do not substitute static mock data for a working flow.
- Distinguish a genuine empty result from loading, network, authorization, validation, and server errors.
- Display readable academic names; keep internal IDs as values and submit the exact backend contract.
- Do not claim a frontend is complete until its requests, response mapping, validation, empty/error states, and success flow are verified.

### 17.1 Profile dashboards

The requested profile-dashboard direction is a shared, clean profile layout inspired by the supplied dashboard reference, with role-specific tabs and data.

Potential student sections, subject to actual module support:

- Overview.
- Academic profile.
- Courses/enrollment context.
- Assessments and assignments.
- Projects/research.
- Academic history.
- Portfolio, achievements, and skills.
- Activity.
- Settings.

Potential faculty sections, subject to actual module support:

- Overview.
- Professional profile.
- Teaching/courses where supported by assignments.
- Assessments and reviews.
- Student supervision/mentorship.
- Projects/research where records exist.
- Activity.
- Settings.

Use authoritative academic records for course, score, placement, and verification history. User-editable biography/skills must not be confused with institution-verified credentials. Do not invent course-assignment or historical-enrollment data when the corresponding model does not exist.

---

## 18. Key API reference by domain

> This is a concise index of routes explicitly listed in the supplied module documents. Confirm exact prefixes and router registration against the current branch.

### Authentication

- `POST /api/v1/auth/register/student`
- `POST /api/v1/auth/register/faculty`
- `POST /api/v1/auth/verify-email`
- `POST /api/v1/auth/verification/resend`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`
- `POST /api/v1/auth/password-reset/confirm`

### Student/faculty profile

- `GET/PATCH /api/v1/students/me`
- `GET /api/v1/students/me/enrollments`
- `GET /api/v1/students/me/dashboard`
- `GET/PATCH /api/v1/faculty/me`
- `GET /api/v1/faculty/me/affiliations`
- `GET /api/v1/faculty/me/dashboard`

### Institution administration

- `POST /api/v1/institutions`
- `GET /api/v1/institutions`
- `GET /api/v1/institutions/{institution_id}`
- `PATCH /api/v1/institutions/{institution_id}/status`
- `PUT /api/v1/institutions/{institution_id}/members/{account_id}`
- `GET /api/v1/institutions/{institution_id}/members`
- `DELETE /api/v1/institutions/{institution_id}/members/{account_id}`
- `POST /api/v1/institutions/{institution_id}/invitations`
- `GET /api/v1/institutions/{institution_id}/invitations`
- `DELETE /api/v1/institutions/{institution_id}/invitations/{invitation_id}`
- `POST /api/v1/institutions/invitations/accept`
- `POST /api/v1/institutions/register`
- `GET /api/v1/institutions/{institution_id}/registration-status`
- `GET /api/v1/institutions/{institution_id}/dashboard`

### Academic administration

- `GET /api/v1/institutions/{institution_id}/students`
- `GET /api/v1/institutions/{institution_id}/students/{student_id}`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/cohort`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/academic-records/{record_id}/verification`
- `PATCH /api/v1/institutions/{institution_id}/students/{student_id}/portfolio/{entry_id}/verification`
- `GET /api/v1/institutions/{institution_id}/faculty`
- `PATCH /api/v1/institutions/{institution_id}/faculty/{faculty_id}`
- `POST/GET /api/v1/institutions/{institution_id}/mentorships`
- `PATCH /api/v1/institutions/{institution_id}/mentorships/{mentorship_id}/end`
- `GET /api/v1/institutions/{institution_id}/audit-events`

Institution-scoped schools, departments, programmes, academic years, and cohorts have list/create routes and, in the documented stage, PATCH and guarded DELETE routes. Inspect current route schemas for exact methods and payloads.

### Internship and placement

- `GET /api/v1/internships/opportunities`
- `GET /api/v1/internships/opportunities/{opportunity_id}`
- `POST /api/v1/internships/providers`
- `POST /api/v1/internships/opportunities`
- `POST /api/v1/internships/opportunities/{opportunity_id}/applications`
- `GET /api/v1/internships/applications/me`
- `POST /api/v1/internships/applications/{application_id}/withdraw`
- `PATCH /api/v1/internships/applications/{application_id}/status`
- `POST /api/v1/internships/applications/{application_id}/placement`

### Evaluation / Griffin

- `POST /api/v1/evaluations/report-versions/{version_id}`
- `GET /api/v1/evaluations/{evaluation_id}`
- `GET /api/v1/evaluations/{evaluation_id}/attempts`

Live Griffin dispatch is blocked until the authoritative external API contract is supplied and implemented.

### Assessments

- `PATCH /api/v1/institutions/{institution_id}/assessment-campaigns/{campaign_id}/assignments/{assignment_id}`

### Campus recruitment

- `POST/GET /api/v1/institutions/{institution_id}/recruitment-drives`
- `GET/PATCH /api/v1/recruitment-drives/{drive_id}`
- `POST /api/v1/recruitment-drives/{drive_id}/publish`
- `POST /api/v1/recruitment-drives/{drive_id}/activate`
- `POST /api/v1/recruitment-drives/{drive_id}/complete`
- `POST /api/v1/recruitment-drives/{drive_id}/cancel`
- `POST /api/v1/recruitment-drives/{drive_id}/archive`
- `POST /api/v1/recruitment-drives/{drive_id}/employers`
- `DELETE /api/v1/recruitment-drives/{drive_id}/employers/{organization_id}`
- `GET /api/v1/employers/organizations/{organization_id}/recruitment-drive-invitations`
- `POST /api/v1/employers/organizations/{organization_id}/recruitment-drive-invitations/{participation_id}/respond`
- `POST /api/v1/employers/organizations/{organization_id}/recruitment-drives/{drive_id}/opportunities`
- Student-scoped drive/eligibility routes listed in Section 6.6.

### Employer and recruiter

- `POST /api/v1/employers/register`
- `GET /api/v1/employers/me/organizations`
- `GET/PATCH /api/v1/employers/organizations/{organization_id}`
- `GET /api/v1/employers/organizations/{organization_id}/registration-status`
- `POST /api/v1/employers/organizations/{organization_id}/submit-for-verification`
- `PATCH /api/v1/employers/organizations/{organization_id}/status`
- `POST /api/v1/employers/organizations/{organization_id}/verification-decision`
- Organization member, invitation, job, application pipeline, notes, and dashboard routes listed in Section 9.

### Optional identity verification

- `GET /api/v1/identity-verification/status`
- `POST /api/v1/identity-verification/initiate`

Initiation currently fails closed while no supported live identity-verification contract is available.

---

## 19. Known limitations and explicit non-claims

The following limitations are stated in the supplied source documents and must remain visible to implementers:

1. **Schema drift:** some ORM fields or newer module schemas may not match the checked-in DDL or deployed database. A reported login traceback references `accounts.full_name`, which may be missing in the actual MySQL table. Inspect the real schema before choosing between a safe migration and a code/model correction.
2. **Migration ancestry:** some source snapshots contain only part of the migration chain. Reconcile Alembic ancestry and deployed revision before applying migrations.
3. **Institution isolation:** not all legacy routes have been retrofitted with institution-scoped authorization; some older academic rows have nullable institution keys.
4. **Faculty teaching assignments:** a dedicated teaching-assignment model was not present in the documented academic-administration stage.
5. **Student enrollment history:** current enrollment context is derived from `student_profiles.cohort_id`; the source does not establish a separate historical enrollment table.
6. **Griffin live integration:** external API contract and credentials are not established in the supplied document; adapter fails closed and must not fabricate evaluation results.
7. **Identity verification:** TheVerifico OCR is not proof of identity; live Aadhaar verification is unavailable in the documented flow.
8. **Notification reliability:** no transactional outbox, retry worker, or delivery receipt table is documented; workflow emails are best-effort.
9. **Audit coverage:** audit instrumentation is selected/partial, not exhaustive across every legacy route.
10. **Assessment depth:** one outcome per faculty assignment is documented; full team scoring and question/attempt workflows remain future work.
11. **Employer verification:** platform review is not third-party legal verification.
12. **Placement conversion:** employer recruitment `HIRED` does not automatically create a placement; the academic placement flow remains authoritative.
13. **Rate limiting:** shared IP-based rate limiting for authentication/reset workflows is not documented as complete.
14. **Frontend status:** backend module documents do not prove that every route has a finished, integrated, production-verified frontend.
15. **Production verification:** repository changes and local tests alone do not prove production deployment or successful external email/provider delivery.

---

## 20. Security, privacy, and data integrity rules

- Always derive the current account from the authenticated token for self-service operations.
- Never trust client-supplied student identity, account role, institution ownership, verification state, score, or official academic attributes without server-side authorization and validation.
- Enforce organization and institution boundaries on every scoped resource.
- Keep password hashes, JWT secrets, API keys, reset tokens, verification tokens, OTPs, and private recruiter notes out of logs and public responses.
- Store token digests where the workflow specifies them; enforce expiry and single-use semantics.
- Treat email delivery status separately from the business transaction result.
- Do not mark external evaluations or identity verification complete without independently validated provider results.
- Preserve immutable report versions and append-only audit records where implemented.
- Avoid destructive schema changes and use reviewed migrations.
- Return stable, user-appropriate errors without leaking SQL queries, stack traces, secrets, or private data.
- Enforce authorization in the backend, not only by hiding frontend controls.

---

## 21. Recommended end-to-end verification checklist

Before a release is called complete, verify the relevant flows in a test environment:

### Identity
- [ ] Student registration creates the expected account, profile, and server-assigned role.
- [ ] Faculty registration starts inactive and unverified.
- [ ] Verification tokens expire and cannot be reused.
- [ ] Resend does not reveal whether an account exists.
- [ ] Unverified or disabled accounts cannot log in.
- [ ] Password reset responses do not reveal account existence.
- [ ] Password reset token is consumed once and old token versions are rejected after logout/reset as designed.
- [ ] Missing email configuration fails safely and visibly.

### Academic organization
- [ ] Institution lifecycle and membership authorization work.
- [ ] School → department → programme → cohort relationships are validated.
- [ ] Dropdown API errors are distinct from genuine empty results.
- [ ] IDs submitted by the UI match the actual backend schema.
- [ ] Cross-institution or unrelated parent-child IDs are rejected.
- [ ] Guarded deletion refuses to remove referenced academic entities.

### Student/faculty
- [ ] Student and faculty dashboards show real persisted metrics.
- [ ] Students can access only their own restricted records.
- [ ] Faculty can review only assigned placements/submissions and assignments.
- [ ] Institution administrators can search and manage only their institution's records.
- [ ] Profile updates do not overwrite official academic fields or erase history.

### Internship/recruitment
- [ ] Duplicate applications are prevented.
- [ ] Invalid application transitions are rejected.
- [ ] A placement cannot be created before the application is `OFFERED`.
- [ ] Drive eligibility is calculated from persisted student academic data.
- [ ] Employer organization membership and active status are enforced.
- [ ] Private recruiter notes are visible only to authorized organization members.
- [ ] Employer `HIRED` stage does not bypass the academic placement flow.

### Reports/evaluations
- [ ] Upload/download authorization and storage-root boundaries are enforced.
- [ ] Report versions remain associated with the correct submission.
- [ ] Audit events omit secrets and raw report contents.
- [ ] Griffin failures are recorded without fake processing/completion states.
- [ ] External evaluation idempotency and result validation are tested before live activation.

### Operations
- [ ] Alembic ancestry matches the target database.
- [ ] Migrations pass in an isolated MySQL-compatible database.
- [ ] Frontend build, linting, and backend tests pass.
- [ ] CI status is inspected for the actual commit.
- [ ] Production deployment and provider delivery are separately verified before claiming they work.

---

## 22. Change-management rules for future contributors

When implementing a new Kairos feature:

1. Read this guide and the owning domain module documentation.
2. Inspect the current source code, ORM, API schemas, and migration history.
3. State whether the request extends existing behavior or introduces a new capability.
4. Preserve existing route contracts and state-machine rules unless a reviewed change requires otherwise.
5. Implement the domain logic in the owning service; keep routers thin.
6. Reuse existing tables and canonical records rather than introducing parallel stores.
7. Add safe migrations only when supported by the intended model and actual schema.
8. Add success, failure, authorization, empty-state, and concurrency tests appropriate to the feature.
9. Run relevant tests and inspect CI.
10. Report implemented, tested, pushed, deployed, and production-verified states separately.

Do not hide missing data as an empty list, suppress API errors, remove authorization filters to make a screen work, use fake metrics, or claim an external integration works without a valid contract and evidence.

---

## 23. Glossary

- **Account:** Canonical login identity, associated with email, password hash, active/verified state, and roles.
- **Student profile:** Student-specific attributes such as enrollment number and cohort relationship.
- **Faculty profile:** Faculty-specific attributes such as employee code, department, and designation.
- **Institution:** Tenant boundary for institution administration and academic configuration.
- **Membership:** A role assignment within a specific institution or employer organization.
- **School / Faculty:** A top-level academic organizational unit in the institution hierarchy; UI labels may vary by institution.
- **Department:** Academic unit within a school.
- **Programme:** Degree/course offering associated with a department.
- **Cohort:** Student grouping associated with a programme and academic year.
- **Opportunity:** A published job or internship listing.
- **Application:** A student's application for an opportunity.
- **Placement:** An academic placement record created through the established placement workflow.
- **Report version:** A versioned submission linked to storage metadata.
- **Griffin evaluation:** A Kairos-tracked request to an external evaluation engine; completion requires validated external results.
- **Recruitment drive:** An institution-owned campus recruiting event with eligibility targeting and employer participation.
- **Audit event:** Append-only operational metadata for selected sensitive actions.
- **Best-effort notification:** Email sent after a successful business commit, without durable retry/outbox guarantees in the documented implementation.

---

## 24. Source documents consolidated

This guide consolidates information from the supplied documents:

- `ACADEMIC_ADMINISTRATION.md`
- `ASSESSMENT_OUTCOMES.md`
- `AUDIT.md`
- `authentication-and-onboarding.md`
- `AUTHENTICATION.md`
- `BACKEND_ARCHITECTURE_AUDIT.md`
- `CAMPUS_RECRUITMENT.md`
- `DASHBOARDS.md`
- `EMPLOYERS_AND_RECRUITMENT.md`
- `GRIFFIN_INTEGRATION.md`
- `IDENTITY_VERIFICATION.md`
- `identity-verification.md`
- `INSTITUTION_ONBOARDING.md`
- `INSTITUTION_REGISTRATION.md`
- `internship-module.md`
- `kairos_system_database_architecture_specification.md`
- `MODULARIZATION_MIGRATION_GUIDE.md`
- `NOTIFICATIONS.md`

When these documents conflict, prefer inspecting the current repository and migration history. Preserve explicit limitations until code, tests, schema, and deployment evidence justify changing them.

---

**Document status:** Consolidated product/workflow reference based on supplied project documents. Not a production certification, not a guarantee that every described endpoint is deployed, and not a replacement for the current source code, API schemas, migration history, or CI results.
