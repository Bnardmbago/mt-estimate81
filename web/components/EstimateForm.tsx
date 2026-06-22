"use client";

import { FormEvent, ReactNode, forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail } from "@/lib/estimate";
import { displayProjectName, localizedProjectName, resolveProjectNameForSave } from "@/lib/formFields";
import {
  type FormFieldSchema,
  type FormFieldValues,
  formValuesFromSchema,
  getFieldLabel,
  getFieldPlaceholder,
  getOptionLabel,
  isSchemaFieldRequired,
  resolveFormSchema,
  specificationFieldKeys,
  splitSchemaBySection,
  validateFormValues,
} from "@/lib/formSchema";

type EstimateFormProps = {
  estimate: EstimateDetail;
  hasUploadedDocuments?: boolean;
  children?: ReactNode;
};

export type EstimateFormHandle = {
  saveIfNeeded: () => Promise<boolean>;
  saveBeforeAiSuggest: () => Promise<boolean>;
  saveProjectName: () => Promise<boolean>;
  getValues: () => FormFieldValues;
  applyValues: (partial: Partial<FormFieldValues>) => void;
};

const inputClassName =
  "w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500";

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
  { estimate, hasUploadedDocuments = false, children },
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

  const isDirty = !valuesEqual(schema, values, savedValues);

  useEffect(() => {
    setValues(initialValues);
    setSavedValues(initialValues);
    setErrors({});
    setSaveState("idle");
    setSaveError(null);
  }, [initialValues]);

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
    const errors = validateFormValues(schema, nextValues, hasUploadedDocuments, tForm("required"));
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

  useImperativeHandle(
    ref,
    () => ({
      saveIfNeeded,
      saveBeforeAiSuggest,
      saveProjectName,
      getValues,
      applyValues,
    }),
    [applyValues, getValues, saveBeforeAiSuggest, saveIfNeeded, saveProjectName],
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
          <textarea
            id={fieldId}
            rows={4}
            value={values[field.key] ?? ""}
            onChange={(event) => updateField(field.key, event.target.value)}
            placeholder={getFieldPlaceholder(field, locale)}
            className={`${inputClassName} resize-y min-h-[6rem] ${
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

        {field.type === "select" && (
          <select
            id={fieldId}
            value={values[field.key] ?? ""}
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
          {estimate.form_template_name && (
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

        {headerFields.length > 0 ? (
          <section className="space-y-5">
            <h2 className="text-base font-semibold text-gray-900">{tForm("headerQuestionnaire")}</h2>
            {headerFields.map((field) => renderField(field))}
          </section>
        ) : null}

        {children}

        {specificationFields.length > 0 ? (
          <section className="space-y-5">
            <h2 className="text-base font-semibold text-gray-900">{tForm("specificationDetails")}</h2>
            {hasUploadedDocuments && (
              <p className="text-sm text-gray-600">{tForm("optionalWithDocuments")}</p>
            )}
            {specificationFields.map((field) => renderField(field))}
          </section>
        ) : null}
      </form>
    </div>
  );
});

export default EstimateForm;
