from typing import Any

PHASE_LABELS_JA: dict[str, str] = {
    "requirement": "要件定義／仕様分析",
    "requirements": "要件定義／仕様分析",
    "design": "設計",
    "development": "実装",
    "testing": "動作確認（QA）",
    "test": "動作確認（QA）",
    "qa": "動作確認（QA）",
    "deployment": "リリース",
    "management": "管理工数",
    "infrastructure": "インフラ",
}

ROLE_LABELS_JA: dict[str, str] = {
    "developer": "開発者",
    "engineer": "エンジニア",
    "pm": "プロジェクトマネージャー",
    "project manager": "プロジェクトマネージャー",
    "project_manager": "プロジェクトマネージャー",
    "qa": "QA",
    "qa engineer": "QAエンジニア",
    "tester": "テスター",
    "ba": "ビジネスアナリスト",
    "analyst": "アナリスト",
    "business analyst": "ビジネスアナリスト",
    "devops": "DevOps",
    "designer": "デザイナー",
    "ui designer": "UIデザイナー",
    "ux designer": "UXデザイナー",
    "architect": "アーキテクト",
    "support": "サポート",
    "full stack engineer": "フルスタックエンジニア",
    "full stack developer": "フルスタックエンジニア",
    "fullstack engineer": "フルスタックエンジニア",
    "fullstack developer": "フルスタックエンジニア",
    "mobile developer": "モバイル開発者",
    "mobile engineer": "モバイルエンジニア",
    "frontend developer": "フロントエンド開発者",
    "backend developer": "バックエンド開発者",
    "senior developer": "シニア開発者",
    "tech lead": "テックリード",
}

NRC_CATEGORY_LABELS_JA: dict[str, str] = {
    "Development": "開発",
    "Project Management": "プロジェクト管理",
    "Business Analysis": "ビジネス分析",
    "QA": "QA",
    "DevOps": "DevOps",
    "Security Setup": "セキュリティセットアップ",
    "Software Setup": "ソフトウェアセットアップ",
    "Data Migration": "データ移行",
    "Training": "トレーニング",
    "Infrastructure Setup": "インフラセットアップ",
    "Contingency": "予備費",
    "Overhead": "間接費",
}

RC_CATEGORY_LABELS_JA: dict[str, str] = {
    "Cloud Hosting": "クラウドホスティング",
    "Database": "データベース",
    "AI API Usage": "AI API利用",
    "Monitoring": "監視",
    "Backup": "バックアップ",
    "Software Licenses": "ソフトウェアライセンス",
    "Security": "セキュリティ",
    "Maintenance": "保守",
    "Other": "その他",
}

LINE_ITEM_LABELS_JA: dict[str, str] = {
    "Maintenance and Support": "メンテナンスとサポート",
    "Maintenance support": "メンテナンスとサポート",
    "hosting": "ホスティング",
    "monitoring": "モニタリング",
    "Setup": "セットアップ",
    "Item": "項目",
}


def _normalize_key(value: str) -> str:
    return value.strip().lower().replace("_", " ")


def localize_phase(phase: str, locale: str) -> str:
    if locale != "ja" or not phase:
        return phase
    normalized = _normalize_key(phase)
    if normalized in PHASE_LABELS_JA:
        return PHASE_LABELS_JA[normalized]
    compact = normalized.replace(" ", "")
    for key, label in PHASE_LABELS_JA.items():
        if key.replace(" ", "") == compact:
            return label
    return phase


def localize_role(role: str, locale: str) -> str:
    if locale != "ja" or not role:
        return role
    normalized = _normalize_key(role)
    if normalized in ROLE_LABELS_JA:
        return ROLE_LABELS_JA[normalized]
    return role


def localize_nrc_category(category: str, locale: str) -> str:
    if locale != "ja" or not category:
        return category
    return NRC_CATEGORY_LABELS_JA.get(category, category)


def localize_rc_category(category: str, locale: str) -> str:
    if locale != "ja" or not category:
        return category
    return RC_CATEGORY_LABELS_JA.get(category, category)


