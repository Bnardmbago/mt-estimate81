from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font

from app.models.estimate import Estimate

SHEET_NAMES = {
    "en": {
        "executive": "Executive",
        "features": "Features",
        "phase": "Phase Breakdown",
        "timeline": "Timeline",
        "role": "Role Breakdown",
        "nrc": "NRC Detail",
        "rc": "RC Detail",
        "assumptions": "Assumptions",
        "reference": "Risks & Reference",
    },
    "ja": {
        "executive": "エグゼクティブ",
        "features": "機能明細",
        "phase": "フェーズ内訳",
        "timeline": "タイムライン",
        "role": "ロール内訳",
        "nrc": "NRC内訳",
        "rc": "RC内訳",
        "assumptions": "前提条件",
        "reference": "リスク・参照",
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


def _write_bullet_list(ws, items: list[str], *, start_row: int) -> int:
    row_idx = start_row
    for item in items:
        ws.cell(row=row_idx, column=1, value=f"- {item}")
        row_idx += 1
    return row_idx


def _build_executive_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    project = ctx["project_summary"]
    executive = ctx["executive_summary"]

    row_idx = _write_key_value_rows(
        ws,
        [
            (labels["project_name"], project["project_name"]),
            (labels["client_name"], project["client_name"]),
            (labels["estimate_id"], project["estimate_id"]),
            (labels["export_revision"], project["export_revision"]),
            (labels["generated_date"], project["generated_date"]),
            (labels["estimate_type"], project["estimate_type"]),
        ],
    )
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["executive_cost_summary"]).font = _header_font()
    row_idx += 1
    currency_rows = [
        (labels["nrc_total"], executive["nrc_total_jpy"]),
        (labels["monthly_rc"], executive["monthly_rc_jpy"]),
        (labels["annual_rc"], executive["annual_rc_jpy"]),
        (labels["first_year_total_cost"], executive["first_year_total_jpy"]),
    ]
    for label, value in currency_rows:
        ws.cell(row=row_idx, column=1, value=label).font = _header_font()
        cell = ws.cell(row=row_idx, column=2, value=value)
        cell.number_format = CURRENCY_FORMAT
        row_idx += 1
    row_idx = _write_key_value_rows(
        ws,
        [
            (labels["confidence_score"], f"{executive['confidence_score']:.0f}%"),
            (labels["accuracy_level"], executive["accuracy_label"]),
        ],
        start_row=row_idx,
    )

    ws.cell(row=row_idx, column=1, value=labels["key_assumptions"]).font = _header_font()
    row_idx += 1
    key_assumptions = ctx.get("key_assumptions") or []
    if key_assumptions:
        row_idx = _write_key_value_rows(
            ws,
            [(row["label"], row["value"]) for row in key_assumptions],
            start_row=row_idx,
        )
    else:
        ws.cell(row=row_idx, column=1, value=labels["none"])
        row_idx += 1


def _build_features_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
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
            for item in ctx.get("feature_items") or []
        ],
    )


def _build_phase_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    calculation = ctx["calculation"]
    phase_rows = calculation.get("phase_breakdown") or []
    _write_table(
        ws,
        [labels["phase"], labels["hours"], labels["days"], labels["percentage"]],
        [
            [
                row["phase"],
                row["hours"],
                row.get("days", row["hours"] / 8),
                row["percentage"],
            ]
            for row in phase_rows
        ],
        column_formats={4: PERCENT_FORMAT},
    )


