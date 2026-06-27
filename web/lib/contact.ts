import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { fetchEstimates } from "@/lib/estimate";
import type { UserProfile } from "@/lib/user-types";

export async function resolveAuthenticatedHome(locale: string, token: string): Promise<string> {
  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token);

  if (profile.status === "ok" && profile.data.account_type === "contact") {
    const estimates = await fetchEstimates(token);
    if (estimates && estimates.length > 0) {
      return `/${locale}/estimates/${estimates[0].id}`;
    }
    return `/${locale}/contact`;
  }

  return `/${locale}/estimates`;
}

export async function redirectAuthenticatedHome(locale: string): Promise<void> {
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  if (!token) {
    redirect(`/${locale}/contact`);
  }
  redirect(await resolveAuthenticatedHome(locale, token));
}
