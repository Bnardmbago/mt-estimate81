type ContactErrorTranslator = (key: string) => string;

const CODE_TO_I18N_KEY: Record<string, string> = {
  EMAIL_NOT_CONFIGURED: "errorEmailNotConfigured",
  EMAIL_SEND_FAILED: "errorEmailSendFailed",
  CAPTCHA_FAILED: "errorCaptchaFailed",
  CAPTCHA_NOT_CONFIGURED: "errorCaptchaNotConfigured",
  RATE_LIMIT_EMAIL: "errorRateLimit",
  RATE_LIMIT_IP: "errorRateLimit",
  USE_FULL_LOGIN: "errorFullAccount",
  NAME_OR_COMPANY_REQUIRED: "errorNameOrCompany",
  API_UNREACHABLE: "errorNetwork",
  API_BAD_RESPONSE: "errorNetwork",
};

export function contactErrorMessage(
  t: ContactErrorTranslator,
  payload: unknown,
  fallbackKey = "error",
): string {
  const record =
    typeof payload === "object" && payload !== null
      ? (payload as { code?: string; error?: string })
      : {};
  const code = record.code;
  if (code && CODE_TO_I18N_KEY[code]) {
    return t(CODE_TO_I18N_KEY[code]);
  }
  if (typeof record.error === "string" && record.error.trim()) {
    return record.error;
  }
  return t(fallbackKey);
}
