import uuid
from datetime import date
from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.admin.discount_config import get_estimate_discount_rate, get_estimate_markup_rate
from app.audit.service import log_change
from app.calculation.development_approach import DevelopmentApproach
from app.calculation.calendar import default_project_start_date
from app.calculation.currency import rate_card_settings_to_jpy
from app.calculation.engine import CalculationError, calculate_estimate
from app.calculation.markup import compute_internal_pricing
from app.calculation.rc_detailed import build_detailed_rc_breakdown, get_markup_rate_from_calculation
from app.calculation.gantt import GanttFeatureItem, build_gantt_timeline, build_gantt_timeline_two_pass
from app.calculation.line_items import normalize_calculation_result, sanitize_calculation_result_for_user
from app.calculation.schemas import FeatureItemInput as CalcFeatureItemInput
from app.calculation.schemas import GanttFeatureItemInput, RateCardSettings
from app.estimates.access import can_access_estimate, require_estimate_access
from app.estimates.form_fields import normalize_form_data, prune_form_data_to_schema, snapshot_fields
from app.estimates.budget_comparison import build_budget_comparison
from app.estimates.delivery_schedule import build_delivery_schedule_advisory
from app.estimates.nrc_rc_assumptions import (
    NrcRcAssumptions,
    apply_nrc_rc_assumptions_to_settings,
    resolve_nrc_rc_assumptions,
)
from app.estimates.questionnaire_validation import missing_questionnaire_fields_for_calculation
from app.form_templates.service import get_template_or_404, resolve_template
from app.fx import get_fx_service
from app.estimates.rate_card_stale import (
    get_latest_extraction_tune_status,
    get_rate_card_auto_tune_enabled,
    get_rate_card_tune_recommended,
    is_rate_card_stale_for_estimate,
    mark_rate_card_auto_tune_enabled,
)
from app.i18n.localized_content import (
    normalize_locale,
    resolve_feature_item_fields,
    resolve_localized_dict,
    store_feature_item_localization,
    store_localized_dict,
)
from app.models.audit import AuditLog
from app.models.form_template import FormTemplate
from app.models.estimate import Estimate, EstimateStatus, FeatureItem
from app.models.rate_card import RateCard, RateCardVersion
from app.models.user import User
from app.rate_cards.normalize import normalize_settings_dict
from app.rate_cards.system import attach_system_rate_card
from app.rate_cards.service import (
    create_rate_card_with_settings,
    get_active_rate_card,
    get_latest_version_for_card,
    get_rate_card_for_user,
)
from app.users.access import is_contact_user
from app.storage.factory import get_storage_backend
from app.schemas.estimate import (
    CreateEstimateRateCardRequest,
    EstimateCreate,
    EstimateDetail,
    EstimateUpdate,
    ExtractedDataUpdate,
    FeatureItemResponse,
    FeatureItemsUpdate,
    NrcRcAssumptionsUpdate,
)


def _enrich_calculation_for_display(
    calculation: dict[str, Any] | None,
    locale: str,
) -> dict[str, Any] | None:
    if not calculation:
        return calculation
    if calculation.get("rc_detailed_breakdown"):
        return calculation
    markup_rate = get_markup_rate_from_calculation(calculation)
    cost_breakdown_mode = calculation.get("cost_breakdown_mode", "standard")
    return {
        **calculation,
        "rc_detailed_breakdown": build_detailed_rc_breakdown(
            calculation,
            locale=locale,
            markup_rate=markup_rate,
            cost_breakdown_mode=cost_breakdown_mode,
        ),
    }


async def create_estimate(
    db: AsyncSession,
    user: User,
    data: EstimateCreate,
) -> Estimate:
    if is_contact_user(user):
        existing_count = await db.scalar(
            select(func.count()).select_from(Estimate).where(Estimate.created_by == user.id)
        )
        if existing_count and existing_count >= 1:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Contact accounts are limited to one estimate",
                    "code": "CONTACT_ESTIMATE_LIMIT",
                },
            )

    client_name = (
        data.client_name.strip()
        if data.client_name and data.client_name.strip()
        else user.default_client_name()
    )
    template = await resolve_template(db, data.form_template_id)
    schema_snapshot = snapshot_fields(template.fields)

    estimate = Estimate(
        project_name=data.project_name,
        client_name=client_name,
        locale=data.locale,
        form_data=data.form_data,
        form_template_id=template.id,
        form_schema_snapshot=schema_snapshot,
        status=EstimateStatus.DRAFT.value,
        created_by=user.id,
    )
    db.add(estimate)
    await db.flush()

    if is_contact_user(user):
        await attach_system_rate_card(db, estimate)

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="created",
        changes={
            "project_name": data.project_name,
            "client_name": client_name,
            "locale": data.locale,
            "status": EstimateStatus.DRAFT.value,
        },
    )
    await db.commit()
    return await get_estimate(db, estimate.id)


