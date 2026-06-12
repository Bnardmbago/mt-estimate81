import { redirect } from "next/navigation";

export default async function LegacyVariancePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  redirect(`/${locale}/estimates`);
}