def _build_timeline_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    gantt = ctx.get("gantt") or {}
    tasks = gantt.get("tasks") or []

    if not tasks:
        ws.cell(row=1, column=1, value=labels["none"])
        return

    row_idx = _write_key_value_rows(
        ws,
        [
            (labels["gantt_project_start"], gantt.get("project_start_date")),
            (labels["gantt_project_end"], gantt.get("project_end_date")),
            (labels["gantt_total_working_days"], gantt.get("total_working_days")),
        ],
    )
    row_idx += 1
    _write_table(
        ws,
        [
            labels["gantt_task"],
            labels["phase"],
            labels["role"],
            labels["hours"],
            labels["gantt_start_date"],
            labels["gantt_end_date"],
            labels["gantt_duration_days"],
        ],
        [
            [
                task["name"],
                task["phase"],
                task["role"],
                task["hours"],
                task["start_date"],
                task["end_date"],
                task["duration_working_days"],
            ]
            for task in tasks
        ],
        start_row=row_idx,
    )


def _build_role_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    calculation = ctx["calculation"]
    role_rows = calculation.get("role_breakdown") or []
    headers = [labels["role"], labels["developers"], labels["hours"], labels["rate"], labels["cost"]]
    for col_idx, header in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=header).font = _header_font()

    for row_idx, row in enumerate(role_rows, start=2):
        ws.cell(row=row_idx, column=1, value=row["role"])
        ws.cell(row=row_idx, column=2, value=row.get("personnel_count", 1))
        ws.cell(row=row_idx, column=3, value=row["hours"])
        rate_cell = ws.cell(row=row_idx, column=4, value=row["rate_jpy"])
        rate_cell.number_format = CURRENCY_FORMAT
        cost_cell = ws.cell(row=row_idx, column=5, value=row["cost_jpy"])
        cost_cell.number_format = CURRENCY_FORMAT

    subtotal_row = len(role_rows) + 2
    ws.cell(row=subtotal_row, column=1, value=labels["subtotal"]).font = _header_font()
    subtotal_cell = ws.cell(
        row=subtotal_row,
        column=5,
        value=calculation.get("role_labor_subtotal_jpy", 0),
    )
    subtotal_cell.number_format = CURRENCY_FORMAT
    subtotal_cell.font = _header_font()


def _build_nrc_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    calculation = ctx["calculation"]
    line_items = calculation.get("nrc_line_items") or []
    row_idx = _write_table(
        ws,
        [labels["category"], labels["item"], labels["cost"]],
        [[row["category"], row["item"], row["cost_jpy"]] for row in line_items],
        column_formats={3: CURRENCY_FORMAT},
    )
    row_idx += 1
    ws.cell(row=row_idx, column=1, value=labels["nrc_total"]).font = _header_font()
    total_cell = ws.cell(row=row_idx, column=3, value=ctx["executive_summary"]["nrc_total_jpy"])
    total_cell.number_format = CURRENCY_FORMAT
    total_cell.font = _header_font()


def _build_rc_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    calculation = ctx["calculation"]
    line_items = calculation.get("rc_line_items") or []
    _write_table(
        ws,
        [labels["category"], labels["item"], labels["monthly"], labels["annual"]],
        [
            [
                row["category"],
                row["item"],
                row["monthly_jpy"],
                row["annual_jpy"],
            ]
            for row in line_items
        ],
        column_formats={3: CURRENCY_FORMAT, 4: CURRENCY_FORMAT},
    )


def _build_assumptions_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    extracted = ctx["extracted"]
    row_idx = 1

    ws.cell(row=row_idx, column=1, value=labels["input_assumptions"]).font = _header_font()
    row_idx += 1
    form_fields = ctx.get("form_fields") or []
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
        row_idx = _write_bullet_list(ws, items, start_row=row_idx)
    if not has_content:
        ws.cell(row=row_idx, column=1, value=labels["none"])


