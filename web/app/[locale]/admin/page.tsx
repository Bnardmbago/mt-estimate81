import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import RateCardEditor from "@/components/admin/RateCardEditor";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://api:8000";

export default async function AdminPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");
  const t = await getTranslations("admin");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const response = await fetch(`${API_URL}/admin/rate-cards/active`, {
    headers: { Cookie: `access_token=${token.value}` },
    cache: "no-store",
  });

  if (response.status === 403) {
    redirect(`/${locale}/estimates`);
  }

  if (response.status === 401) {
    redirect(`/${locale}/login`);
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h1 className="mb-6 text-2xl font-bold">{t("title")}</h1>
      <div className="mb-6 border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          <span className="border-b-2 border-blue-600 px-1 py-2 text-sm font-medium text-blue-600">
            {t("tabs.rateCards")}
          </span>
        </nav>
      </div>
      <RateCardEditor />
    </div>
  );
}
