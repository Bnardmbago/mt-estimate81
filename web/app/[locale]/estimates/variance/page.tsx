import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import VarianceDashboard from "@/components/VarianceDashboard";

export default async function VariancePage({
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

  return <VarianceDashboard locale={locale} />;
}