async def list_estimates(db: AsyncSession, user: User) -> list[Estimate]:
    query = select(Estimate).order_by(Estimate.updated_at.desc())
    if not user.is_admin:
        query = query.where(Estimate.created_by == user.id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_estimate(db: AsyncSession, estimate_id: uuid.UUID) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.documents),
            selectinload(Estimate.actuals),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    return estimate


async def get_estimate_for_user(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> Estimate:
    estimate = await get_estimate(db, estimate_id)
    require_estimate_access(estimate, user)
    return estimate


async def estimate_to_detail(
    db: AsyncSession,
    estimate: Estimate,
    display_locale: str | None = None,
    user: User | None = None,
) -> EstimateDetail:
    rate_card_name = None
    if estimate.rate_card_id:
        card = await db.get(RateCard, estimate.rate_card_id)
        if card:
            rate_card_name = card.name

    resolved_locale = normalize_locale(display_locale, estimate.locale)
    fallback_locale = normalize_locale(estimate.locale, resolved_locale)
    form_data = resolve_localized_dict(estimate.form_data, resolved_locale, fallback_locale)
    extracted_data = None
    if estimate.extracted_data is not None:
        extracted_data = resolve_localized_dict(
            estimate.extracted_data,
            resolved_locale,
            fallback_locale,
        )

    feature_items = []
    for item in sorted(estimate.feature_items, key=lambda row: row.sort_order):
        fields = resolve_feature_item_fields(
            name=item.name,
            description=item.description,
            phase=item.phase,
            role=item.role,
            localizations=item.localizations,
            display_locale=resolved_locale,
            fallback_locale=fallback_locale,
        )
        feature_items.append(
            FeatureItemResponse(
                id=item.id,
                sort_order=item.sort_order,
                name=fields["name"],
                description=fields["description"],
                hours=float(item.hours),
                phase=fields["phase"],
                role=fields["role"],
                is_ai_generated=item.is_ai_generated,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
        )

    detail = EstimateDetail.model_validate(estimate, from_attributes=True)
    rate_card_stale = await is_rate_card_stale_for_estimate(db, estimate)
    tune_status = await get_latest_extraction_tune_status(db, estimate.id)
    complexity_profile = None
    if isinstance(extracted_data, dict):
        profile = extracted_data.get("complexity_profile")
        if isinstance(profile, dict):
            complexity_profile = profile
    template_name = None
    if estimate.form_template_id:
        template = await db.get(FormTemplate, estimate.form_template_id)
        if template:
            template_name = template.name
    schema_snapshot = snapshot_fields(estimate.form_schema_snapshot)
    return detail.model_copy(
        update={
            "rate_card_name": rate_card_name,
            "form_data": form_data,
            "extracted_data": extracted_data,
            "feature_items": feature_items,
            "rate_card_stale": rate_card_stale,
            "complexity_profile": complexity_profile,
            "rate_card_auto_tuned": tune_status["rate_card_auto_tuned"],
            "rate_card_tune_recommended": tune_status["rate_card_tune_recommended"]
            or get_rate_card_tune_recommended(estimate),
            "rate_card_auto_tune_enabled": get_rate_card_auto_tune_enabled(estimate),
            "form_template_name": template_name,
            "form_schema_snapshot": schema_snapshot,
            "calculation_result": sanitize_calculation_result_for_user(
                _enrich_calculation_for_display(
                    normalize_calculation_result(estimate.calculation_result),
                    resolved_locale,
                ),
                include_internal_pricing=bool(user and user.is_admin),
            ),
        }
    )


async def update_estimate(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: EstimateUpdate,
    content_locale: str | None = None,
) -> Estimate:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.feature_items),
            selectinload(Estimate.documents),
            selectinload(Estimate.actuals),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    require_estimate_access(estimate, user)

    changes: dict[str, Any] = {}
    update_data = data.model_dump(exclude_unset=True)
    form_data_payload = update_data.pop("form_data", None)
    form_template_id = update_data.pop("form_template_id", None)

    if form_template_id is not None:
        if estimate.status != EstimateStatus.DRAFT.value:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Form template can only be changed on draft estimates",
                    "code": "INVALID_STATUS",
                },
            )
        template = await get_template_or_404(db, form_template_id)
        new_snapshot = snapshot_fields(template.fields)
        if estimate.form_template_id != template.id:
            changes["form_template_id"] = {
                "old": str(estimate.form_template_id) if estimate.form_template_id else None,
                "new": str(template.id),
            }
            estimate.form_template_id = template.id
            estimate.form_schema_snapshot = new_snapshot
            estimate.form_data = prune_form_data_to_schema(new_snapshot, estimate.form_data)

    locked_statuses = {
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
        EstimateStatus.COMPLETED.value,
    }
    if is_contact_user(user) and "rate_card_id" in update_data:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Contact accounts cannot change rate cards",
                "code": "CONTACT_ACCESS_DENIED",
            },
        )
    if "rate_card_id" in update_data and estimate.status in locked_statuses:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Rate card cannot be changed after calculation",
                "code": "RATE_CARD_LOCKED_ON_ESTIMATE",
            },
        )

    if "rate_card_id" in update_data and update_data["rate_card_id"] is not None:
        await get_rate_card_for_user(db, update_data["rate_card_id"], user)
        if update_data["rate_card_id"] != estimate.rate_card_id:
            estimate.maintenance_assumptions = mark_rate_card_auto_tune_enabled(
                estimate.maintenance_assumptions or {},
                enabled=False,
            )

    for field, new_value in update_data.items():
        old_value = getattr(estimate, field)
        if old_value != new_value:
            def _audit_value(value: Any) -> Any:
                if isinstance(value, uuid.UUID):
                    return str(value)
                return value

            changes[field] = {
                "old": _audit_value(old_value),
                "new": _audit_value(new_value),
            }
            setattr(estimate, field, new_value)

    if form_data_payload is not None:
        locale = normalize_locale(content_locale, estimate.locale)
        schema_snapshot = snapshot_fields(estimate.form_schema_snapshot)
        existing_locale_data = resolve_localized_dict(
            estimate.form_data,
            locale,
            estimate.locale,
        )
        merged_payload = {**existing_locale_data, **form_data_payload}
        normalized_payload = normalize_form_data(schema_snapshot, merged_payload)
        stored_form_data = store_localized_dict(estimate.form_data, locale, normalized_payload)
        if estimate.form_data != stored_form_data:
            changes["form_data"] = {
                "old": "updated",
                "new": locale,
            }
            estimate.form_data = stored_form_data

    if changes:
        await log_change(
            db,
            estimate_id=estimate.id,
            user_id=user.id,
            action="updated",
            changes=changes,
        )

    await db.commit()
    return await get_estimate(db, estimate.id)


