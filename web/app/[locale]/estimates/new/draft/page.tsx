import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import NewEstimateDraftClient from "@/components/NewEstimateDraftClient";
import { contactUrl } from "@/lib/authRedirect";
import { fetchEstimates } from "@/lib/estimate";
import type { UserProfile } from "@/lib/user-types";

export const dynamic = "force-dynamic";

export default async function NewEstimateDraftPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ template?: string }>;
}) {
  const { locale } = await params;
  const { template } = await searchParams;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(contactUrl(locale));
  }

  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token.value);
  if (profile.status === "ok" && profile.data.account_type === "contact") {
    const estimates = await fetchEstimates(token.value);
    if (estimates && estimates.length > 0) {
      redirect(`/${locale}/estimates/${estimates[0].id}`);
    }
    redirect(contactUrl(locale));
  }

  if (!template) {
    redirect(`/${locale}/estimates/new`);
  }

  const isAdmin = profile.status === "ok" && profile.data.is_admin;

  return <NewEstimateDraftClient templateId={template} isAdmin={isAdmin} />;
}
