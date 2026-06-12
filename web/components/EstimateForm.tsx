"use client";

import { FormEvent, forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { apiJson } from "@/lib/api";
import type { EstimateDetail } from "@/lib/estimate";
import {
  FORM_FIELDS,
  isFieldRequired,
  type FormFieldKey,
  type FormFieldValues,
  formValuesFromData,
} from "@/lib/formFields";

type EstimateFormProps = {
  estimate: EstimateDetail;
  hasUploadedDocuments?: boolean;
};

export type EstimateFormHandle = {
  saveIfNeeded: () => Promise<boolean>;
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

function valuesEqual(a: FormFieldValues, b: FormFieldValues): boolean {
  return FORM_FIELDS.every((field) => a[field.key] === b[field.key]);
}

const EstimateForm = forwardRef<EstimateFormHandle, EstimateFormProps>(function EstimateForm(
  { estimate, hasUploadedDocuments = false },
  ref,
) {
  const router = useRouter();
  const locale = useLocale();
  const tForm = useTranslations("form");
  const tEstimates = useTranslations("estimates");

  const initialValues = useMemo(
    () => formValuesFromData(estimate.form_data, estimate.project_name),
    [estimate.form_data, estimate.project_name],
  );

  const [values, setValues] = useState<FormFieldValues>(initialValues);
  const [savedValues, setSavedValues] = useState<FormFieldValues>(initialValues);
  const [errors, setErrors] = useState<Partial<Record<FormFieldKey, string>>>({});
  const [saving, setSaving] = useState(false);
  const [saveState, setSaveState] = useState<"idle" | "saved" | "error">("idle");
  const [saveError, setSaveError] = useState<string | null>(null);

  const isDirty = !valuesEqual(values, savedValues);

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

  const updateField = useCallback((key: FormFieldKey, value: string) => {
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

  function validate(nextValues: FormFieldValues): Partial<Record<FormFieldKey, string>> {
    const nextErrors: Partial<Record<FormFieldKey, string>> = {};

    for (const field of FORM_FIELDS) {
      if (!isFieldRequired(field, hasUploadedDocuments)) {
        continue;
      }
      if (!nextValues[field.key].trim()) {
        nextErrors[field.key] = tForm("required");
      }
    }

    return nextErrors;
  }

  useEffect(() => {
    if (!hasUploadedDocuments) {
      return;
    }
    setErrors((current) => {
      const next = { ...current };
      let changed = false;
      for (const field of FORM_FIELDS) {
        if (field.key !== "project_name" && next[field.key]) {
          delete next[field.key];
          changed = true;
        }
      }
      return changed ? next : current;
    });
  }, [hasUploadedDocuments]);

  async function persistValues(nextValues: FormFieldValues): Promise<void> {
    const formData = Object.fromEntries(
      FORM_FIELDS.filter((field) => field.key !== "project_name").map((field) => [
        field.key,
        nextValues[field.key],
      ]),
    );

    await apiJson<EstimateDetail>(
      `/estimates/${estimate.id}`,
      {
        method: "PATCH",
        body: JSON.stringify({
          project_name: nextValues.project_name.trim(),
          form_data: formData,
        }),
      },
      locale,
    );

    setSavedValues(nextValues);
    setSaveState("saved");
    router.refresh();
  }

  const saveIfNeeded = useCallback(async (): Promise<boolean> => {
    if (valuesEqual(values, savedValues)) {
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
  }, [hasUploadedDocuments, locale, savedValues, tEstimates, values]);

  useImperativeHandle(ref, () => ({ saveIfNeeded }), [saveIfNeeded]);

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
              {values.project_name || estimate.project_name}
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

      {hasUploadedDocuments && (
        <p className="mb-4 text-sm text-gray-600">{tForm("optionalWithDocuments")}</p>
      )}

      <form id="estimate-form" onSubmit={handleSubmit} className="space-y-5">
        {FORM_FIELDS.map((field) => {
          const fieldId = `field-${field.key}`;
          const label = tForm(field.key);
          const hasError = Boolean(errors[field.key]);
          const required = isFieldRequired(field, hasUploadedDocuments);

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
                  value={values[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                  className={`${inputClassName} resize-y min-h-[6rem] ${
                    hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
                  }`}
                />
              )}

              {field.type === "text" && (
                <input
                  id={fieldId}
                  type="text"
                  value={values[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                  className={`${inputClassName} ${
                    hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
                  }`}
                />
              )}

              {field.type === "select" && (
                <select
                  id={fieldId}
                  value={values[field.key]}
                  onChange={(event) => updateField(field.key, event.target.value)}
                  className={`${inputClassName} ${
                    hasError ? "border-red-500 focus:border-red-500 focus:ring-red-500" : ""
                  }`}
                >
                  <option value="">{tForm("selectPlaceholder")}</option>
                  {field.options.map((option) => (
                    <option key={option} value={option}>
                      {tForm(`options.${option}` as "options.simple")}
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
        })}
      </form>
    </div>
  );
});

export default EstimateForm;