async def update_feature_items(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: FeatureItemsUpdate,
    content_locale: str | None = None,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Feature items can only be edited during review",
                "code": "INVALID_STATUS",
            },
        )

    existing_ids = {item.id for item in estimate.feature_items}
    incoming_ids = {item.id for item in data.items if item.id is not None}
    removed_ids = existing_ids - incoming_ids

    if removed_ids:
        await db.execute(
            delete(FeatureItem).where(
                FeatureItem.estimate_id == estimate_id,
                FeatureItem.id.in_(removed_ids),
            )
        )

    items_by_id = {item.id: item for item in estimate.feature_items}
    updated_items: list[FeatureItem] = []
    locale = normalize_locale(content_locale, estimate.locale)

    for index, item_data in enumerate(data.items):
        localization = store_feature_item_localization(
            None,
            locale,
            name=item_data.name,
            description=item_data.description,
            phase=item_data.phase,
            role=item_data.role,
        )
        if item_data.id and item_data.id in items_by_id:
            item = items_by_id[item_data.id]
            item.sort_order = index
            item.name = item_data.name
            item.description = item_data.description
            item.hours = item_data.hours
            item.phase = item_data.phase
            item.role = item_data.role
            item.is_ai_generated = item_data.is_ai_generated
            item.localizations = store_feature_item_localization(
                item.localizations,
                locale,
                name=item_data.name,
                description=item_data.description,
                phase=item_data.phase,
                role=item_data.role,
            )
            updated_items.append(item)
        else:
            item = FeatureItem(
                estimate_id=estimate_id,
                sort_order=index,
                name=item_data.name,
                description=item_data.description,
                hours=item_data.hours,
                phase=item_data.phase,
                role=item_data.role,
                is_ai_generated=item_data.is_ai_generated,
                localizations=localization,
            )
            db.add(item)
            updated_items.append(item)

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="feature_items_updated",
        changes={"count": len(updated_items)},
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def update_extracted_data(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: ExtractedDataUpdate,
    content_locale: str | None = None,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Extracted data can only be edited during review",
                "code": "INVALID_STATUS",
            },
        )

    locale = normalize_locale(content_locale, estimate.locale)
    current = resolve_localized_dict(estimate.extracted_data, locale, estimate.locale)
    update_data = data.model_dump(exclude_unset=True)
    current.update(update_data)
    estimate.extracted_data = store_localized_dict(estimate.extracted_data, locale, current)

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="extracted_data_updated",
        changes={"fields": list(update_data.keys())},
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def update_nrc_rc_assumptions(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    data: NrcRcAssumptionsUpdate,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "NRC/RC assumptions can only be edited during review or after calculation",
                "code": "INVALID_STATUS",
            },
        )

    assumptions = NrcRcAssumptions(
        setup_cost_items=data.setup_cost_items,
        monthly_rc_items=data.monthly_rc_items,
        source="manual",
        complexity_level=data.complexity_level,
    )
    estimate.nrc_rc_assumptions = assumptions.model_dump()

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="nrc_rc_assumptions_updated",
        changes={
            "setup_item_count": len(data.setup_cost_items),
            "monthly_item_count": len(data.monthly_rc_items),
        },
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def _get_active_rate_card_version(db: AsyncSession, user: User) -> RateCardVersion:
    rate_card = await get_active_rate_card(db, user)
    if not rate_card:
        raise HTTPException(
            status_code=400,
            detail={"error": "No active rate card configured", "code": "RATE_CARD_NOT_FOUND"},
        )
    return await get_latest_version_for_card(db, rate_card.id)


