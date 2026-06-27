import { roleDevelopersCount } from "@/lib/datetime";

type RoleBreakdownRow = {
  role: string;
  hours: number;
  personnel_count?: number;
  rate_jpy: number;
  cost_jpy: number;
};

export function filterActiveRoleBreakdown(
  roleBreakdown: RoleBreakdownRow[],
  estimatedDurationDays: number | undefined,
  totalEffortDays: number,
): RoleBreakdownRow[] {
  return roleBreakdown.filter((row) => {
    if (row.hours <= 0) {
      return false;
    }
    const headcount = roleDevelopersCount(
      row.hours,
      row.personnel_count,
      estimatedDurationDays,
      totalEffortDays,
    );
    return headcount > 0;
  });
}
