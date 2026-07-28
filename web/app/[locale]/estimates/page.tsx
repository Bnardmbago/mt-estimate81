import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import EstimatesList from "@/components/EstimatesList";
import { contactUrl } from "@/lib/authRedirect";
import { fetchEstimates } from "@/lib/estimate";
import type { UserProfile } from "@/lib/user-types";

export default async function EstimatesPage({
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

  const estimates = await fetchEstimates(token.value);

  if (estimates === null) {
    redirect(contactUrl(locale));
  }

  if (profile.data.account_type === "contact") {
    if (estimates.length > 0) {
      redirect(`/${locale}/estimates/${estimates[0].id}`);
    }
    redirect(contactUrl(locale));
  }

  const t = await getTranslations("estimates");

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">{t("list")}</h1>
        <Link
          href={`/${locale}/estimates/new`}
          data-tour="estimates-new-button"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {t("new")}
        </Link>
      </div>
      <EstimatesList estimates={estimates} locale={locale} />
    </div>
  );
}
