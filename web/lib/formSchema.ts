import { FORM_FIELDS, isUsableProjectName } from "@/lib/formFields";

export type LocalizedText = {
  en: string;
  ja: string;
};

export type SelectOptionSchema = {
  value: string;
  label: LocalizedText;
};

export type FormFieldSchema = {
  key: string;
  type: "text" | "textarea" | "select" | "number" | "currency";
  required: boolean;
  sort_order: number;
  section?: "header" | "specification";
  label: LocalizedText;
  description?: LocalizedText;
  placeholder?: LocalizedText;
  options?: SelectOptionSchema[];
};

const DELIVERY_SCHEDULE_OPTIONS: SelectOptionSchema[] = [
  { value: "asap", label: { en: "ASAP", ja: "できるだけ早く" } },
  { value: "within_1_3_months", label: { en: "Within 1–3 months", ja: "1〜3か月以内" } },
  { value: "within_3_6_months", label: { en: "Within 3–6 months", ja: "3〜6か月以内" } },
  { value: "within_6_12_months", label: { en: "Within 6–12 months", ja: "6〜12か月以内" } },
  { value: "over_12_months", label: { en: "Over 12 months", ja: "12か月以上" } },
  { value: "flexible", label: { en: "Flexible", ja: "未定・相談したい" } },
];

const TIMELINE_PLANNING_OPTIONS: SelectOptionSchema[] = [
  {
    value: "match_schedule",
    label: { en: "Match desired schedule", ja: "希望納期に合わせる" },
  },
  {
    value: "fastest_parallel",
    label: { en: "Fastest parallel plan", ja: "最短（役割並行）" },
  },
];