async def _resolve_rate_card_version_for_gantt(
    db: AsyncSession,
    estimate: Estimate,
    user: User,
) -> RateCardVersion:
    if estimate.rate_card_version_id:
        version_result = await db.execute(
            select(RateCardVersion).where(RateCardVersion.id == estimate.rate_card_version_id)
        )
        version = version_result.scalar_one_or_none()
        if version:
            return version
    if estimate.rate_card_id:
        await get_rate_card_for_user(db, estimate.rate_card_id, user)
        return await get_latest_version_for_card(db, estimate.rate_card_id)
    return await _get_active_rate_card_version(db, user)


def _gantt_items_from_estimate(
    estimate: Estimate,
    display_locale: str | None = None,
) -> list[GanttFeatureItem]:
    resolved_locale = normalize_locale(display_locale, estimate.locale)
    fallback_locale = normalize_locale(estimate.locale, resolved_locale)
    items: list[GanttFeatureItem] = []
    for item in sorted(estimate.feature_items, key=lambda row: row.sort_order):
        fields = resolve_feature_item_fields(
            name=item.name,
            description=item.description,
            phase=item.phase,
            role=item.role,
            localizations=item.localizations,
            display_locale=resolved_locale,
            fallback_locale=fallback_locale,
        )
        items.append(
            GanttFeatureItem(
                id=str(item.id),
                sort_order=item.sort_order,
                name=fields["name"],
                hours=float(item.hours),
                phase=fields["phase"],
                role=fields["role"],
            )
        )
    return items


def _resolve_project_start_date(
    estimate: Estimate,
    override: date | None = None,
) -> date:
    if override is not None:
        return override
    if estimate.project_start_date is not None:
        return estimate.project_start_date
    return default_project_start_date()


