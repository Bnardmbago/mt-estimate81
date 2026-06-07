from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from app.exports.markdown import (
    LABELS,
    _build_feature_rows,
    _build_form_fields,
    format_date,
)
from app.models.estimate import Estimate

SHEET_NAMES = {
    "en": {
        "summary": "Summary",
        "features": "Features",
        "phase": "Phase Breakdown",
        "role": "Role Breakdown",
        "nrc": "NRC Detail",
        "rc": "RC Detail",
        "assumptions": "Assumptions",
    },
    "ja": {
        "summary": "サマリー",
        "features": "機能明細",
        "phase": "フェーズ内訳",
        "role": "ロール内訳",
        "nrc": "NRC内訳",
        "rc": "RC内訳",
        "assumptions": "前提条件",
    },
}

CURRENCY_FORMAT = '"¥"#,##0'
PERCENT_FORMAT = "0%"


def _header_font() -> Font:
    return Font(bold=True)


def _write_key_value_rows(
    ws,
    rows: list[tuple[str, Any]],
    *,
    start_row: int = 1,
    value_format: str | None = None,
) -> int:
    row_idx = start_row
    for label, value in rows:
        ws.cell(row=row_idx, column=1, value=label).font = _header_font()
        cell = ws.cell(row=row_idx, column=2, value=value)
        if value_format:
            cell.number_format = value_format
        row_idx += 1
    return row_idx


def _write_table(
    ws,
    headers: list[str],
    rows: list[list[Any]],
    *,
    start_row: int = 1,
    column_formats: dict[int, str] | None = None,
) -> int:
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=start_row, column=col_idx, value=header).font = _header_font()

    row_idx = start_row + 1
    for row in rows:
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            if column_formats and col_idx in column_formats:
                cell.number_format = column_formats[col_idx]
        row_idx += 1
    return row_idx


def _auto_width(ws) -> None:
    for column_cells in ws.columns:
        max_length = 0
        column = column_cells[0].column_letter
        for cell in column_cells:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[column].width = min(max_length + 2, 50)


def _build_summary_sheet(
    ws,
    estimate: Estimate,
    locale: str,
    labels: dict[str, str],
    calculation: dict[str, Any],
    *,
    rate_card_name: str | None,
    rate_card_version_number: int | None,
    generated_at: datetime,
) -> None:
    extracted = estimate.extracted_data or {}
    row_idx = _write_key_value_rows(
        ws,
        [
            (labels["project_name"], estimate.project_name),
            (labels["client_name"], estimate.client_name),
            (labels["generated_date"], format_date(generated_at, locale)),
        ],
    )
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["effort_summary"]).font = _header_font()
    row_idx += 1
    row_idx = _write_key_value_rows(
        ws,
        [
            (labels["total_hours"], calculation.get("total_effort_hours", 0)),
            (labels["total_days"], calculation.get("total_effort_days", 0)),
        ],
        start_row=row_idx,
    )
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["first_year_total"]).font = _header_font()
    ws.cell(row=row_idx, column=2, value=calculation.get("first_year_total_jpy", 0)).number_format = (
        CURRENCY_FORMAT
    )
    row_idx += 2

    ws.cell(row=row_idx, column=1, value=labels["risks_gaps"]).font = _header_font()
    row_idx += 1
    risks = extracted.get("risks") or []
    gaps = extracted.get("gaps") or []
    if risks:
        ws.cell(row=row_idx, column=1, value=labels["risks"]).font = _header_font()
        row_idx += 1
        for item in risks:
            ws.cell(row=row_idx, column=1, value=f"- {item}")
            row_idx += 1
    if gaps:
        ws.cell(row=row_idx, column=1, value=labels["gaps"]).font = _header_font()
        row_idx += 1
        for item in gaps:
            ws.cell(row=row_idx, column=1, value=f"- {item}")
            row_idx += 1
    if not risks and not gaps:
        ws.cell(row=row_idx, column=1, value=labels["none"])
        row_idx += 1
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["confidence_notes"]).font = _header_font()
    row_idx += 1
    ws.cell(row=row_idx, column=1, value=extracted.get("confidence_notes") or labels["none"])
    row_idx += 2

    ws.cell(row=row_idx, column=1, value=labels["rate_card_reference"]).font = _header_font()
    row_idx += 1
    _write_key_value_rows(
        ws,
        [
            (labels["rate_card_name"], rate_card_name or labels["none"]),
            (
                labels["rate_card_version"],
                rate_card_version_number
                if rate_card_version_number is not None
                else labels["none"],
            ),
        ],
        start_row=row_idx,
    )


def _build_features_sheet(ws, estimate: Estimate, labels: dict[str, str]) -> None:
    feature_rows = _build_feature_rows(estimate)
    _write_table(
        ws,
        [
            labels["feature_name"],
            labels["feature_description"],
            labels["feature_phase"],
            labels["feature_role"],
            labels["feature_hours"],
            labels["feature_days"],
        ],
        [
            [
                item["name"],
                item["description"],
                item["phase"],
                item["role"],
                item["hours"],
                item["days"],
            ]
            for item in feature_rows
        ],
    )


def _build_phase_sheet(ws, calculation: dict[str, Any], labels: dict[str, str]) -> None:
    phase_rows = calculation.get("phase_breakdown") or []
    _write_table(
        ws,
        [labels["phase"], labels["hours"], labels["percentage"]],
        [[row["phase"], row["hours"], row["percentage"]] for row in phase_rows],
        column_formats={3: PERCENT_FORMAT},
    )


