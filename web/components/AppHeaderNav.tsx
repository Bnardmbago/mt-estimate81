"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { usePathname } from "@/i18n/navigation";
import type { AccountType } from "@/lib/user-types";

type NavLabels = {
  welcome: string;
  estimates: string;
  proposal: string;
  rateCards: string;
  help: string;
  admin: string;
};

type NavItem = {
  href: string;
  label: string;
  match: (pathname: string) => boolean;
};

type AppHeaderNavProps = {
  locale: string;
  isAuthenticated: boolean;
  isAdmin: boolean;
  accountType: AccountType;
  labels: NavLabels;
};

function MenuIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden
    >
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="20" y2="18" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-4 w-4"
      aria-hidden
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function navLinkClass(isActive: boolean, mobile = false) {
  const base = mobile ? "header-btn w-full justify-start" : "header-btn";
  return isActive ? `${base} header-btn-active` : base;
}

export default function AppHeaderNav({
  locale,
  isAuthenticated,
  isAdmin,
  accountType,
  labels,
}: AppHeaderNavProps) {
  const t = useTranslations("nav");
  const pathname = usePathname();
  const panelId = useId();
  const navRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const isContactUser = accountType === "contact";

  const items: NavItem[] = [
    {
      href: `/${locale}/welcome`,
      label: labels.welcome,
      match: (path) => path === "/welcome" || path.startsWith("/welcome/"),
    },
  ];

  if (isAuthenticated) {
    items.push({
      href: `/${locale}/estimates`,
      label: labels.estimates,
      match: (path) => path === "/estimates" || path.startsWith("/estimates/"),
    });

    if (!isContactUser) {
      items.push(
        {
          href: `/${locale}/proposal`,
          label: labels.proposal,
          match: (path) => path === "/proposal" || path.startsWith("/proposal/"),
        },
        {
          href: `/${locale}/rate-cards`,
          label: labels.rateCards,
          match: (path) => path === "/rate-cards" || path.startsWith("/rate-cards/"),
        },
        {
          href: `/${locale}/help`,
          label: labels.help,
          match: (path) => path === "/help" || path.startsWith("/help/"),
        },
      );
    }

    if (isAdmin) {
      items.push({
        href: `/${locale}/admin?tab=users`,
        label: labels.admin,
        match: (path) => path === "/admin" || path.startsWith("/admin/"),
      });
    }
  }

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (!navRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpen]);

  return (
    <div ref={navRef} className="flex min-w-0 flex-1 items-center gap-2">
      <button
        type="button"
        className="header-btn-icon md:hidden"
        aria-expanded={menuOpen}
        aria-controls={panelId}
        aria-label={menuOpen ? t("closeMenu") : t("openMenu")}
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? <CloseIcon /> : <MenuIcon />}
      </button>

      <nav
        aria-label="Main"
        className="hidden items-center gap-2 md:flex"
      >
        {items.map((item) => {
          const isActive = item.match(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={navLinkClass(isActive)}
              aria-current={isActive ? "page" : undefined}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>

      {menuOpen ? (
        <div
          id={panelId}
          className="absolute left-0 right-0 top-14 z-20 border-b border-gray-200 bg-white px-4 py-3 shadow-sm dark:border-gray-700 dark:bg-gray-900 md:hidden"
        >
          <nav aria-label="Main mobile" className="flex flex-col gap-2">
            {items.map((item) => {
              const isActive = item.match(pathname);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={navLinkClass(isActive, true)}
                  aria-current={isActive ? "page" : undefined}
                  onClick={() => setMenuOpen(false)}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      ) : null}
    </div>
  );
}
