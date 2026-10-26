export type AadhaarBannerStatus = {
  status: "not_started" | "pending" | "verified" | "failed" | "expired" | "cancelled" | "review_required";
  verified: boolean;
};

export type AadhaarBannerContent = {
  title: string;
  description: string;
  action: string;
};

export function getAadhaarBannerContent(
  status: AadhaarBannerStatus | null | undefined,
): AadhaarBannerContent | null;