def _build_reference_sheet(ws, ctx: dict[str, Any]) -> None:
    labels = ctx["labels"]
    extracted = ctx["extracted"]
    rate_card = ctx["rate_card_reference"]
    row_idx = 1

    ws.cell(row=row_idx, column=1, value=labels["cost_drivers_title"]).font = _header_font()
    row_idx += 1
    cost_drivers = ctx.get("cost_drivers") or []
    if cost_drivers:
        row_idx = _write_table(
            ws,
            [labels["driver"], labels["impact"]],
            [[row["name"], row["impact_jpy"]] for row in cost_drivers],
            start_row=row_idx,
            column_formats={2: CURRENCY_FORMAT},
        )
    else:
        ws.cell(row=row_idx, column=1, value=labels["none"])
        row_idx += 2

    ws.cell(row=row_idx, column=1, value=labels["risks_gaps"]).font = _header_font()
    row_idx += 1
    for section_label, key in (
        (labels["risks"], "risks"),
        (labels["missing_information"], "gaps"),
        (labels["estimation_warnings"], "estimation_warnings"),
        (labels["assumption_risks"], "assumption_risks"),
    ):
        items = extracted.get(key) or []
        if not items:
            continue
        ws.cell(row=row_idx, column=1, value=section_label).font = _header_font()
        row_idx += 1
        row_idx = _write_bullet_list(ws, items, start_row=row_idx)
    row_idx += 1

    ws.cell(row=row_idx, column=1, value=labels["estimate_exclusions"]).font = _header_font()
    row_idx += 1
    exclusions = extracted.get("estimate_exclusions") or []
    if exclusions:
        row_idx = _write_bullet_list(ws, exclusions, start_row=row_idx)
    else:
        ws.cell(row=row_idx, column=1, value=labels["none"])
        row_idx += 2

    ws.cell(row=row_idx, column=1, value=labels["confidence_notes"]).font = _header_font()
    row_idx += 1
    row_idx = _write_key_value_rows(
        ws,
        [(labels["confidence_score"], f"{extracted.get('confidence_score', 0):.0f}%")],
        start_row=row_idx,
    )
    for key, label_key in (
        ("confidence_factors", "confidence_factors"),
        ("missing_inputs", "missing_inputs"),
        ("recommendations", "recommendations"),
    ):
        items = extracted.get(key) or []
        if not items:
            continue
        ws.cell(row=row_idx, column=1, value=labels[label_key]).font = _header_font()
        row_idx += 1
        row_idx = _write_bullet_list(ws, items, start_row=row_idx)
    notes = extracted.get("confidence_notes")
    if notes:
        ws.cell(row=row_idx, column=1, value=notes)
        row_idx += 2

    ws.cell(row=row_idx, column=1, value=labels["rate_card_reference"]).font = _header_font()
    row_idx += 1
    _write_key_value_rows(
        ws,
        [
            (labels["rate_card_name"], rate_card["name"]),
            (
                labels["rate_card_version"],
                rate_card["version_number"]
                if rate_card["version_number"] is not None
                else labels["none"],
            ),
            (labels["effective_date"], rate_card["effective_date"]),
            (labels["policy_version"], rate_card["policy_version"]),
        ],
        start_row=row_idx,
    )


def generate_excel(report_context: dict[str, Any], estimate: Estimate) -> bytes:
    locale = report_context["locale"]
    if locale not in ("ja", "en"):
        raise ValueError(f"Unsupported locale: {locale}")

    sheet_names = SHEET_NAMES[locale]
    wb = Workbook()
    wb.remove(wb.active)

    builders = [
        (sheet_names["executive"], _build_executive_sheet),
        (sheet_names["features"], _build_features_sheet),
        (sheet_names["phase"], _build_phase_sheet),
        (sheet_names["timeline"], _build_timeline_sheet),
        (sheet_names["role"], _build_role_sheet),
        (sheet_names["nrc"], _build_nrc_sheet),
        (sheet_names["rc"], _build_rc_sheet),
        (sheet_names["assumptions"], _build_assumptions_sheet),
        (sheet_names["reference"], _build_reference_sheet),
    ]

    for name, builder in builders:
        ws = wb.create_sheet(name)
        builder(ws, report_context)
        _auto_width(ws)

    del estimate  # retained for API compatibility; workbook uses report_context only

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
