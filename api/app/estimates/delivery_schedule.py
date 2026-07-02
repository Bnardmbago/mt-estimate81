from __future__ import annotations

from typing import Any, Literal

DeliveryScheduleStatus = Literal["within_band", "over_band", "unknown"]

DELIVERY_SCHEDULE_TARGET_WORKING_DAYS: dict[str, int] = {
    "asap": 45,
    "within_1_3_months": 65,
    "within_3_6_months": 130,
    "within_6_12_months": 260,
}


def delivery_schedule_target_working_days(slug: str | None) -> int | None:
    if not slug:
        return None
    normalized = str(slug).strip()
    if not normalized:
        return None
    return DELIVERY_SCHEDULE_TARGET_WORKING_DAYS.get(normalized)


def build_delivery_schedule_advisory(
    delivery_schedule: str | None,
    total_working_days: int,
) -> dict[str, Any]:
    target = delivery_schedule_target_working_days(delivery_schedule)
    if target is None:
        return {
            "delivery_schedule": delivery_schedule,
            "delivery_schedule_status": "unknown",
            "delivery_schedule_message_key": "deliverySchedule.unknown",
            "target_working_days": None,
            "actual_working_days": total_working_days,
        }

    status: DeliveryScheduleStatus = (
        "within_band" if total_working_days <= target else "over_band"
    )
    message_key = (
        "deliverySchedule.withinBand"
        if status == "within_band"
        else "deliverySchedule.overBand"
    )
    return {
        "delivery_schedule": delivery_schedule,
        "delivery_schedule_status": status,
        "delivery_schedule_message_key": message_key,
        "target_working_days": target,
        "actual_working_days": total_working_days,
    }
