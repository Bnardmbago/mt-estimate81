from __future__ import annotations

from typing import TYPE_CHECKING

from app.calculation.schemas import MonthlyRcItem, RateCardSettings, RoleRate, SetupCostItem

if TYPE_CHECKING:
    from app.fx.service import FxService


async def rate_card_settings_to_jpy(
    settings: RateCardSettings,
    fx_service: FxService,
) -> tuple[RateCardSettings, dict]:
    fx_snapshot = await fx_service.build_snapshot()
    source_currency = settings.currency

    if source_currency == "JPY":
        return settings, fx_snapshot

    roles = []
    for role in settings.roles:
        hourly_jpy = await fx_service.convert_amount(role.hourly_rate, source_currency, "JPY")
        daily_jpy = (
            await fx_service.convert_amount(role.daily_rate, source_currency, "JPY")
            if role.daily_rate is not None
            else hourly_jpy * 8
        )
        roles.append(
            RoleRate(
                name=role.name,
                hourly_rate=hourly_jpy,
                daily_rate=daily_jpy,
            )
        )

    monthly_rc_items = []
    for item in settings.monthly_rc_items:
        amount_jpy = await fx_service.convert_amount(item.amount, source_currency, "JPY")
        monthly_rc_items.append(MonthlyRcItem(name=item.name, amount=amount_jpy))

    setup_cost_items = []
    for item in settings.setup_cost_items:
        amount_jpy = await fx_service.convert_amount(item.amount, source_currency, "JPY")
        setup_cost_items.append(SetupCostItem(name=item.name, amount=amount_jpy))

    default_maintenance_jpy = await fx_service.convert_amount(
        settings.default_maintenance_monthly_jpy,
        source_currency,
        "JPY",
    )
    jpy_settings = settings.model_copy(
        update={
            "roles": roles,
            "monthly_rc_items": monthly_rc_items,
            "setup_cost_items": setup_cost_items,
            "default_maintenance_monthly_jpy": default_maintenance_jpy,
            "currency": "JPY",
        }
    )
    return jpy_settings, fx_snapshot
