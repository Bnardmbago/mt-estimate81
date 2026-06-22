import { getTranslations } from "next-intl/server";
import AppHeaderNav from "@/components/AppHeaderNav";
import LocaleSwitcher from "@/components/LocaleSwitcher";
import LogoutButton from "@/components/LogoutButton";
import ThemeToggle from "@/components/ThemeToggle";

type AppHeaderProps = {
  locale: string;
  isAuthenticated: boolean;
  isAdmin?: boolean;
};

export default async function AppHeader({
  locale,
  isAuthenticated,
  isAdmin = false,
}: AppHeaderProps) {
  const t = await getTranslations("nav");

  return (
    <header className="relative border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-3 px-4">
        <AppHeaderNav
          locale={locale}
          isAuthenticated={isAuthenticated}
          isAdmin={isAdmin}
          labels={{
            welcome: t("welcome"),
            estimates: t("estimates"),
            rateCards: t("rateCards"),
            proofOfConcept: t("proofOfConcept"),
            help: t("help"),
            admin: t("admin"),
          }}
        />
        <div className="flex shrink-0 items-center gap-2">
          <ThemeToggle />
          <LocaleSwitcher />
          {isAuthenticated && <LogoutButton locale={locale} />}
        </div>
      </div>
    </header>
  );
}
