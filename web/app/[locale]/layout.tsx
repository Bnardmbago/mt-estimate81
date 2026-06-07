import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import Link from "next/link";
import { routing, type Locale } from "@/i18n/routing";
import "../globals.css";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as Locale)) {
    notFound();
  }

  const messages = await getMessages();
  const t = await getTranslations("nav");
  const otherLocale = locale === "ja" ? "en" : "ja";

  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider messages={messages}>
          <header className="border-b border-gray-200 bg-white">
            <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
              <nav className="flex items-center gap-4 text-sm font-medium">
                <Link href={`/${locale}/estimates`} className="hover:text-blue-600">
                  {t("estimates")}
                </Link>
                <Link href={`/${locale}/admin`} className="hover:text-blue-600">
                  {t("admin")}
                </Link>
              </nav>
              <Link
                href={`/${otherLocale}/login`}
                className="rounded border border-gray-300 px-2 py-1 text-xs uppercase tracking-wide hover:bg-gray-100"
              >
                {otherLocale}
              </Link>
            </div>
          </header>
          <main className="mx-auto max-w-5xl px-4 py-8">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
