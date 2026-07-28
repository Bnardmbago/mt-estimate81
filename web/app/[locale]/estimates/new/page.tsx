import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import NewEstimateForm from "@/components/NewEstimateForm";
import { contactUrl } from "@/lib/authRedirect";
import { fetchEstimates } from "@/lib/estimate";
import type { UserProfile } from "@/lib/user-types";

export default async function NewEstimatePage({
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

  if (template) {
    redirect(`/${locale}/estimates/new/draft?template=${encodeURIComponent(template)}`);
  }

  const t = await getTranslations("estimates");

  return (
    <div>
      <div className="mb-6">
        <Link
          href={`/${locale}/estimates`}
          className="mb-2 inline-block text-sm text-gray-500 hover:text-blue-600"
        >
          ← {t("back")}
        </Link>
        <h1 className="text-2xl font-semibold">{t("newEstimateTitle")}</h1>
      </div>
      <NewEstimateForm />
    </div>
  );
}