async def get_gantt_timeline(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
    start_date: date | None = None,
    display_locale: str | None = None,
) -> dict[str, Any]:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if not estimate.feature_items:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "At least one feature item is required",
                "code": "FEATURE_ITEMS_REQUIRED",
            },
        )

    version = await _resolve_rate_card_version_for_gantt(db, estimate, user)
    rate_settings = RateCardSettings.model_validate(
        normalize_settings_dict(dict(version.settings or {}))
    )
    resolved_start = _resolve_project_start_date(estimate, start_date)

    gantt_items = _gantt_items_from_estimate(estimate, display_locale=display_locale)
    phase_names = [phase.name for phase in rate_settings.phases]

    role_headcount: dict[str, int] | None = None
    calculation = estimate.calculation_result or {}
    breakdown = calculation.get("role_breakdown") or []
    if breakdown:
        role_headcount = {
            str(row["role"]).strip(): max(1, int(row.get("personnel_count") or 1))
            for row in breakdown
            if float(row.get("hours") or 0) > 0
        }

    if role_headcount:
        return build_gantt_timeline(
            gantt_items,
            phase_names,
            resolved_start,
            role_headcount=role_headcount,
        )

    return build_gantt_timeline_two_pass(gantt_items, phase_names, resolved_start)


async def run_calculation(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    recalculate_with_current_rates: bool = False,
    project_start_date: date | None = None,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Calculation requires review or calculated status",
                "code": "INVALID_STATUS",
            },
        )

    if not estimate.feature_items:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "At least one feature item is required",
                "code": "FEATURE_ITEMS_REQUIRED",
            },
        )

    if recalculate_with_current_rates and not can_access_estimate(estimate, user):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Only admin or estimate owner can recalculate with current rates",
                "code": "FORBIDDEN",
            },
        )

    if not estimate.rate_card_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "A rate card must be selected before calculation",
                "code": "RATE_CARD_REQUIRED",
            },
        )

    resolved_locale = normalize_locale(estimate.locale, estimate.locale)
    fallback_locale = normalize_locale(estimate.locale, resolved_locale)
    form_data = resolve_localized_dict(estimate.form_data, resolved_locale, fallback_locale)
    schema_snapshot = snapshot_fields(estimate.form_schema_snapshot)
    if schema_snapshot:
        form_data = normalize_form_data(schema_snapshot, form_data)

    missing_fields = missing_questionnaire_fields_for_calculation(
        has_documents=bool(estimate.documents),
        form_data=form_data,
        contact_user=is_contact_user(user),
    )
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Complete the questionnaire before calculating",
                "code": "QUESTIONNAIRE_INCOMPLETE",
                "fields": missing_fields,
            },
        )

    await get_rate_card_for_user(db, estimate.rate_card_id, user)

    if recalculate_with_current_rates:
        version = await get_latest_version_for_card(db, estimate.rate_card_id)
        estimate.rate_card_version_id = version.id
    elif estimate.rate_card_version_id:
        version_result = await db.execute(
            select(RateCardVersion).where(RateCardVersion.id == estimate.rate_card_version_id)
        )
        version = version_result.scalar_one_or_none()
        if not version or version.rate_card_id != estimate.rate_card_id:
            version = await get_latest_version_for_card(db, estimate.rate_card_id)
            estimate.rate_card_version_id = version.id
    else:
        version = await get_latest_version_for_card(db, estimate.rate_card_id)
        estimate.rate_card_version_id = version.id

    feature_inputs = [
        CalcFeatureItemInput(
            name=item.name,
            hours=float(item.hours),
            phase=item.phase,
            role=item.role,
        )
        for item in estimate.feature_items
    ]
    rate_settings = RateCardSettings.model_validate(
        normalize_settings_dict(dict(version.settings or {}))
    )
    form_development_approach_applied = False
    form_approach = str(form_data.get("development_approach") or "").strip()
    if form_approach:
        try:
            approach = DevelopmentApproach(form_approach)
            rate_settings = rate_settings.model_copy(update={"development_approach": approach})
            form_development_approach_applied = True
        except ValueError:
            pass

    source_currency = rate_settings.currency
    source_region = rate_settings.region
    jpy_settings, fx_snapshot = await rate_card_settings_to_jpy(rate_settings, get_fx_service())
    feature_dicts = [
        {
            "name": item.name,
            "hours": float(item.hours),
            "phase": item.phase,
            "role": item.role,
        }
        for item in estimate.feature_items
    ]
    maintenance = dict(estimate.maintenance_assumptions or {})
    extracted = (
        resolve_localized_dict(estimate.extracted_data, estimate.locale, estimate.locale)
        if estimate.extracted_data
        else {}
    )
    resolved_nrc_rc = resolve_nrc_rc_assumptions(
        estimate,
        feature_items=feature_dicts,
        form_data=form_data,
        extracted_data=extracted if isinstance(extracted, dict) else {},
        rate_card_settings=jpy_settings.model_dump(),
    )
    jpy_settings = RateCardSettings.model_validate(
        normalize_settings_dict(
            apply_nrc_rc_assumptions_to_settings(jpy_settings.model_dump(), resolved_nrc_rc)
        )
    )
    cost_drivers = extracted.get("cost_drivers") or [] if isinstance(extracted, dict) else []
    resolved_start = _resolve_project_start_date(estimate, project_start_date)
    if project_start_date is not None or estimate.project_start_date is None:
        estimate.project_start_date = resolved_start

    gantt_feature_items = [
        GanttFeatureItemInput(
            id=str(item.id),
            sort_order=item.sort_order,
            name=item.name,
            hours=float(item.hours),
            phase=item.phase,
            role=item.role,
        )
        for item in sorted(estimate.feature_items, key=lambda row: row.sort_order)
    ]

    discount_rate = await get_estimate_discount_rate(db)
    markup_rate = await get_estimate_markup_rate(db)

    try:
        result = calculate_estimate(
            feature_inputs,
            jpy_settings,
            maintenance,
            rate_card_version_id=str(version.id),
            cost_drivers=cost_drivers,
            project_start_date=resolved_start,
            gantt_feature_items=gantt_feature_items,
            discount_rate=discount_rate,
        )
    except CalculationError:
        raise

    internal_pricing = compute_internal_pricing(result, markup_rate)
    result_payload = result.model_dump()
    if internal_pricing is not None:
        result_payload["internal_pricing"] = internal_pricing
    result_payload["rc_detailed_breakdown"] = build_detailed_rc_breakdown(
        result_payload,
        locale=normalize_locale(estimate.locale, estimate.locale),
        markup_rate=markup_rate,
        cost_breakdown_mode=rate_settings.cost_breakdown_mode,
    )
    result_payload["cost_breakdown_mode"] = rate_settings.cost_breakdown_mode
    result_payload["fx_snapshot"] = fx_snapshot
    result_payload["source_currency"] = source_currency
    result_payload["source_region"] = source_region
    if form_development_approach_applied:
        result_payload["form_development_approach_applied"] = True
    result_payload["nrc_rc_assumptions"] = resolved_nrc_rc
    result_payload["nrc_rc_source"] = resolved_nrc_rc.get("source", "derived")

    gantt = result_payload.get("gantt") or {}
    total_working_days = int(gantt.get("total_working_days") or 0)
    delivery_schedule = str(form_data.get("delivery_schedule") or "").strip() or None
    result_payload["delivery_schedule_advisory"] = build_delivery_schedule_advisory(
        delivery_schedule,
        total_working_days,
    )
    budget_comparison = build_budget_comparison(
        form_data.get("client_budget"),
        int(result.nrc["total_jpy"]),
    )
    if budget_comparison:
        result_payload["budget_comparison"] = budget_comparison

    estimate.calculation_result = result_payload
    estimate.status = EstimateStatus.CALCULATED.value

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="calculated",
        changes={
            "rate_card_version_id": str(version.id),
            "recalculate_with_current_rates": recalculate_with_current_rates,
            "first_year_total_jpy": result.first_year_total_jpy,
        },
    )
    await db.commit()
    return await get_estimate(db, estimate_id)


