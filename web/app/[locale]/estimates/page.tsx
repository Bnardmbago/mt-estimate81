import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";

export default async function EstimatesPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const t = await getTranslations("estimates");

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">{t("list")}</h1>
        <button
          type="button"
          disabled
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white opacity-50"
        >
          {t("new")}
        </button>
      </div>
      <p className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center text-gray-500">
        {t("empty")}
      </p>
    </div>
  );
}
