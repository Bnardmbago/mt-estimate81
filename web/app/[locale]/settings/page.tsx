import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import SettingsPageClient from "@/components/settings/SettingsPageClient";
import { contactUrl } from "@/lib/authRedirect";
import type { UserProfile } from "@/lib/user-types";

export default async function SettingsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(contactUrl(locale));
  }

  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token.value);
  if (profile.status !== "ok") {
    redirect(contactUrl(locale));
  }

  return (
    <div className="px-4 py-8">
      <SettingsPageClient locale={locale} profile={profile.data} />
    </div>
  );
}
