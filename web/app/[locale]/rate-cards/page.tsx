import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import RateCardEditor from "@/components/rate-cards/RateCardEditor";
import { resolveAuthenticatedHome } from "@/lib/contact";
import type { UserProfile } from "@/lib/user-types";

export default async function RateCardsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");
  const t = await getTranslations("rateCards");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const { serverApiJson } = await import("@/lib/server-api");
  const profile = await serverApiJson<UserProfile>("/auth/me", token.value);
  if (profile.status === "ok" && profile.data.account_type === "contact") {
    redirect(await resolveAuthenticatedHome(locale, token.value));
  }

  return (
    <div
      data-tour="rate-cards-editor"
      className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
    >
      <h1 className="text-2xl font-bold">{t("pageTitle")}</h1>
      <p className="mt-2 text-sm text-gray-500">{t("pageDescription")}</p>
      <div className="mt-6">
        <RateCardEditor />
      </div>
    </div>
  );
}
