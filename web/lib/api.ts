const API_BASE = "/api";

export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const url = path.startsWith("/") ? `${API_BASE}${path}` : `${API_BASE}/${path}`;
  const headers = new Headers(options.headers);
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;

  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(url, {
    ...options,
    credentials: "include",
    headers,
  });
}

export async function apiJson<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await apiFetch(path, options);

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
          : response.statusText,
    );
  }

  return response.json() as Promise<T>;
}
