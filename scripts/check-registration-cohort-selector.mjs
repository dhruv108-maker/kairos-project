import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const registration = readFileSync("src/views/auth/auth2/register/index.tsx", "utf8");
const institutionRouter = readFileSync("backend/app/modules/institutions/router.py", "utf8");
const authRouter = readFileSync("backend/app/api/auth.py", "utf8");

// Cohort IDs are API-backed form values, never free-text fields in signup.
assert.doesNotMatch(registration, /<Input[^>]*(?:id|name)=["']cohort_id["']/i);
assert.doesNotMatch(registration, /<Input[^>]*(?:cohort\s*id|cohort_id)/i);
assert.doesNotMatch(registration, /(?:enter|type|obtain|ask for)\s+(?:your\s+)?cohort\s*id/i);
assert.match(registration, /<Select value=\{cohortId\}/);
assert.match(registration, /<SelectItem key=\{cohort\.id\} value=\{cohort\.id\}>\{cohort\.name\}/);
assert.match(registration, /cohort_id:\s*cohortId/);

// Only fetch choices after exact verified-domain resolution, cancel stale requests,
// and discard any selected ID absent from the latest API response.
assert.match(registration, /if \(!institutionId \|\| !verifiedDomainMatch\)/);
assert.match(registration, /return \(\) => \{ cancelled = true; \}/);
assert.match(registration, /setCohortId\(\(selected\) => result\.cohorts\.some/);
assert.match(registration, /Retry loading cohorts/);
assert.match(registration, /contact your institution administrator/i);

// Backend options are scoped to active institution structures, active cohorts,
// and the current academic year; registration repeats those checks independently.
assert.match(institutionRouter, /AcademicYear\.is_current\.is_\(True\)/);
assert.match(institutionRouter, /Cohort\.is_active\.is_\(True\)/);
assert.match(authRouter, /Cohort\.id == payload\.cohort_id/);
assert.match(authRouter, /AcademicYear\.is_current\.is_\(True\)/);
assert.match(authRouter, /Cohort\.is_active\.is_\(True\)/);

console.log("Registration cohort selector acceptance checks passed.");