const USAGE_PLATFORM_OPTIONS: SelectOptionSchema[] = [
  { value: "web_browser", label: { en: "Web Browser", ja: "Webブラウザ" } },
  { value: "iphone_app", label: { en: "iOS (iPhone app)", ja: "iOS（iPhoneアプリ）" } },
  { value: "android_app", label: { en: "Android app", ja: "Androidアプリ" } },
  { value: "cross_platform", label: { en: "Cross Platform", ja: "クロスプラットフォーム" } },
  { value: "mobile_only", label: { en: "Mobile Only", ja: "モバイルのみ" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const TARGET_USERS_OPTIONS: SelectOptionSchema[] = [
  { value: "internal_staff", label: { en: "Internal staff", ja: "社内スタッフ" } },
  { value: "external_customers", label: { en: "External customers", ja: "外部顧客" } },
  {
    value: "both_internal_external",
    label: { en: "Both internal and external users", ja: "社内・外部の両方" },
  },
  { value: "partners", label: { en: "Partners / vendors", ja: "パートナー / 取引先" } },
  { value: "general_public", label: { en: "General public", ja: "一般公開" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const PAYMENT_NEEDED_OPTIONS: SelectOptionSchema[] = [
  { value: "none", label: { en: "Not needed", ja: "不要" } },
  { value: "bank_transfer", label: { en: "Bank transfer only", ja: "銀行振込のみ" } },
  { value: "credit_card", label: { en: "Credit card only", ja: "クレジットカードのみ" } },
  {
    value: "both",
    label: { en: "Bank transfer and credit card", ja: "銀行振込とクレジットカード" },
  },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const NATURE_OF_WORK_OPTIONS: SelectOptionSchema[] = [
  { value: "new_build", label: { en: "New build", ja: "新規開発" } },
  { value: "enhancement", label: { en: "Enhancement", ja: "機能追加・改修" } },
  { value: "replacement", label: { en: "Replacement", ja: "リプレース" } },
  { value: "migration", label: { en: "Migration", ja: "移行" } },
  { value: "integration", label: { en: "Integration", ja: "システム連携" } },
  { value: "general", label: { en: "General", ja: "汎用" } },
];

const BUSINESS_DOMAIN_OPTIONS: SelectOptionSchema[] = [
  { value: "retail", label: { en: "Retail", ja: "小売" } },
  { value: "finance", label: { en: "Finance", ja: "金融" } },
  { value: "healthcare", label: { en: "Healthcare", ja: "医療・ヘルスケア" } },
  { value: "manufacturing", label: { en: "Manufacturing", ja: "製造" } },
  { value: "logistics", label: { en: "Logistics", ja: "物流" } },
  { value: "education", label: { en: "Education", ja: "教育" } },
  { value: "government", label: { en: "Government", ja: "公共・行政" } },
  { value: "it_saas", label: { en: "IT / SaaS", ja: "IT / SaaS" } },
  { value: "other", label: { en: "Other", ja: "その他" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const DEVELOPMENT_APPROACH_OPTIONS: SelectOptionSchema[] = [
  { value: "traditional", label: { en: "Traditional", ja: "従来型" } },
  { value: "ai_assisted", label: { en: "AI-assisted", ja: "AI支援" } },
  { value: "hybrid", label: { en: "Hybrid", ja: "ハイブリッド" } },
  { value: "low_code", label: { en: "Low-code", ja: "ローコード" } },
];

const MAINTENANCE_SUPPORT_OPTIONS: SelectOptionSchema[] = [
  { value: "none", label: { en: "None", ja: "なし" } },
  { value: "best_effort", label: { en: "Best effort", ja: "ベストエフォート" } },
  { value: "business_hours", label: { en: "Business hours support", ja: "営業時間内サポート" } },
  { value: "sla_24x7", label: { en: "24/7 SLA support", ja: "24時間365日SLA" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const MVP_SCOPE_OPTIONS: SelectOptionSchema[] = [
  { value: "mvp", label: { en: "MVP only", ja: "MVPのみ" } },
  { value: "full_release", label: { en: "Full release", ja: "フルリリース" } },
  { value: "phased", label: { en: "Phased rollout", ja: "段階的リリース" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const AUTH_COMPLEXITY_OPTIONS: SelectOptionSchema[] = [
  { value: "none", label: { en: "Not needed", ja: "不要" } },
  { value: "simple_login", label: { en: "Simple login", ja: "シンプルなログイン" } },
  { value: "sso", label: { en: "SSO / enterprise auth", ja: "SSO / エンタープライズ認証" } },
  { value: "multi_tenant", label: { en: "Multi-tenant", ja: "マルチテナント" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const DATA_MIGRATION_OPTIONS: SelectOptionSchema[] = [
  { value: "no", label: { en: "No", ja: "いいえ" } },
  { value: "yes_limited", label: { en: "Yes, limited migration", ja: "あり（限定的）" } },
  { value: "yes_major", label: { en: "Yes, major migration", ja: "あり（大規模）" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const COMPLIANCE_LEVEL_OPTIONS: SelectOptionSchema[] = [
  { value: "none", label: { en: "None", ja: "なし" } },
  {
    value: "standard",
    label: { en: "Standard (e.g. privacy, audit logs)", ja: "標準（プライバシー、監査ログ等）" },
  },
  { value: "regulated", label: { en: "Regulated (e.g. HIPAA, PCI)", ja: "規制対象（HIPAA、PCI等）" } },
  { value: "undecided", label: { en: "Undecided", ja: "未定" } },
];

const COMPLEXITY_OPTIONS: SelectOptionSchema[] = [
  { value: "low", label: { en: "Low / Simple", ja: "低 / シンプル" } },
  { value: "medium", label: { en: "Medium", ja: "中" } },
  { value: "high", label: { en: "High", ja: "高" } },
];

const SELECT_FIELD_OPTIONS: Partial<Record<string, SelectOptionSchema[]>> = {
  delivery_schedule: DELIVERY_SCHEDULE_OPTIONS,
  timeline_planning: TIMELINE_PLANNING_OPTIONS,
  usage_platform: USAGE_PLATFORM_OPTIONS,
  target_users: TARGET_USERS_OPTIONS,
  payment_needed: PAYMENT_NEEDED_OPTIONS,
  nature_of_work: NATURE_OF_WORK_OPTIONS,
  business_domain: BUSINESS_DOMAIN_OPTIONS,
  development_approach: DEVELOPMENT_APPROACH_OPTIONS,
  maintenance_support: MAINTENANCE_SUPPORT_OPTIONS,
  mvp_scope: MVP_SCOPE_OPTIONS,
  auth_complexity: AUTH_COMPLEXITY_OPTIONS,
  data_migration_needed: DATA_MIGRATION_OPTIONS,
  compliance_level: COMPLIANCE_LEVEL_OPTIONS,
  data_complexity: COMPLEXITY_OPTIONS,
  ui_complexity: COMPLEXITY_OPTIONS,
};

const KNOWN_FIELD_TYPE_PATCHES: Partial<Record<string, FormFieldSchema["type"]>> = {
  desired_system: "text",
  usage_platform: "select",
  target_users: "select",
  payment_needed: "select",
  expected_user_count: "number",
  concurrent_users: "number",
  delivery_schedule: "select",
  timeline_planning: "select",
  client_budget: "currency",
  nature_of_work: "select",
  business_domain: "select",
  development_approach: "select",
  maintenance_support: "select",
  mvp_scope: "select",
  auth_complexity: "select",
  data_migration_needed: "select",
  compliance_level: "select",
  integration_count: "number",
  data_complexity: "select",
  ui_complexity: "select",
};

const FIELD_PLACEHOLDERS: Partial<Record<string, LocalizedText>> = {
  desired_system: {
    en: "e.g. Customer portal, internal dashboard, mobile ordering app",
    ja: "例: 顧客ポータル、社内ダッシュボード、モバイル注文アプリ",
  },
  expected_user_count: { en: "e.g. 1000", ja: "例: 1000" },
  concurrent_users: { en: "e.g. 100", ja: "例: 100" },
  client_budget: { en: "e.g. 5000000", ja: "例: 5000000" },
  problem_to_solve: {
    en: "e.g. Reduce manual data entry and improve customer response time",
    ja: "例: 手作業の入力作業を減らし、顧客対応時間を短縮したい",
  },
  required_features: {
    en: "One feature per line (e.g. login, search, reporting)",
    ja: "1行に1機能（例: ログイン、検索、レポート）",
  },
  scope_boundaries: {
    en: "In scope: … / Out of scope: …",
    ja: "対象: … / 対象外: …",
  },
  non_functional_needs: {
    en: "e.g. security, performance, availability, scalability",
    ja: "例: セキュリティ、性能、可用性、拡張性",
  },
  integrations: {
    en: "One system per line or comma-separated",
    ja: "1行1システム、またはカンマ区切り",
  },
  integration_count: {
    en: "e.g. 3",
    ja: "例: 3",
  },
  technology_preferences: {
    en: "e.g. React, PostgreSQL, AWS (optional)",
    ja: "例: React、PostgreSQL、AWS（任意）",
  },
  rules_and_standards: {
    en: "e.g. GDPR, internal security policy, accessibility standards",
    ja: "例: GDPR、社内セキュリティポリシー、アクセシビリティ基準",
  },
  team_and_resources: {
    en: "e.g. 2 engineers, part-time designer, client-side PM",
    ja: "例: エンジニア2名、パートタイムデザイナー、クライアント側PM",
  },
  risks_unknowns: {
    en: "e.g. legacy API docs missing, vendor timeline uncertain",
    ja: "例: 既存API仕様書なし、ベンダー納期未定",
  },
  delivery_timing: {
    en: "Key milestones, fixed dates, dependencies",
    ja: "主要マイルストーン、固定日、依存関係",
  },
};

export type FormValidationMessages = {
  required: string;
  invalidNumber: string;
  invalidCurrency: string;
};

const LEGACY_LABELS: Record<string, LocalizedText> = {
  nature_of_work: { en: "Nature of work", ja: "作業の性質" },
  scope_boundaries: { en: "Scope boundaries", ja: "スコープ境界" },
  mvp_scope: { en: "Delivery scope", ja: "リリース範囲" },
  project_overview: { en: "Project overview", ja: "プロジェクト概要" },
  system_type: { en: "Type of system", ja: "システム種別" },
  business_domain: { en: "Business domain", ja: "業界・ドメイン" },
  main_functional_needs: { en: "Main functional needs", ja: "主要機能要件" },
  non_functional_needs: { en: "Non-functional needs", ja: "非機能要件" },
  users_and_load: { en: "Users and load", ja: "ユーザー数・負荷" },
  integrations: { en: "Connections to other systems", ja: "他システム連携" },
  integration_count: { en: "Number of integrations", ja: "連携システム数" },
  data_complexity: { en: "Data complexity", ja: "データ複雑度" },
  ui_complexity: { en: "User interface complexity", ja: "UI複雑度" },
  auth_complexity: { en: "Authentication complexity", ja: "認証の複雑度" },
  data_migration_needed: { en: "Data migration needed", ja: "データ移行の要否" },
  compliance_level: { en: "Compliance requirements", ja: "コンプライアンス要件" },
  technology_preferences: { en: "Technology preferences", ja: "技術的偏好" },
  development_approach: { en: "Development approach", ja: "開発アプローチ" },
  rules_and_standards: { en: "Rules and standards to follow", ja: "遵守ルール・標準" },
  team_and_resources: { en: "Team and resources", ja: "チーム・リソース" },
  development_location: { en: "Where development happens", ja: "開発拠点" },
  delivery_timing: { en: "Delivery timing", ja: "納期・スケジュール" },
  maintenance_support: { en: "Maintenance and support", ja: "保守・サポート" },
  risks_unknowns: { en: "Risks and unknowns", ja: "リスク・不明点" },
  budget: { en: "Budget", ja: "予算" },
  delivery_schedule: {
    en: "What is your desired delivery schedule?",
    ja: "希望の納期・スケジュールはいつですか？",
  },
  timeline_planning: {
    en: "How should we plan the timeline?",
    ja: "タイムラインの計画方法",
  },
  client_budget: { en: "What is your budget?", ja: "予算を教えてください。" },
};

/** Header keys that must appear even on older estimate schema snapshots. */
const ENSURE_HEADER_FIELD_KEYS = ["timeline_planning"] as const;

function buildEnsuredHeaderField(
  key: (typeof ENSURE_HEADER_FIELD_KEYS)[number],
  sortOrder: number,
): FormFieldSchema {
  return {
    key,
    type: "select",
    required: false,
    sort_order: sortOrder,
    section: "header",
    label: LEGACY_LABELS[key] ?? { en: key, ja: key },
    description: { en: "", ja: "" },
    placeholder: { en: "", ja: "" },
    options: SELECT_FIELD_OPTIONS[key] ?? [],
  };
}

export function ensureKnownHeaderFields(schema: FormFieldSchema[]): FormFieldSchema[] {
  const byKey = new Map(schema.map((field) => [field.key, field]));
  const missing = ENSURE_HEADER_FIELD_KEYS.filter((key) => !byKey.has(key));
  if (missing.length === 0) {
    return schema;
  }

  const result = [...schema];
  for (const key of missing) {
    const delivery = byKey.get("delivery_schedule");
    const clientBudget = byKey.get("client_budget");
    let sortOrder = 95;
    if (delivery && clientBudget && clientBudget.sort_order > delivery.sort_order) {
      sortOrder =
        delivery.sort_order + Math.max(1, Math.floor((clientBudget.sort_order - delivery.sort_order) / 2));
    } else if (delivery) {
      sortOrder = delivery.sort_order + 5;
    } else if (clientBudget) {
      sortOrder = Math.max(0, clientBudget.sort_order - 5);
    }
    const field = buildEnsuredHeaderField(key, sortOrder);
    result.push(field);
    byKey.set(key, field);
  }
  return result.sort((a, b) => a.sort_order - b.sort_order);
}

export function resolveFormSchema(
  snapshot: FormFieldSchema[] | null | undefined,
): FormFieldSchema[] {
  if (!snapshot || snapshot.length === 0) {
    return legacyFormFieldsToSchema();
  }
  return ensureKnownHeaderFields(
    patchKnownFieldTypes([...snapshot].sort((a, b) => a.sort_order - b.sort_order)),
  );
}

const OPTION_LABELS: Record<string, LocalizedText> = {
  low: { en: "Low / Simple", ja: "低 / シンプル" },
  medium: { en: "Medium", ja: "中" },
  high: { en: "High", ja: "高" },
  simple: { en: "Low / Simple", ja: "低 / シンプル" },
  moderate: { en: "Medium", ja: "中" },
  complex: { en: "High", ja: "高" },
  japan: { en: "Mainly in Japan", ja: "主に国内" },
  offshore: { en: "Mainly offshore", ja: "主にオフショア" },
  hybrid: { en: "Mix of Japan and offshore", ja: "国内とオフショアの混合" },
};

const COMPLEXITY_VALUE_ALIASES: Record<string, string> = {
  simple: "low",
  basic: "low",
  moderate: "medium",
  normal: "medium",
  complex: "high",
  advanced: "high",
};

const COMPLEXITY_CANONICAL_TO_LEGACY: Record<string, string> = {
  low: "simple",
  medium: "moderate",
  high: "complex",
};

function resolveComplexityValueForSchema(field: FormFieldSchema, raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) {
    return trimmed;
  }
  const optionValues = new Set((field.options ?? []).map((option) => option.value));
  if (optionValues.has(trimmed)) {
    return trimmed;
  }
  const canonical = COMPLEXITY_VALUE_ALIASES[trimmed.toLowerCase()] ?? trimmed.toLowerCase();
  if (optionValues.has(canonical)) {
    return canonical;
  }
  const legacy = COMPLEXITY_CANONICAL_TO_LEGACY[canonical];
  if (legacy && optionValues.has(legacy)) {
    return legacy;
  }
  return trimmed;
}

export type FormFieldValues = Record<string, string>;

export function resolveLocale(locale: string): "en" | "ja" {
  return locale === "ja" ? "ja" : "en";
}

export function getFieldLabel(field: FormFieldSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return field.label[resolved] || field.label.en || field.key;
}

export function getFieldPlaceholder(field: FormFieldSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return field.placeholder?.[resolved] || field.placeholder?.en || "";
}

export function getOptionLabel(option: SelectOptionSchema, locale: string): string {
  const resolved = resolveLocale(locale);
  return option.label[resolved] || option.label.en || option.value;
}

/** True when a select field has a stored value that does not match any current option. */
export function isOrphanSelectValue(field: FormFieldSchema, value: string): boolean {
  const trimmed = value.trim();
  if (field.type !== "select" || !trimmed) {
    return false;
  }
  return !(field.options ?? []).some((option) => option.value === trimmed);
}

export function legacyFormFieldsToSchema(): FormFieldSchema[] {
  return FORM_FIELDS.filter((field) => field.key !== "project_name").map((field, index) => {
    const labels = LEGACY_LABELS[field.key] ?? { en: field.key, ja: field.key };
    const schema: FormFieldSchema = {
      key: field.key,
      type: field.type,
      required: field.required,
      sort_order: index * 10,
      label: labels,
      description: { en: "", ja: "" },
      placeholder: { en: "", ja: "" },
    };
    if (field.type === "select" && "options" in field) {
      schema.options = field.options.map((value) => ({
        value,
        label: OPTION_LABELS[value] ?? { en: value, ja: value },
      }));
    }
    return schema;
  });
}

export function patchKnownFieldTypes(schema: FormFieldSchema[]): FormFieldSchema[] {
  return schema.map((field) => {
    const targetType = KNOWN_FIELD_TYPE_PATCHES[field.key];
    const placeholders = FIELD_PLACEHOLDERS[field.key];
    if (!targetType) {
      if (placeholders) {
        return { ...field, placeholder: placeholders };
      }
      return field;
    }
    const patched: FormFieldSchema = { ...field, type: targetType };
    if (targetType === "select") {
      patched.options = SELECT_FIELD_OPTIONS[field.key] ?? field.options ?? [];
    }
    if (placeholders) {
      patched.placeholder = placeholders;
    }
    return patched;
  });
}

export function splitSchemaBySection(schema: FormFieldSchema[]): {
  headerFields: FormFieldSchema[];
  specificationFields: FormFieldSchema[];
} {
  const sorted = resolveFormSchema(schema);
  return {
    headerFields: sorted.filter((field) => field.section === "header"),
    specificationFields: sorted.filter((field) => field.section !== "header"),
  };
}

export function specificationFieldKeys(schema: FormFieldSchema[]): Set<string> {
  return new Set(splitSchemaBySection(schema).specificationFields.map((field) => field.key));
}

export function isSchemaFieldRequired(
  field: FormFieldSchema,
  hasUploadedDocuments: boolean,
): boolean {
  if (field.key === "project_name") {
    return true;
  }
  if (hasUploadedDocuments) {
    return false;
  }
  return field.required;
}

export function validateFormValues(
  schema: FormFieldSchema[],
  values: FormFieldValues,
  hasUploadedDocuments: boolean,
  messages: FormValidationMessages,
): Partial<Record<string, string>> {
  const errors: Partial<Record<string, string>> = {};

  for (const field of schema) {
    const value = values[field.key]?.trim() ?? "";
    if (isSchemaFieldRequired(field, hasUploadedDocuments) && !value) {
      errors[field.key] = messages.required;
      continue;
    }
    if (!value) {
      continue;
    }
    if (field.type === "number") {
      if (!/^\d+$/.test(value)) {
        errors[field.key] = messages.invalidNumber;
      }
    } else if (field.type === "currency") {
      if (!/^\d+$/.test(value)) {
        errors[field.key] = messages.invalidCurrency;
      }
    }
  }

  if (!isUsableProjectName(values.project_name)) {
    errors.project_name = messages.required;
  }

  return errors;
}

export function emptyFormValuesForSchema(schema: FormFieldSchema[]): FormFieldValues {
  const values: FormFieldValues = { project_name: "" };
  for (const field of schema) {
    if (field.key === "data_complexity" || field.key === "ui_complexity") {
      values[field.key] = "low";
    } else if (field.key === "timeline_planning") {
      values[field.key] = "match_schedule";
    } else {
      values[field.key] = "";
    }
  }
  return values;
}

export function formValuesFromSchema(
  schema: FormFieldSchema[],
  formData: Record<string, unknown> | null | undefined,
  projectName: string,
  displayProjectName: (name: string) => string,
): FormFieldValues {
  const values = emptyFormValuesForSchema(schema);
  values.project_name = displayProjectName(projectName);

  if (formData) {
    for (const field of schema) {
      const raw = formData[field.key];
      let asString: string | null = null;
      if (typeof raw === "string") {
        asString = raw;
      } else if (typeof raw === "number" || typeof raw === "boolean") {
        asString = String(raw);
      }

      if (asString !== null) {
        if (field.key === "data_complexity" || field.key === "ui_complexity") {
          values[field.key] = resolveComplexityValueForSchema(field, asString);
        } else {
          values[field.key] = asString;
        }
      } else if (field.key === "timeline_planning") {
        // Existing estimates without the field keep fastest (blank → natural at calc).
        values[field.key] = "";
      }
    }
  }

  return values;
}

export function schemaFieldLabels(
  schema: FormFieldSchema[],
  locale: string,
): Record<string, string> {
  return Object.fromEntries(
    schema.map((field) => [field.key, getFieldLabel(field, locale)]),
  );
}

export function slugifyFieldKey(label: string): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 50);
  if (!slug || !/^[a-z]/.test(slug)) {
    return `field_${Date.now().toString(36)}`;
  }
  return slug;
}
