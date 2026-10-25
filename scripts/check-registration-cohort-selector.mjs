import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const registration = readFileSync("src/views/auth/auth2/register/index.tsx", "utf8");
const institutionRouter = readFileSync("backend/app/modules/institutions/router.py", "utf8");
const authRouter = readFileSync("backend/app/api/auth.py", "utf8");
const schemas = readFileSync("backend/app/api/schemas.py", "utf8");
const apiClient = readFileSync("src/api/kairos-client.ts", "utf8");

for (const field of ["School / Faculty", "Department", "Programme / Course"]) {
  assert.ok(registration.includes(field), `registration field missing: ${field}`);
}
for (const contract of ["school_id: String(schoolId)", "department_id: String(departmentId)", "programme_id: String(programmeId)"]) {
  assert.ok(registration.includes(contract), `registration payload missing: ${contract}`);
}
assert.ok(registration.includes("selectedDepartments.map((department)"));
assert.ok(registration.includes("selectedProgrammes.map((programme)"));
assert.ok(registration.includes('institution_id: String(institutionId)'), "faculty registration must retain its optional institution ID");
assert.ok(registration.includes("const common = { email: submittedEmail, password, full_name: fullName };"), "student registration must let the backend resolve institution from the verified email domain");
assert.ok(registration.includes('school_id: String(schoolId)'), "school ID must be serialized as a string");
assert.ok(registration.includes('department_id: String(departmentId)'), "department ID must be serialized as a string");
assert.ok(registration.includes('programme_id: String(programmeId)'), "programme ID must be serialized as a string");
assert.ok(registration.includes('password !== confirmPassword'), "password confirmation must be checked locally");
assert.ok(!registration.includes('confirm_password: confirmPassword'), "password confirmation must not be sent to the API");
assert.ok(registration.includes("academicOptionLabel(school.name, school.code, school.id)"));
assert.ok(registration.includes("academicOptionLabel(department.name, department.code, department.id)"));
assert.ok(registration.includes("academicOptionLabel(programme.name, programme.code, programme.id)"));
assert.ok(apiClient.includes("validationErrors: ApiValidationError[]"));
assert.ok(apiClient.includes("location ? `${location}: ${item.msg}` : item.msg"), "validation errors must include their backend field location");
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
assert.ok(!institutionRouter.includes("Cohort.academic_year_id"), "cohort options must not require optional academic-year columns");
assert.ok(institutionRouter.includes("Cohort.is_active.is_(True)"), "only active cohorts should be offered");
assert.ok(institutionRouter.includes('"cohorts": ['), "the registration API must return active cohort options");
assert.ok(institutionRouter.includes('"programme_id": str(row.programme_id)'), "cohort choices must preserve programme association");
assert.ok(authRouter.includes("WHERE d.id = :department_id"), "registration must resolve the department through the parameterized SQL contract");
assert.ok(authRouter.includes("str(payload.institution_id) != str(resolved_institution_id)"), "backend must compare explicitly supplied institution IDs without assuming numeric identifiers");
assert.ok(authRouter.includes("AND s.id = :school_id"), "department selection must be constrained to the selected school");
assert.ok(authRouter.includes("LOWER(p.status) = 'active'"), "registration must accept only active programmes using the SQL contract");
assert.ok(schemas.includes("programme_id: str | None = Field(default=None"));
assert.ok(schemas.includes("cohort_id: str | None = Field(default=None"));


const authFrame = readFileSync("src/components/auth/AuthFrame.tsx", "utf8");
const fullLogo = readFileSync("src/layouts/full/shared/logo/FullLogo.tsx", "utf8");
const sidebarLogo = readFileSync("src/layouts/full/shared/logo/Logo.tsx", "utf8");
assert.equal((authFrame.match(/<FullLogo linked=\{false\} \/>/g) ?? []).length, 1, "the single auth-frame brand link must use presentational logo markup");
assert.ok(authFrame.includes('to={brandHref}'), "AuthFrame must preserve its configured brand destination");
assert.ok(fullLogo.includes("linked = true"), "standalone FullLogo must remain linked by default");
assert.ok(fullLogo.includes('to="/"'), "standalone FullLogo must navigate home");
assert.ok(sidebarLogo.includes('<Link') && sidebarLogo.includes('<img'), "sidebar logo remains a home link");
assert.ok(!sidebarLogo.includes("SidebarMenuButton"), "sidebar logo must not nest a button inside its link");
console.log("Registration and logo navigation regression checks passed.");
