import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const registration = readFileSync("src/views/auth/auth2/register/index.tsx", "utf8");
const institutionRouter = readFileSync("backend/app/modules/institutions/router.py", "utf8");
const authRouter = readFileSync("backend/app/api/auth.py", "utf8");
const schemas = readFileSync("backend/app/api/schemas.py", "utf8");

for (const field of ["School / Faculty", "Department", "Programme / Course"]) {
  assert.ok(registration.includes(field), `registration field missing: ${field}`);
}
for (const contract of ["school_id: schoolId", "department_id: departmentId", "programme_id: programmeId"]) {
  assert.ok(registration.includes(contract), `registration payload missing: ${contract}`);
}
assert.ok(registration.includes("selectedDepartments.map((department)"));
assert.ok(registration.includes("selectedProgrammes.map((programme)"));
assert.ok(!/name=["'](?:school_id|department_id|cohort_id)["']/.test(registration), "IDs must not be manually entered");
assert.ok(registration.includes("Your institution can assign your cohort after registration"));
assert.ok(registration.includes("academicOptionsErrorMessage"));
assert.ok(registration.includes("Retry loading academic options"));
assert.ok(registration.includes("isAcademicOptions"));
assert.ok(!registration.includes("programme.degree_level"), "optional degree metadata must not be required by the UI");

assert.ok(institutionRouter.includes('"schools": [{"id": str(row.id), "name": row.name, "code": row.code} for row in schools]'));
assert.ok(institutionRouter.includes('"school_id": str(row.school_id)'));
assert.ok(institutionRouter.includes('"programmes": [{"id": str(row.id), "name": row.name, "code": row.code, "department_id": str(row.department_id)} for row in programmes]'));
assert.ok(institutionRouter.includes('func.upper(Programme.status) == "ACTIVE"'));
assert.ok(!institutionRouter.includes("Cohort.academic_year_id"), "cohort schema must not block registration options");
assert.ok(institutionRouter.includes('"cohorts": []'));
assert.ok(authRouter.includes("Department.id == payload.department_id"));
assert.ok(authRouter.includes("School.id == payload.school_id"));
assert.ok(authRouter.includes("func.upper(Programme.status) == "ACTIVE""));
assert.ok(schemas.includes("programme_id: str | None = Field(default=None"));
assert.ok(schemas.includes("cohort_id: str | None = Field(default=None"));

console.log("Registration academic-options regression checks passed.");
