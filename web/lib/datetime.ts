const HOURS_PER_EFFORT_DAY = 8;

/** Naive UTC timestamps from the API are stored without a Z suffix. */
export function parseUtcTimestamp(value: string): Date {
  const trimmed = value.trim();
  if (!trimmed) {
    return new Date(Number.NaN);
  }
  if (trimmed.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return new Date(trimmed);
  }
  return new Date(`${trimmed}Z`);
}

export function formatLocalTimestamp(value: string, locale: string): string {
  const date = parseUtcTimestamp(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString(locale === "ja" ? "ja-JP" : "en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });
}

export function roleDevelopersCount(
  hours: number,
  personnelCount: number | undefined,
  estimatedDurationDays: number | undefined,
  totalEffortDays: number,
): number {
  if (personnelCount != null) {
    return personnelCount;
  }
  if (hours <= 0) {
    return 0;
  }
  const duration =
    estimatedDurationDays != null && estimatedDurationDays > 0
      ? estimatedDurationDays
      : totalEffortDays;
  const capacity = Math.max(duration * HOURS_PER_EFFORT_DAY, HOURS_PER_EFFORT_DAY);
  return Math.max(1, Math.ceil(hours / capacity));
}
