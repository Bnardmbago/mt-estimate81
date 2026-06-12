/** Server-side fetch via the Next.js /api proxy (same path the browser uses). */
export function getServerApiBaseUrl(): string {
  const webInternal = process.env.WEB_INTERNAL_URL || "http://127.0.0.1:3000";
  return `${webInternal}/api`;
}

export async function serverApiFetch(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<Response> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const headers = new Headers(init.headers);
  headers.set("Cookie", `access_token=${token}`);

  return fetch(`${getServerApiBaseUrl()}${normalizedPath}`, {
    ...init,
    headers,
    cache: "no-store",
  });
}

export type ApiFetchResult<T> =
  | { status: "ok"; data: T }
  | { status: "unauthorized" }
  | { status: "not_found" }
  | { status: "error"; httpStatus: number };

export async function serverApiJson<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<ApiFetchResult<T>> {
  try {
    const response = await serverApiFetch(path, token, init);

    if (response.status === 401) {
      return { status: "unauthorized" };
    }

    if (response.status === 404 || response.status === 403) {
      return { status: "not_found" };
    }

    if (!response.ok) {
      return { status: "error", httpStatus: response.status };
    }

    return { status: "ok", data: (await response.json()) as T };
  } catch (error) {
    console.error("Server API fetch failed:", path, error);
    return { status: "error", httpStatus: 502 };
  }
}
