import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import RateCardEditor from "@/components/rate-cards/RateCardEditor";

export default async function RateCardDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");
  const t = await getTranslations("rateCards");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <Link
        href={`/${locale}/rate-cards`}
        className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
      >
        {t("allCardsList.backToList")}
      </Link>
      <h1 className="mt-3 text-2xl font-bold">{t("allCardsList.detailTitle")}</h1>
      <p className="mt-1 text-sm text-gray-500">{t("allCardsList.detailDescription")}</p>
      <div className="mt-6">
        <RateCardEditor initialCardId={id} showAllCardsList={false} />
      </div>
    </div>
  );
}
