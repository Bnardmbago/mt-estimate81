import { cookies } from "next/headers";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import EstimateDetailContent from "@/components/EstimateDetailContent";
import { fetchEstimateResult } from "@/lib/estimate";

export const dynamic = "force-dynamic";

export default async function EstimateDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");
  const t = await getTranslations("estimates");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const result = await fetchEstimateResult(id, token.value, locale);

  if (result.status === "unauthorized") {
    redirect(`/${locale}/login`);
  }

  if (result.status === "not_found") {
    notFound();
  }

  if (result.status === "error") {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <h1 className="text-lg font-semibold">{t("loadError")}</h1>
        <p className="mt-2 text-sm">
          {t("loadErrorDetail", { status: result.httpStatus })}
        </p>
        <Link
          href={`/${locale}/estimates`}
          className="mt-4 inline-block text-sm font-medium text-blue-600 hover:underline"
        >
          {t("back")}
        </Link>
      </div>
    );
  }

  const estimate = result.data;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <EstimateDetailContent estimate={estimate} />
    </div>
  );
}
