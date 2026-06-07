import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { createEstimate } from "@/lib/estimate";

export default async function NewEstimatePage({
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

  const estimate = await createEstimate(locale, token.value);

  if (!estimate) {
    redirect(`/${locale}/estimates`);
  }

  redirect(`/${locale}/estimates/${estimate.id}`);
}
