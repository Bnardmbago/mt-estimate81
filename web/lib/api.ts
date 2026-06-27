const API_BASE = "/api";

export type ApiErrorPayload = {
  error?: string;
  code?: string;
  details?: Record<string, unknown>;
};

export function parseApiErrorPayload(
  payload: unknown,
  fallback: string,
): { message: string; code?: string } {
  if (typeof payload !== "object" || payload === null) {
    return { message: fallback };
  }

  const record = payload as Record<string, unknown>;
  const nested =
    typeof record.detail === "object" && record.detail !== null
      ? (record.detail as Record<string, unknown>)
      : null;

  const error =
    (typeof record.error === "string" && record.error) ||
    (nested && typeof nested.error === "string" ? nested.error : null);
  const code =
    (typeof record.code === "string" && record.code) ||
    (nested && typeof nested.code === "string" ? nested.code : undefined);

  if (error) {
    return { message: error, code };
  }

  if (typeof record.detail === "string") {
    return { message: record.detail };
  }

  if (Array.isArray(record.detail)) {
    const message = record.detail
      .map((item: { msg?: string; loc?: string[] }) =>
        item.loc ? `${item.loc.join(".")}: ${item.msg ?? "invalid"}` : item.msg,
      )
      .filter(Boolean)
      .join("; ");
    if (message) {
      return { message };
    }
  }

  return { message: fallback };
}

export function withLocaleHeaders(locale: string, options: RequestInit = {}): RequestInit {
  const headers = new Headers(options.headers);
  headers.set("X-Display-Locale", locale);
  headers.set("X-Content-Locale", locale);
  return { ...options, headers };
}

export async function apiFetch(
  path: string,
  options: RequestInit = {},
  locale?: string,
): Promise<Response> {
  const resolvedOptions = locale ? withLocaleHeaders(locale, options) : options;
  const url = path.startsWith("/") ? `${API_BASE}${path}` : `${API_BASE}/${path}`;
  const headers = new Headers(resolvedOptions.headers);
  const isFormData =
    typeof FormData !== "undefined" && resolvedOptions.body instanceof FormData;

  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(url, {
    ...resolvedOptions,
    credentials: "include",
    headers,
  });
}

export async function apiJson<T>(
  path: string,
  options: RequestInit = {},
  locale?: string,
): Promise<T> {
  const response = await apiFetch(path, options, locale);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    const { message } = parseApiErrorPayload(error, response.statusText);
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}