def _build_role_sheet(ws, calculation: dict[str, Any], labels: dict[str, str]) -> None:
    role_rows = calculation.get("role_breakdown") or []
    headers = [labels["role"], labels["hours"], labels["rate"], labels["cost"]]
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=header).font = _header_font()

    for row_idx, row in enumerate(role_rows, start=2):
        ws.cell(row=row_idx, column=1, value=row["role"])
        ws.cell(row=row_idx, column=2, value=row["hours"])
        rate_cell = ws.cell(row=row_idx, column=3, value=row["rate_jpy"])
        rate_cell.number_format = CURRENCY_FORMAT
        cost_cell = ws.cell(row=row_idx, column=4, value=f"=B{row_idx}*C{row_idx}")
        cost_cell.number_format = CURRENCY_FORMAT


def _build_nrc_sheet(ws, calculation: dict[str, Any], labels: dict[str, str]) -> None:
    nrc = calculation.get("nrc") or {}
    _write_key_value_rows(
        ws,
        [
            (labels["labor"], nrc.get("labor_jpy", 0)),
            (labels["setup"], nrc.get("setup_jpy", 0)),
            (labels["contingency"], nrc.get("contingency_jpy", 0)),
            (labels["overhead"], nrc.get("overhead_jpy", 0)),
            (labels["nrc_total"], nrc.get("total_jpy", 0)),
        ],
        value_format=CURRENCY_FORMAT,
    )
    ws.cell(row=5, column=1).font = _header_font()
    ws.cell(row=5, column=2).font = _header_font()


def _build_rc_sheet(ws, calculation: dict[str, Any], labels: dict[str, str]) -> None:
    rc = calculation.get("rc") or {}
    row_idx = 1
    ws.cell(row=row_idx, column=1, value=labels["monthly_items"]).font = _header_font()
    ws.cell(row=row_idx, column=2, value=labels["cost"]).font = _header_font()
    row_idx += 1

    for item in rc.get("monthly_items") or []:
        ws.cell(row=row_idx, column=1, value=item["name"])
        cell = ws.cell(row=row_idx, column=2, value=item["amount_jpy"])
        cell.number_format = CURRENCY_FORMAT
        row_idx += 1

    for label, key in (
        (labels["maintenance"], "maintenance_jpy"),
        (labels["monthly_total"], "monthly_total_jpy"),
        (labels["annual_total"], "annual_total_jpy"),
    ):
        ws.cell(row=row_idx, column=1, value=label).font = _header_font()
        cell = ws.cell(row=row_idx, column=2, value=rc.get(key, 0))
        cell.number_format = CURRENCY_FORMAT
        cell.font = _header_font()
        row_idx += 1


def _build_assumptions_sheet(
    ws,
    estimate: Estimate,
    locale: str,
    labels: dict[str, str],
) -> None:
    extracted = estimate.extracted_data or {}
    form_data = estimate.form_data or {}
    row_idx = 1

    ws.cell(row=row_idx, column=1, value=labels["input_assumptions"]).font = _header_font()
    row_idx += 1
    form_fields = _build_form_fields(form_data, locale)
    if form_fields:
        for field in form_fields:
            ws.cell(row=row_idx, column=1, value=field["label"]).font = _header_font()
            ws.cell(row=row_idx, column=2, value=field["value"])
            row_idx += 1
    else:
        ws.cell(row=row_idx, column=1, value=labels["none"])
        row_idx += 1
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["extracted_requirements"]).font = _header_font()
    row_idx += 1

    sections = [
        (labels["functional_requirements"], extracted.get("functional_requirements")),
        (labels["non_functional_requirements"], extracted.get("non_functional_requirements")),
        (labels["user_roles"], extracted.get("user_roles")),
        (labels["modules"], extracted.get("modules")),
        (labels["external_systems"], extracted.get("external_systems")),
    ]
    has_content = False
    for section_label, items in sections:
        if not items:
            continue
        has_content = True
        ws.cell(row=row_idx, column=1, value=section_label).font = _header_font()
        row_idx += 1
        for item in items:
            ws.cell(row=row_idx, column=1, value=f"- {item}")
            row_idx += 1
    if not has_content:
        ws.cell(row=row_idx, column=1, value=labels["none"])


def generate_excel(
    estimate: Estimate,
    locale: str,
    *,
    rate_card_name: str | None = None,
    rate_card_version_number: int | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    calculation = estimate.calculation_result or {}
    labels = LABELS[locale]
    sheet_names = SHEET_NAMES[locale]
    generated_at = generated_at or datetime.utcnow()

    wb = Workbook()
    wb.remove(wb.active)

    summary_ws = wb.create_sheet(sheet_names["summary"])
    _build_summary_sheet(
        summary_ws,
        estimate,
        locale,
        labels,
        calculation,
        rate_card_name=rate_card_name,
        rate_card_version_number=rate_card_version_number,
        generated_at=generated_at,
    )
    _auto_width(summary_ws)

    features_ws = wb.create_sheet(sheet_names["features"])
    _build_features_sheet(features_ws, estimate, labels)
    _auto_width(features_ws)

    phase_ws = wb.create_sheet(sheet_names["phase"])
    _build_phase_sheet(phase_ws, calculation, labels)
    _auto_width(phase_ws)

    role_ws = wb.create_sheet(sheet_names["role"])
    _build_role_sheet(role_ws, calculation, labels)
    _auto_width(role_ws)

    nrc_ws = wb.create_sheet(sheet_names["nrc"])
    _build_nrc_sheet(nrc_ws, calculation, labels)
    _auto_width(nrc_ws)

    rc_ws = wb.create_sheet(sheet_names["rc"])
    _build_rc_sheet(rc_ws, calculation, labels)
    _auto_width(rc_ws)

    assumptions_ws = wb.create_sheet(sheet_names["assumptions"])
    _build_assumptions_sheet(assumptions_ws, estimate, locale, labels)
    _auto_width(assumptions_ws)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