async def get_audit_log(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> list[AuditLog]:
    await get_estimate_for_user(db, estimate_id, user)

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.estimate_id == estimate_id)
        .order_by(AuditLog.created_at.asc())
    )
    return list(result.scalars().all())


async def tune_rate_card_from_extraction(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
) -> Estimate:
    from app.estimates.rate_card_stale import (
        RATE_CARD_FINGERPRINT_KEY,
        mark_rate_card_auto_tune_enabled,
        mark_rate_card_tune_recommended,
    )
    from app.rate_cards.complexity import score_project_complexity
    from app.rate_cards.fingerprint import get_latest_rate_card_fingerprint
    from app.rate_cards.generation import (
        regenerate_rate_card_after_extraction,
        should_tune_rate_card_on_extract,
    )

    estimate = await get_estimate_for_user(db, estimate_id, user)
    if estimate.status not in (
        EstimateStatus.REVIEW.value,
        EstimateStatus.CALCULATED.value,
        EstimateStatus.EXPORTED.value,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Rate card tuning requires extracted requirements",
                "code": "INVALID_STATUS",
            },
        )
    if not estimate.extracted_data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Extract requirements before tuning the rate card",
                "code": "EXTRACTION_REQUIRED",
            },
        )
    if not estimate.rate_card_id:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Assign a rate card before tuning",
                "code": "RATE_CARD_REQUIRED",
            },
        )

    if not await should_tune_rate_card_on_extract(db, estimate):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Enable auto-tune on the estimate rate card before tuning",
                "code": "AUTO_TUNE_DISABLED",
            },
        )

    locale = normalize_locale(estimate.locale, estimate.locale)
    extracted_data = resolve_localized_dict(estimate.extracted_data, locale, estimate.locale)
    feature_items = [
        {
            "name": item.name,
            "hours": float(item.hours),
            "phase": item.phase,
            "role": item.role,
        }
        for item in sorted(estimate.feature_items, key=lambda row: row.sort_order)
    ]
    form_data = resolve_localized_dict(estimate.form_data, locale, estimate.locale)
    profile = extracted_data.get("complexity_profile")
    if not isinstance(profile, dict):
        profile = score_project_complexity(
            feature_items=feature_items,
            extracted_data=extracted_data,
            form_data=form_data,
        ).model_dump()

    await regenerate_rate_card_after_extraction(
        db,
        estimate_id,
        user.id,
        complexity_profile=profile,
        maintenance_assumptions=dict(estimate.maintenance_assumptions or {}),
    )
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one()
    maintenance = mark_rate_card_auto_tune_enabled(
        estimate.maintenance_assumptions or {},
        enabled=True,
    )
    maintenance = mark_rate_card_tune_recommended(maintenance, recommended=False)
    fingerprint = await get_latest_rate_card_fingerprint(db, estimate.rate_card_id)
    if fingerprint:
        maintenance[RATE_CARD_FINGERPRINT_KEY] = fingerprint
    estimate.maintenance_assumptions = maintenance
    await db.commit()
    return await get_estimate(db, estimate_id)


