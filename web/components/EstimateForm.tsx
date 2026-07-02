"use client";

import { FormEvent, ReactNode, forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import AutoResizeTextarea from "@/components/AutoResizeTextarea";
import CollapsibleFormSection from "@/components/CollapsibleFormSection";
import { apiJson } from "@/lib/api";
import { moneySymbol } from "@/lib/displayI18n";
import type { EstimateDetail } from "@/lib/estimate";
import { displayProjectName, localizedProjectName, resolveProjectNameForSave } from "@/lib/formFields";
import {
  type FormFieldSchema,
  type FormFieldValues,
  formValuesFromSchema,
  getFieldLabel,
  getFieldPlaceholder,
  getOptionLabel,
  isOrphanSelectValue,
  isSchemaFieldRequired,
  resolveFormSchema,
  specificationFieldKeys,
  splitSchemaBySection,
  validateFormValues,
} from "@/lib/formSchema";

type EstimateFormProps = {
  estimate: EstimateDetail;
  hasUploadedDocuments?: boolean;
  isContactUser?: boolean;
  children?: ReactNode;
  documentsSection?: ReactNode;
};

export type EstimateFormHandle = {
  saveIfNeeded: () => Promise<boolean>;
  saveBeforeAiSuggest: () => Promise<boolean>;
  saveProjectName: () => Promise<boolean>;
  getValues: () => FormFieldValues;
  applyValues: (partial: Partial<FormFieldValues>) => void;
  startPostApplyGuidance: () => void;
};

const SECTION_ID_TECHNICAL_SPECIFICATION = "estimate-section-technical-specification";
const SECTION_ID_CLIENT_QUESTIONNAIRE = "estimate-section-client-questionnaire";

function sectionHasData(fields: FormFieldSchema[], values: FormFieldValues): boolean {
  return fields.some((field) => (values[field.key] ?? "").trim().length > 0);
}

function scrollToSection(sectionId: string): void {
  requestAnimationFrame(() => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  });
}

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

function sanitizeNumericInput(value: string): string {
  return value.replace(/[^\d]/g, "");
}

const statusBadgeClassName: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  extracting: "bg-yellow-100 text-yellow-800",
  review: "bg-blue-100 text-blue-800",
  calculated: "bg-indigo-100 text-indigo-800",
  exported: "bg-purple-100 text-purple-800",
  completed: "bg-green-100 text-green-800",
};

function valuesEqual(
  schema: FormFieldSchema[],
  a: FormFieldValues,
  b: FormFieldValues,
): boolean {
  if (a.project_name !== b.project_name) {
    return false;
  }
  return schema.every((field) => a[field.key] === b[field.key]);
}

