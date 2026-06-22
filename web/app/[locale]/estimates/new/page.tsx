import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getTranslations } from "next-intl/server";
import NewEstimateForm from "@/components/NewEstimateForm";
import { loginUrl } from "@/lib/authRedirect";
import { createEstimate } from "@/lib/estimate";

export default async function NewEstimatePage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ template?: string }>;
}) {
  const { locale } = await params;
  const { template } = await searchParams;
  const returnTo = template
    ? `/${locale}/estimates/new?template=${encodeURIComponent(template)}`
    : `/${locale}/estimates/new`;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(loginUrl(locale, returnTo));
  }

  if (template) {
    const estimate = await createEstimate(locale, token.value, template);

    if (!estimate) {
      redirect(`/${locale}/estimates`);
    }

    redirect(`/${locale}/estimates/${estimate.id}`);
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
