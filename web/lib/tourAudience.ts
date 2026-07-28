import type { AccountType } from "@/lib/user-types";

export type TourAudience = "contact" | "user" | "admin";

export function resolveTourAudience(input: {
  accountType: AccountType;
  isAdmin: boolean;
}): TourAudience {
  if (input.accountType === "contact") return "contact";
  if (input.isAdmin) return "admin";
  return "user";
}
