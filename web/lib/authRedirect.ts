/** Safe relative in-app path for post-login redirect (open-redirect guard). */
export function isSafeReturnPath(path: string | null | undefined): path is string {
  if (!path) {
    return false;
  }
  if (!path.startsWith("/") || path.startsWith("//")) {
    return false;
  }
  return !path.includes("\\");
}

export function loginUrl(locale: string, returnTo?: string): string {
  const base = `/${locale}/login`;
  if (!returnTo || !isSafeReturnPath(returnTo)) {
    return base;
  }
  return `${base}?next=${encodeURIComponent(returnTo)}`;
}

export function resolveReturnPath(
  locale: string,
  next: string | null | undefined,
  fallback = `/${locale}/estimates`,
): string {
  if (isSafeReturnPath(next)) {
    return next;
  }
  return fallback;
}
