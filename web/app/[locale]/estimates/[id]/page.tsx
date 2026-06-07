import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
import EstimateForm from "@/components/EstimateForm";
import { fetchEstimate } from "@/lib/estimate";

export default async function EstimateDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token");

  if (!token) {
    redirect(`/${locale}/login`);
  }

  const estimate = await fetchEstimate(id, token.value);

  if (!estimate) {
    notFound();
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <EstimateForm estimate={estimate} locale={locale} />
    </div>
  );
}
