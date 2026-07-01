"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import AdminHelpReference from "@/components/admin/AdminHelpReference";
import AiSettingsPanel from "@/components/admin/AiSettingsPanel";
import DiscountSettingsPanel from "@/components/admin/DiscountSettingsPanel";
import FormTemplatesPanel from "@/components/admin/FormTemplatesPanel";
import FormulasReference from "@/components/admin/FormulasReference";
import SmtpSettingsPanel from "@/components/admin/SmtpSettingsPanel";
import SystemHealthPanel from "@/components/admin/SystemHealthPanel";
import UserManager from "@/components/admin/UserManager";

type AdminTab =
  | "users"
  | "formTemplates"
  | "discountSettings"
  | "aiSettings"
  | "smtpSettings"
  | "formulas"
  | "help"
  | "system";

const tabs: AdminTab[] = [
  "users",
  "formTemplates",
  "discountSettings",
  "aiSettings",
  "smtpSettings",
  "formulas",
  "help",
  "system",
];

function isAdminTab(value: string | null): value is AdminTab {
  return tabs.includes(value as AdminTab);
}

function tabButtonClass(isActive: boolean) {
  return isActive ? "header-btn header-btn-active" : "header-btn";
}

export default function AdminPanel() {
  const t = useTranslations("admin");
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const activeTab: AdminTab = isAdminTab(tabParam) ? tabParam : "users";

  const tabLabels: Record<AdminTab, string> = {
    users: t("tabs.users"),
    formTemplates: t("tabs.formTemplates"),
    discountSettings: t("tabs.discountSettings"),
    aiSettings: t("tabs.aiSettings"),
    smtpSettings: t("tabs.smtpSettings"),
    formulas: t("tabs.formulas"),
    help: t("tabs.help"),
    system: t("tabs.system"),
  };

  function setActiveTab(tab: AdminTab) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    router.replace(`?${params.toString()}`, { scroll: false });
  }

  return (
    <>
      <nav
        className="mb-6 flex flex-wrap gap-2"
        aria-label={t("title")}
      >
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            aria-current={activeTab === tab ? "page" : undefined}
            className={tabButtonClass(activeTab === tab)}
          >
            {tabLabels[tab]}
          </button>
        ))}
      </nav>

      {activeTab === "users" && <UserManager />}
      {activeTab === "formTemplates" && <FormTemplatesPanel />}
      {activeTab === "discountSettings" && <DiscountSettingsPanel />}
      {activeTab === "aiSettings" && <AiSettingsPanel />}
      {activeTab === "smtpSettings" && <SmtpSettingsPanel />}
      {activeTab === "formulas" && <FormulasReference />}
      {activeTab === "help" && <AdminHelpReference />}
      {activeTab === "system" && <SystemHealthPanel />}
    </>
  );
}
