# Post-Internship Assessment Workflow — Design Note

## Canonical record relationships

The workflow reuses the existing internship placement, report submission, immutable report version, storage file, Griffin evaluation, student profile, faculty profile, institution, programme, cohort, and academic-year records. Each new report submission snapshots its institution, programme, cohort, academic year, and semester so later student/cohort edits do not silently move an assessment to a different academic context.

The presentation is an optional nullable column for legacy report versions, but new final packages and blind-assessment assignments require a PDF report and PPTX presentation. Existing report versions are not updated in place.

New records are additive: versioned institution/programme assessment policy; source-referenced curriculum outcomes; traceable mappings per report version; blind assessment assignments bound to exact report versions and policy snapshots; and revisioned internship academic results. Internship results remain a distinct academic component and never directly update student CGPA.

## State and result gates

The workflow is reconciled with the existing report lifecycle. Supervisor approval remains required before official result preview can become finalizable. Griffin remains a separate evaluation resource, and only a validated completed evaluation/result snapshot for the same report version is eligible as evidence. A missing Griffin contract does not invoke guessed live endpoints.

Curriculum outcomes must be loaded by an institution administrator from the real programme curriculum. Reviewers record a mapping status and traceable evidence; the system does not seed sample courses or outcomes. The versioned grading policy requires explicit component weights that total 100%, raw Griffin score maximum, credit for every supported curriculum mapping status, criteria/ranges, a complete grade-band scale, required independent evaluator count, passing threshold and final approver role. No default grading weights or scale conversions exist.

Result finalization is blocked until the approved policy and every required component are present. Finalization and publication are separate, idempotent operations. Publication is not allowed to silently replace an already published result because a dedicated correction/appeal process is not yet present.

## Blinding and access rules

Student self-service derives the student profile from the authenticated account. The evaluator packet is resolved only through the authenticated evaluator's own assignment. It returns a packet code, version, rubric snapshot, permitted reviewed mapping evidence only when the policy allows it, and generic file-download routes. Original file names and direct profile identifiers are not returned by the blind packet API. Download responses use generic file names, no-store, nosniff and validated MIME types. The UI warns that document content, comments and embedded metadata can still reveal identity; this implementation does not claim forensic anonymization.

Assignment selection is institution-scoped, requires active/verified faculty, excludes the placement supervisor and enforces the policy's exact evaluator count. Submitted criteria scores become immutable. Student result APIs return only that authenticated student's published results. Faculty result history is restricted to placements they supervise. Institution configuration APIs require an active institution-administrator permission.

## Explicit remaining dependencies

1. Griffin's authoritative base URL, authentication, request schema, dispatch contract, polling/callback behavior and result schema must be supplied before live dispatch can be enabled.
2. Each institution must load its approved programme/semester outcomes and configure the versioned grading policy before final results can be produced.
3. Existing submissions with missing academic-context snapshots remain viewable but cannot receive a final result until a new appropriately contextualized submission is created.
4. The institution's formal correction/appeal procedure is not represented in the current models. Published results are therefore not overwritten by generic update paths.
5. API-level blinding cannot remove identities embedded in the submitted document itself; document sanitization/redaction policy may require a further institutional decision.

No production migration is applied by this change.