def localize_line_item_name(name: str, locale: str) -> str:
    if locale != "ja" or not name:
        return name
    return LINE_ITEM_LABELS_JA.get(name, localize_nrc_category(name, locale))


def localize_feature_rows(rows: list[dict[str, Any]], locale: str) -> list[dict[str, Any]]:
    if locale != "ja":
        return rows
    localized: list[dict[str, Any]] = []
    for row in rows:
        localized.append(
            {
                **row,
                "phase": localize_phase(str(row.get("phase") or ""), locale),
                "role": localize_role(str(row.get("role") or ""), locale),
            }
        )
    return localized


def localize_gantt(gantt: dict[str, Any] | None, locale: str) -> dict[str, Any]:
    if not gantt or locale != "ja":
        return gantt or {}
    localized = dict(gantt)
    localized["tasks"] = [
        {
            **task,
            "phase_key": str(task.get("phase_key") or task.get("phase") or ""),
            "phase": localize_phase(str(task.get("phase") or ""), locale),
            "role": localize_role(str(task.get("role") or ""), locale),
        }
        for task in gantt.get("tasks") or []
    ]
    localized["phases"] = [
        {
            **phase,
            "phase_key": str(phase.get("phase_key") or phase.get("phase") or ""),
            "phase": localize_phase(str(phase.get("phase") or ""), locale),
        }
        for phase in gantt.get("phases") or []
    ]
    return localized


def apply_feature_names_to_gantt(
    gantt: dict[str, Any] | None,
    feature_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Overlay localized feature names onto gantt tasks when feature_item_id matches."""
    if not gantt:
        return {}
    by_id = {
        str(row["id"]): row["name"]
        for row in feature_items
        if row.get("id") is not None and row.get("name")
    }
    if not by_id:
        return gantt
    updated = dict(gantt)
    updated["tasks"] = [
        {
            **task,
            "name": by_id.get(str(task.get("feature_item_id")), task.get("name")),
        }
        for task in gantt.get("tasks") or []
    ]
    return updated


def localize_calculation_for_export(calculation: dict[str, Any], locale: str) -> dict[str, Any]:
    if locale != "ja":
        return calculation

    localized = dict(calculation)
    localized["phase_breakdown"] = [
        {
            **row,
            "phase": localize_phase(str(row.get("phase") or ""), locale),
        }
        for row in calculation.get("phase_breakdown") or []
    ]
    localized["role_breakdown"] = [
        {
            **row,
            "role": localize_role(str(row.get("role") or ""), locale),
        }
        for row in calculation.get("role_breakdown") or []
    ]
    localized["nrc_line_items"] = [
        {
            **row,
            "category": localize_nrc_category(str(row.get("category") or ""), locale),
            "item": localize_line_item_name(str(row.get("item") or ""), locale),
        }
        for row in calculation.get("nrc_line_items") or []
    ]
    localized["rc_line_items"] = [
        {
            **row,
            "category": localize_rc_category(str(row.get("category") or ""), locale),
            "item": localize_line_item_name(str(row.get("item") or ""), locale),
        }
        for row in calculation.get("rc_line_items") or []
    ]
    if calculation.get("gantt"):
        localized["gantt"] = localize_gantt(calculation.get("gantt") or {}, locale)
    return localized


def localize_rc_export_breakdown(breakdown: dict[str, Any], locale: str) -> dict[str, Any]:
    if locale != "ja":
        return breakdown

    from app.calculation.rc_detailed import RC_CATEGORY_CONTENT

    localized_items = []
    labels = RC_CATEGORY_CONTENT.get("ja", {})
    for row in breakdown.get("line_items") or []:
        category_key = row.get("category_key")
        if category_key and category_key in labels:
            meta = labels[category_key]
            localized_items.append(
                {
                    **row,
                    "category": meta["category"],
                    "service_description": row.get("service_description") or meta["service_description"],
                    "item": meta["category"],
                }
            )
            continue
        localized_items.append(
            {
                **row,
                "category": localize_rc_category(str(row.get("category") or ""), locale),
                "item": localize_line_item_name(str(row.get("item") or ""), locale),
            }
        )
    return {
        **breakdown,
        "line_items": localized_items,
    }
