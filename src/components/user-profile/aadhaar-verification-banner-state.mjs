const COPY = {
  not_started: {
    title: "Complete your identity verification",
    description:
      "Keep your Kairos profile up to date by completing optional Aadhaar identity verification. You can continue using Kairos without completing this step.",
    action: "Verify Aadhaar",
  },
  pending: {
    title: "Your identity verification is pending",
    description: "Your identity verification is pending. Check your verification status.",
    action: "Check status",
  },
  failed: {
    title: "Your verification is not complete",
    description: "Your verification is not complete. Review the status and retry if available.",
    action: "Review verification",
  },
  expired: {
    title: "Your verification is not complete",
    description: "Your verification is not complete. Review the status and retry if available.",
    action: "Review verification",
  },
  cancelled: {
    title: "Your verification is not complete",
    description: "Your verification is not complete. Review the status and retry if available.",
    action: "Review verification",
  },
  review_required: {
    title: "Your identity verification needs review",
    description: "Your identity verification requires further review. View the current status.",
    action: "View status",
  },
};

export function getAadhaarBannerContent(status) {
  if (status?.status === "verified" && status.verified === true) return null;
  const key = COPY[status?.status] ? status.status : "not_started";
  return COPY[key];
}
