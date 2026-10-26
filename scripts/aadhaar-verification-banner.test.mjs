import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import { getAadhaarBannerContent } from "../src/components/user-profile/aadhaar-verification-banner-state.mjs";

test("missing identity record is treated as not started", () => {
  assert.equal(getAadhaarBannerContent(null)?.action, "Verify Aadhaar");
  assert.match(getAadhaarBannerContent(null)?.description ?? "", /optional Aadhaar identity verification/i);
});

test("verified identity suppresses the promotion banner", () => {
  assert.equal(getAadhaarBannerContent({ status: "verified", identity_verified: true }), null);
});

test("pending state uses status-check wording", () => {
  const content = getAadhaarBannerContent({ status: "pending", identity_verified: false });
  assert.equal(content?.action, "Check status");
  assert.match(content?.description ?? "", /verification is pending/i);
});

test("failed, expired, and cancelled states offer a review/retry path", () => {
  for (const status of ["failed", "expired", "cancelled"]) {
    const content = getAadhaarBannerContent({ status, identity_verified: false });
    assert.equal(content?.action, "Review verification");
    assert.match(content?.description ?? "", /retry if available/i);
  }
});

test("review-required state explains further review", () => {
  const content = getAadhaarBannerContent({ status: "review_required", identity_verified: false });
  assert.equal(content?.action, "View status");
  assert.match(content?.description ?? "", /requires further review/i);
});

test("banner uses authenticated API status and the existing profile route", async () => {
  const [component, layout] = await Promise.all([
    readFile(new URL("../src/components/user-profile/AadhaarVerificationBanner.tsx", import.meta.url), "utf8"),
    readFile(new URL("../src/layouts/full/FullLayout.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(component, /apiRequest<VerificationStatusResponse \| null>\("\/identity-verification\/status"/);
  assert.match(component, /to="\/student\/profile"/);
  assert.match(component, /catch\(\(\) =>/);
  assert.match(layout, /AadhaarVerificationBanner/);
  assert.match(layout, /account && !allowAnonymous && account\.roles\.some/);
});
