import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";
import { routing, type Locale } from "@/i18n/routing";
import AppHeader from "@/components/AppHeader";
import TourProvider from "@/components/tour/TourProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import ThemeScript from "@/components/ThemeScript";
import type { AccountType } from "@/lib/user-types";
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
  const cookieStore = await cookies();
  const token = cookieStore.get("access_token")?.value;
  const isAuthenticated = Boolean(token);
  let isAdmin = false;
  let accountType: AccountType = "full";

  if (isAuthenticated && token) {
    const { serverApiJson } = await import("@/lib/server-api");
    const profile = await serverApiJson<{
      is_admin: boolean;
      is_active: boolean;
      account_type: AccountType;
    }>("/auth/me", token);
    if (profile.status === "ok") {
      isAdmin = profile.data.is_admin && profile.data.is_active;
      accountType = profile.data.account_type ?? "full";
    }
  }

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body>
        <NextIntlClientProvider messages={messages}>
          <ThemeProvider>
            <TourProvider
              isAuthenticated={isAuthenticated}
              isAdmin={isAdmin}
              accountType={accountType}
            >
              <AppHeader
                locale={locale}
                isAuthenticated={isAuthenticated}
                isAdmin={isAdmin}
                accountType={accountType}
              />
              <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
            </TourProvider>
          </ThemeProvider>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
