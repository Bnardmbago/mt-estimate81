export const QUESTIONNAIRE_INCOMPLETE_CODE = "QUESTIONNAIRE_INCOMPLETE";

export type QuestionnaireMissingKey = "scope_signal" | "data_complexity" | "ui_complexity";

const QUESTIONNAIRE_MISSING_KEYS = new Set<string>([
  "scope_signal",
  "data_complexity",
  "ui_complexity",
]);

function readFieldsFromRecord(record: Record<string, unknown>): string[] {
  const details = record.details;
  if (typeof details === "object" && details !== null && !Array.isArray(details)) {
    const fields = (details as Record<string, unknown>).fields;
    if (Array.isArray(fields)) {
      return fields.filter((field): field is string => typeof field === "string");
    }
  }

  const directFields = record.fields;
  if (Array.isArray(directFields)) {
    return directFields.filter((field): field is string => typeof field === "string");
  }

  return [];
}

export function extractQuestionnaireMissingFields(payload: unknown): QuestionnaireMissingKey[] | null {
  if (typeof payload !== "object" || payload === null) {
    return null;
  }

  const record = payload as Record<string, unknown>;
  const nested =
    typeof record.detail === "object" && record.detail !== null
      ? (record.detail as Record<string, unknown>)
      : null;

  const code =
    (typeof record.code === "string" && record.code) ||
    (nested && typeof nested.code === "string" ? nested.code : null);

  if (code !== QUESTIONNAIRE_INCOMPLETE_CODE) {
    return null;
  }

  const fields = readFieldsFromRecord(record);
  const nestedFields = nested ? readFieldsFromRecord(nested) : [];
  const merged = fields.length > 0 ? fields : nestedFields;

  return merged.filter((field): field is QuestionnaireMissingKey =>
    QUESTIONNAIRE_MISSING_KEYS.has(field),
  );
}

export function questionnaireMissingMessageKey(field: QuestionnaireMissingKey): string {
  return `questionnaireMissing.${field}`;
}
