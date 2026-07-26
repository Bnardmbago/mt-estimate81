import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import InternalDossierClient from "@/components/internal/InternalDossierClient";
import { contactUrl } from "@/lib/authRedirect";
import type { UserProfile } from "@/lib/user-types";

export const dynamic = "force-dynamic";

export default async function InternalDossierPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(contactUrl(locale));
  }

  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token.value);

  if (profile.status === "unauthorized") {
    redirect(contactUrl(locale));
  }

  if (profile.status !== "ok" || !profile.data.is_admin) {
    redirect(`/${locale}/estimates/${id}`);
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-900">
      <InternalDossierClient estimateId={id} locale={locale} />
    </div>
  );
}