async def create_rate_card_for_estimate(
    db: AsyncSession,
    user: User,
    estimate_id: uuid.UUID,
    body: CreateEstimateRateCardRequest,
) -> Estimate:
    estimate = await get_estimate_for_user(db, estimate_id, user)

    if estimate.status not in (EstimateStatus.DRAFT.value, EstimateStatus.REVIEW.value):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Rate cards can only be created for draft or review estimates",
                "code": "INVALID_STATUS",
            },
        )

    card, _version = await create_rate_card_with_settings(
        db,
        user=user,
        name=body.name,
        settings=body.settings,
        activate=body.activate,
    )
    estimate.rate_card_id = card.id
    estimate.maintenance_assumptions = mark_rate_card_auto_tune_enabled(
        estimate.maintenance_assumptions or {},
        enabled=True,
    )

    await log_change(
        db,
        estimate_id=estimate.id,
        user_id=user.id,
        action="rate_card_created",
        changes={
            "rate_card_id": str(card.id),
            "rate_card_name": card.name,
        },
    )
    await db.commit()
    return await get_estimate(db, estimate.id)


async def delete_estimate(
    db: AsyncSession,
    estimate_id: uuid.UUID,
    user: User,
) -> None:
    result = await db.execute(
        select(Estimate)
        .where(Estimate.id == estimate_id)
        .options(
            selectinload(Estimate.documents),
            selectinload(Estimate.exports),
        )
    )
    estimate = result.scalar_one_or_none()
    if not estimate:
        raise HTTPException(
            status_code=404,
            detail={"error": "Estimate not found", "code": "ESTIMATE_NOT_FOUND"},
        )
    require_estimate_access(estimate, user)

    storage = get_storage_backend()
    for document in estimate.documents:
        if await storage.exists(document.storage_path):
            await storage.delete(document.storage_path)
    for export in estimate.exports:
        if await storage.exists(export.storage_path):
            await storage.delete(export.storage_path)

    await db.delete(estimate)
    await db.commit()
