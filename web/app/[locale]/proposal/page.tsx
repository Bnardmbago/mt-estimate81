import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Suspense } from "react";
import ProposalPageClient from "@/components/proposal/ProposalPageClient";
import { resolveAuthenticatedHome } from "@/lib/contact";
import type { UserProfile } from "@/lib/user-types";

export default async function ProposalPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token.value);
  if (profile.status === "ok" && profile.data.account_type === "contact") {
    redirect(await resolveAuthenticatedHome(locale, token.value));
  }

  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading…</div>}>
      <ProposalPageClient />
    </Suspense>
  );
}
