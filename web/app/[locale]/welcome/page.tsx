import { getTranslations } from "next-intl/server";
import WelcomePageContent from "@/components/welcome/WelcomePageContent";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "welcome" });

  return {
    title: t("title"),
  };
}

export default function WelcomePage() {
  return <WelcomePageContent />;
}
