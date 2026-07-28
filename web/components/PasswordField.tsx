"use client";

import { useState, type ComponentProps } from "react";
import { useTranslations } from "next-intl";

type PasswordFieldProps = Omit<ComponentProps<"input">, "type">;

function EyeIcon() {
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
      aria-hidden="true"
    >
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon() {
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
      aria-hidden="true"
    >
      <path d="M3 3l18 18" />
      <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
      <path d="M9.9 5.1A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a18.3 18.3 0 0 1-2.2 3.1" />
      <path d="M6.1 6.1C3.7 7.8 2 12 2 12s3.5 7 10 7a10.4 10.4 0 0 0 4.1-.8" />
    </svg>
  );
}

export default function PasswordField({
  className = "",
  onFocus,
  readOnly,
  autoComplete = "off",
  ...props
}: PasswordFieldProps) {
  const t = useTranslations("common");
  const [visible, setVisible] = useState(false);
  // Browsers autofill password fields on load (blue tint + mask dots)
  // even when React value is "". Lock until focus so the field stays empty.
  const [autofillLocked, setAutofillLocked] = useState(true);
  const fullWidth = /\bw-full\b/.test(className);
  const label = visible ? t("hidePassword") : t("showPassword");

  return (
    <div className={`flex items-center gap-2${fullWidth ? " w-full" : ""}`}>
      <input
        {...props}
        type={visible ? "text" : "password"}
        autoComplete={autoComplete}
        readOnly={readOnly ?? autofillLocked}
        onFocus={(event) => {
          setAutofillLocked(false);
          onFocus?.(event);
        }}
        className={fullWidth ? `${className} min-w-0 flex-1` : className}
      />
      <button
        type="button"
        onClick={() => setVisible((current) => !current)}
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded border border-gray-300 bg-white text-gray-600 transition hover:bg-gray-50 hover:text-gray-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 dark:border-gray-600 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-gray-800 dark:hover:text-gray-100 dark:focus-visible:ring-offset-gray-900"
        aria-label={label}
        title={label}
        disabled={props.disabled}
      >
        {visible ? <EyeOffIcon /> : <EyeIcon />}
      </button>
    </div>
  );
}
