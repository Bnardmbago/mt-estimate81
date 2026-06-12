import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import RateCardEditor from "@/components/rate-cards/RateCardEditor";

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

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold">{t("pageTitle")}</h1>
      <p className="mt-2 text-sm text-gray-500">{t("pageDescription")}</p>
      <div className="mt-6">
        <RateCardEditor />
      </div>
    </div>
  );
}
