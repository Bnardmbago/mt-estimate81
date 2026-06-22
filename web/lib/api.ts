const API_BASE = "/api";

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
    const payload =
      typeof error.error === "string"
        ? error
        : typeof error.detail === "object"
          ? error.detail
          : error;
    throw new Error(
      typeof payload.error === "string"
        ? payload.error
        : typeof error.detail === "string"
          ? error.detail
          : Array.isArray(error.detail)
            ? error.detail
                .map((item: { msg?: string; loc?: string[] }) =>
                  item.loc ? `${item.loc.join(".")}: ${item.msg ?? "invalid"}` : item.msg,
                )
                .join("; ")
            : response.statusText,
    );
  }

  return response.json() as Promise<T>;
}
