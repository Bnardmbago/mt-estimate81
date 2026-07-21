/**
 * Post-extract timeline state: extraction clears calculation_result, so the
 * client hydrates /gantt into liveGantt. Server prop sync must not wipe that
 * when features still exist but calculation_result is null.
 */

export type TimelineGanttLike = {
  tasks: unknown[];
};

export function resolveLiveGanttFromServerProps<T extends TimelineGanttLike>(
  serverGantt: T | null | undefined,
  featureItemCount: number,
  currentLiveGantt: T | null,
): T | null {
  if (serverGantt && serverGantt.tasks.length > 0) {
    return serverGantt;
  }
  if (featureItemCount <= 0) {
    return null;
  }
  return currentLiveGantt;
}

/**
 * After re-extract, Next.js refresh can briefly return empty feature_items while
 * the client already hydrated. Keep the hydrated list until the server catches up.
 * (Saving an empty feature list is rejected by the API, so this is safe.)
 */
export function resolveFeatureItemsFromServerProps<T>(
  serverItems: T[] | null | undefined,
  currentItems: T[],
): T[] {
  const items = serverItems ?? [];
  if (items.length === 0 && currentItems.length > 0) {
    return currentItems;
  }
  return items;
}