const EstimateForm = forwardRef<EstimateFormHandle, EstimateFormProps>(function EstimateForm(
  { estimate, hasUploadedDocuments = false, isContactUser = false, children, documentsSection },
  ref,
) {
  const router = useRouter();
  const locale = useLocale();
  const tForm = useTranslations("form");
  const tEstimates = useTranslations("estimates");

  const schema = useMemo(
    () => resolveFormSchema(estimate.form_schema_snapshot),
    [estimate.form_schema_snapshot],
  );

  const { headerFields, specificationFields } = useMemo(
    () => splitSchemaBySection(schema),
    [schema],
  );

  const specKeys = useMemo(() => specificationFieldKeys(schema), [schema]);

  const initialValues = useMemo(
    () => formValuesFromSchema(schema, estimate.form_data, estimate.project_name, displayProjectName),
    [estimate.form_data, estimate.project_name, schema],
  );

  const [values, setValues] = useState<FormFieldValues>(initialValues);
  const [savedValues, setSavedValues] = useState<FormFieldValues>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<string, string>>>({});
  const [saving, setSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [specExpanded, setSpecExpanded] = useState(() =>
    sectionHasData(specificationFields, initialValues),
  );
  const [clientExpanded, setClientExpanded] = useState(() =>
    sectionHasData(headerFields, initialValues),
  );
  const [guidanceStep, setGuidanceStep] = useState<"client" | null>(null);

  const isDirty = !valuesEqual(schema, values, savedValues);

  useEffect(() => {
    setValues(initialValues);
    setSavedValues(initialValues);
    setErrors({});
    setSaveState("idle");
    setSaveError(null);
    setSpecExpanded(sectionHasData(specificationFields, initialValues));
    setClientExpanded(sectionHasData(headerFields, initialValues));
    setGuidanceStep(null);
  }, [initialValues, specificationFields, headerFields]);

  useEffect(() => {
    if (!isDirty && saveState === "saved") {
      return;
    }
    if (isDirty && saveState === "saved") {
      setSaveState("idle");
    }
  }, [isDirty, saveState]);

  const updateField = useCallback((key: string, value: string) => {
    setValues((current) => ({ ...current, [key]: value }));
    setErrors((current) => {
      if (!current[key]) {
        return current;
      }
      const next = { ...current };
      delete next[key];
      return next;
    });
  }, []);

  function validate(nextValues: FormFieldValues): Partial<Record<string, string>> {
    const fieldsToValidate = isContactUser
      ? schema.filter((field) => field.section === "header")
      : schema;
    const errors = validateFormValues(fieldsToValidate, nextValues, hasUploadedDocuments, {
      required: tForm("required"),
      invalidNumber: tForm("invalidNumber"),
      invalidCurrency: tForm("invalidCurrency"),
    });
    const effectiveProjectName = resolveProjectNameForSave(
      nextValues.project_name,
      estimate.project_name,
    );
    if (!effectiveProjectName) {
      errors.project_name = tForm("required");
    } else {
      delete errors.project_name;
    }
    return errors;
  }

  useEffect(() => {
    if (!hasUploadedDocuments) {
      return;
    }
    setErrors((current) => {
      const next = { ...current };
      let changed = false;
      for (const field of schema) {
        if (next[field.key]) {
          delete next[field.key];
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [hasUploadedDocuments, schema]);

  async function persistValues(nextValues: FormFieldValues): Promise<void> {
    const formData = Object.fromEntries(
      schema.map((field) => [field.key, nextValues[field.key]]),
    );

    await apiJson<EstimateDetail>(
      `/estimates/${estimate.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          project_name: resolveProjectNameForSave(
            nextValues.project_name,
            estimate.project_name,
          ),
          form_data: formData,
        }),
      },
      locale,
    );

    setSavedValues(nextValues);
    setSaveState("saved");
    router.refresh();
  }

  async function persistProjectName(projectName: string): Promise<void> {
    await apiJson<EstimateDetail>(
      `/estimates/${estimate.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          project_name: projectName.trim(),
        }),
      },
      locale,
    );

    const nextValues = { ...values, project_name: projectName.trim() };
    const nextSaved = { ...savedValues, project_name: projectName.trim() };
    setValues(nextValues);
    setSavedValues(nextSaved);
    setSaveState("saved");
    router.refresh();
  }

  const saveIfNeeded = useCallback(async (): Promise<boolean> => {
    if (valuesEqual(schema, values, savedValues)) {
      return true;
    }

    setSaveError(null);
    const nextErrors = validate(values);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return false;
    }

    setSaving(true);
    setSaveState("idle");

    try {
      await persistValues(values);
      return true;
    } catch (error) {
      setSaveState("error");
      setSaveError(error instanceof Error ? error.message : tEstimates("saveError"));
      return false;
    } finally {
      setSaving(false);
    }
  }, [hasUploadedDocuments, locale, savedValues, schema, tEstimates, values]);

  const saveProjectName = useCallback(async (): Promise<boolean> => {
    const projectName = resolveProjectNameForSave(values.project_name, estimate.project_name);
    if (!projectName) {
      setErrors((current) => ({ ...current, project_name: tForm("required") }));
      return false;
    }

    const savedProjectName = resolveProjectNameForSave(
      savedValues.project_name,
      estimate.project_name,
    );
    if (projectName === savedProjectName) {
      return true;
    }

    setSaveError(null);
    setSaving(true);
    setSaveState("idle");

    try {
      await persistProjectName(projectName);
      return true;
    } catch (error) {
      setSaveState("error");
      setSaveError(error instanceof Error ? error.message : tEstimates("saveError"));
      return false;
    } finally {
      setSaving(false);
    }
  }, [estimate.project_name, locale, savedValues.project_name, tEstimates, tForm, values.project_name]);

  const saveBeforeAiSuggest = useCallback(async (): Promise<boolean> => {
    const projectName = resolveProjectNameForSave(values.project_name, estimate.project_name);
    if (!projectName) {
      setErrors((current) => ({ ...current, project_name: tForm("required") }));
      return false;
    }

    if (valuesEqual(schema, values, savedValues)) {
      return true;
    }

    setSaveError(null);
    setSaving(true);
    setSaveState("idle");

    const formData = Object.fromEntries(
      schema.map((field) => [field.key, values[field.key] ?? ""]),
    );

    try {
      await apiJson<EstimateDetail>(
        `/estimates/${estimate.id}`,
        {
          method: "PATCH",
          body: JSON.stringify({
            project_name: projectName,
            form_data: formData,
          }),
        },
        locale,
      );

      const nextValues = {
        ...values,
        project_name: displayProjectName(projectName),
      };
      const nextSaved = {
        ...values,
        project_name: displayProjectName(projectName),
      };
      setValues(nextValues);
      setSavedValues(nextSaved);
      setSaveState("saved");
      router.refresh();
      return true;
    } catch (error) {
      setSaveState("error");
      setSaveError(error instanceof Error ? error.message : tEstimates("saveError"));
      return false;
    } finally {
      setSaving(false);
    }
  }, [estimate.id, estimate.project_name, locale, router, savedValues, schema, tEstimates, tForm, values]);

  const getValues = useCallback(() => values, [values]);

  const applyValues = useCallback(
    (partial: Partial<FormFieldValues>) => {
      setValues((current) => {
        const next = { ...current };
        for (const [key, value] of Object.entries(partial)) {
          if (typeof value !== "string" || !specKeys.has(key)) {
            continue;
          }
          next[key] = value;
        }
        return next;
      });
      setSaveState("idle");
    },
    [specKeys],
  );

  const completeClientGuidanceStep = useCallback(() => {
    setGuidanceStep(null);
    if (isContactUser) {
      return;
    }
    setSpecExpanded(true);
    scrollToSection(SECTION_ID_TECHNICAL_SPECIFICATION);
  }, [isContactUser]);

  const startPostApplyGuidance = useCallback(() => {
    setGuidanceStep("client");
    setClientExpanded(true);
    setSpecExpanded(false);
    scrollToSection(SECTION_ID_CLIENT_QUESTIONNAIRE);
  }, []);

  async function handleGuidanceSaveAndContinue() {
    const saved = await saveIfNeeded();
    if (saved) {
      completeClientGuidanceStep();
    }
  }

  function handleGuidanceSkip() {
    completeClientGuidanceStep();
  }

  useImperativeHandle(
    ref,
    () => ({
      saveIfNeeded,
      saveBeforeAiSuggest,
      saveProjectName,
      getValues,
      applyValues,
      startPostApplyGuidance,
    }),
    [applyValues, getValues, saveBeforeAiSuggest, saveIfNeeded, saveProjectName, startPostApplyGuidance],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaveError(null);

    const nextErrors = validate(values);
    setErrors(nextErrors);

    if (Object.keys(nextErrors).length > 0) {
      return;
    }

    setSaving(true);
    setSaveState("idle");

    try {
      await persistValues(values);
    } catch (error) {
      setSaveState("error");
      setSaveError(error instanceof Error ? error.message : tEstimates("saveError"));
    } finally {
      setSaving(false);
    }
  }

  function renderField(field: FormFieldSchema) {
    const fieldId = `field-${field.key}`;
    const label = getFieldLabel(field, locale);
    const hasError = Boolean(errors[field.key]);
    const required = isSchemaFieldRequired(field, hasUploadedDocuments);

    return (
      <div key={field.key}>
        <label htmlFor={fieldId} className="mb-1 block text-sm font-medium">
          {label}
          {required && <span className="ml-1 text-red-500">*</span>}
        </label>

        {field.type === "textarea" && (
          <AutoResizeTextarea
            id={fieldId}
            value={values[field.key] ?? ""}
            onChange={(event) => updateField(field.key, event.target.value)}
            placeholder={getFieldPlaceholder(field, locale)}
            className={`${inputClassName} resize-none overflow-hidden ${
              hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
            }`}
          />
        )}

        {field.type === "text" && (
          <input
            id={fieldId}
            type="text"
            value={values[field.key] ?? ""}
            onChange={(event) => updateField(field.key, event.target.value)}
            placeholder={getFieldPlaceholder(field, locale)}
            className={`${inputClassName} ${
              hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
            }`}
          />
        )}

        {field.type === "number" && (
          <input
            id={fieldId}
            type="number"
            min={0}
            step={1}
            inputMode="numeric"
            value={values[field.key] ?? ""}
            onChange={(event) =>
              updateField(field.key, sanitizeNumericInput(event.target.value))
            }
            placeholder={getFieldPlaceholder(field, locale)}
            className={`${inputClassName} ${
              hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
            }`}
          />
        )}

        {field.type === "currency" && (
          <div className="flex">
            <span
              className={`inline-flex items-center rounded-l border border-r-0 border-gray-300 bg-gray-50 px-3 text-sm text-gray-600 ${
                hasError ? "border-red-500" : ""
              }`}
            >
              {moneySymbol("JPY")}
            </span>
            <input
              id={fieldId}
              type="number"
              min={0}
              step={1}
              inputMode="numeric"
              value={values[field.key] ?? ""}
              onChange={(event) =>
                updateField(field.key, sanitizeNumericInput(event.target.value))
              }
              placeholder={getFieldPlaceholder(field, locale)}
              className={`${inputClassName} rounded-l-none ${
                hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
              }`}
            />
          </div>
        )}

        {field.type === "select" && (
          <>
            <select
              id={fieldId}
              value={
                isOrphanSelectValue(field, values[field.key] ?? "")
                  ? ""
                  : (values[field.key] ?? "")
              }
              onChange={(event) => updateField(field.key, event.target.value)}
              className={`${inputClassName} ${
                hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
              }`}
            >
              <option value="">{tForm("selectPlaceholder")}</option>
              {(field.options ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {getOptionLabel(option, locale)}
                </option>
              ))}
            </select>
            {isOrphanSelectValue(field, values[field.key] ?? "") && (
              <p className="mt-1 text-sm text-amber-700">
                {tForm("legacySelectValue", { value: values[field.key] ?? "" })}
              </p>
            )}
          </>
        )}

        {hasError && (
          <p className="mt-1 text-sm text-red-600" role="alert">
            {errors[field.key]}
          </p>
        )}
      </div>
    );
  }

  const badgeClass =
    statusBadgeClassName[estimate.status] ?? "bg-gray-100 text-gray-700";

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 border-b border-gray-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            href={`/${locale}/estimates`}
            className="mb-2 inline-block text-sm text-gray-500 hover:text-blue-600"
          >
            ← {tEstimates("back")}
          </Link>
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold">
              {values.project_name ||
                localizedProjectName(estimate.project_name, locale)}
            </h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ${badgeClass}`}
            >
              {tEstimates(`status.${estimate.status}`)}
            </span>
          </div>
          <p className="mt-1 text-sm text-gray-500">
            {tEstimates("client")}: {estimate.client_name}
          </p>
          {estimate.form_template_name && !isContactUser && (
            <p className="mt-1 text-sm text-gray-500">
              {tForm("templateLabel")}: {estimate.form_template_name}
            </p>
          )}
        </div>

        <div className="flex flex-col items-start gap-2 sm:items-end">
          <div className="flex items-center gap-3">
            {isDirty && (
              <span className="text-sm text-amber-600">{tEstimates("unsaved")}</span>
            )}
            {!isDirty && saveState === "saved" && (
              <span className="text-sm text-green-600">{tEstimates("saved")}</span>
            )}
            <button
              type="submit"
              form="estimate-form"
              disabled={saving || !isDirty}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {saving ? tEstimates("saving") : tEstimates("save")}
            </button>
          </div>
          {saveState === "error" && saveError && (
            <p className="text-sm text-red-600" role="alert">
              {saveError}
            </p>
          )}
        </div>
      </div>

      <form id="estimate-form" onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label htmlFor="field-project_name" className="mb-1 block text-sm font-medium">
            {tForm("project_name")}
            <span className="ml-1 text-red-500">*</span>
          </label>
          <input
            id="field-project_name"
            type="text"
            required
            value={values.project_name}
            onChange={(event) => updateField("project_name", event.target.value)}
            placeholder={tForm("project_namePlaceholder")}
            className={`${inputClassName} ${
              errors.project_name ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
            }`}
          />
          {errors.project_name && (
            <p className="mt-1 text-sm text-red-600" role="alert">
              {errors.project_name}
            </p>
          )}
        </div>

        {children}

        {specificationFields.length > 0 && !isContactUser ? (
          <CollapsibleFormSection
            id={SECTION_ID_TECHNICAL_SPECIFICATION}
            title={tForm("specificationDetails")}
            description={tForm("specificationDetailsDescription")}
            expanded={specExpanded}
            onExpandedChange={setSpecExpanded}
            sectionClassName="border-sky-200 bg-sky-50/40"
            expandLabel={tForm("expandSection")}
            collapseLabel={tForm("collapseSection")}
          >
            {hasUploadedDocuments && (
              <p className="text-sm text-gray-600">{tForm("optionalWithDocuments")}</p>
            )}
            {specificationFields.map((field) => renderField(field))}
          </CollapsibleFormSection>
        ) : null}

        {documentsSection}

        {headerFields.length > 0 ? (
          <CollapsibleFormSection
            id={SECTION_ID_CLIENT_QUESTIONNAIRE}
            title={tForm("headerQuestionnaire")}
            description={tForm("headerQuestionnaireDescription")}
            expanded={clientExpanded}
            onExpandedChange={setClientExpanded}
            sectionClassName="border-amber-200 bg-amber-50/30"
            expandLabel={tForm("expandSection")}
            collapseLabel={tForm("collapseSection")}
          >
            {guidanceStep === "client" ? (
              <div className="rounded-lg border border-amber-300 bg-amber-100/60 p-4">
                <p className="text-sm text-amber-950">{tForm("clientQuestionnaireGuidance")}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => void handleGuidanceSaveAndContinue()}
                    disabled={saving}
                    className="rounded bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800 disabled:opacity-50"
                  >
                    {saving ? tEstimates("saving") : tForm("saveAndContinue")}
                  </button>
                  <button
                    type="button"
                    onClick={handleGuidanceSkip}
                    disabled={saving}
                    className="rounded border border-amber-400 bg-white px-4 py-2 text-sm font-medium text-amber-900 hover:bg-amber-50 disabled:opacity-50"
                  >
                    {tForm("skipForNow")}
                  </button>
                </div>
              </div>
            ) : null}
            {headerFields.map((field) => renderField(field))}
          </CollapsibleFormSection>
        ) : null}
      </form>
    </div>
  );
});

export default EstimateForm;
