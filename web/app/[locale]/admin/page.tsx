import { Suspense } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import AdminPanel from "@/components/admin/AdminPanel";
import { loginUrl } from "@/lib/authRedirect";
import { serverApiFetch } from "@/lib/server-api";

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
    redirect(loginUrl(locale, `/${locale}/admin`));
  }

  const response = await serverApiFetch("/admin/users", token.value);

  if (response.status === 403) {
    redirect(`/${locale}/estimates`);
  }

  if (response.status === 401) {
    redirect(loginUrl(locale, `/${locale}/admin`));
  }

  if (!response.ok) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-800">
        <h1 className="text-lg font-semibold">{t("loadError")}</h1>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h1 className="mb-6 text-2xl font-bold">{t("title")}</h1>
      <Suspense fallback={<p className="text-sm text-gray-500">{t("loading")}</p>}>
        <AdminPanel />
      </Suspense>
    </div>
  );
}
