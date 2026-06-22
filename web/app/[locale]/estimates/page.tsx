import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import EstimatesList from "@/components/EstimatesList";
import { loginUrl } from "@/lib/authRedirect";
import { fetchEstimates } from "@/lib/estimate";

export default async function EstimatesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const returnTo = `/${locale}/estimates`;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(loginUrl(locale, returnTo));
  }

  const t = await getTranslations("estimates");
  const estimates = await fetchEstimates(token.value);

  if (estimates === null) {
    redirect(loginUrl(locale, returnTo));
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("list")}</h1>
        <Link
          href={`/${locale}/estimates/new`}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {t("new")}
        </Link>
      </div>
      <EstimatesList estimates={estimates} locale={locale} />
    </div>
  );
}
