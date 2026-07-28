export function clonePlainData<T>(value: T): T {
  if (typeof globalThis.structuredClone === "function") {
    return globalThis.structuredClone(value);
  }
  return cloneFallback(value);
}

function cloneFallback<T>(value: T): T {
  if (Array.isArray(value)) {
    return value.map((item) => cloneFallback(item)) as T;
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, entry]) => [key, cloneFallback(entry)]),
    ) as T;
  }
  return value;
}
