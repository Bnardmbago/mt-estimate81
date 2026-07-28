"""Proposal content generation: structured stubs + optional AI enrichment."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

from app.proposals.generation_presets import (
    DEFAULT_PROPOSAL_AI_SETTINGS,
    GenerationPurpose,
    get_preset,
    min_tables_for_part,
    purpose_for_part,
)
from app.proposals.poc_pricing import price_poc_selection
from app.proposals.snapshot import feature_label

logger = logging.getLogger(__name__)

Locale = Literal["ja", "en"]

PHASE_LABELS = {
    "en": {
        "requirement": "Requirements",
        "design": "Design",
        "development": "Development",
        "testing": "Testing",
        "deployment": "Deployment",
        "management": "Project management",
    },
    "ja": {
        "requirement": "要件定義",
        "design": "設計",
        "development": "開発",
        "testing": "テスト",
        "deployment": "導入",
        "management": "プロジェクト管理",
    },
}


def _phase_label(phase: str, locale: Locale) -> str:
    key = str(phase or "").strip().lower()
    return PHASE_LABELS.get(locale, PHASE_LABELS["en"]).get(key, str(phase or "").replace("_", " "))


def _section(section_id: str, title: str, body: str, **extra: Any) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "body": body,
        "user_edited": False,
        **extra,
    }


def stub_assessment(snapshot: dict[str, Any], locale: Locale) -> dict[str, Any]:
    risks = snapshot.get("risks") or []
    modules = snapshot.get("modules") or []
    costs = snapshot.get("costs") or {}
    feature_count = len(snapshot.get("features") or [])
    has_ai = any(
        "ai" in str(m).lower() or "人工知能" in str(m)
        for m in modules
    ) or any(
        "ai" in str(f.get("name", "")).lower()
        for f in (snapshot.get("features") or [])
    )

    complexity = "high" if feature_count > 25 or has_ai else "medium" if feature_count > 10 else "low"
    poc_recommended = bool(has_ai or risks)

    if locale == "ja":
        return {
            "sections": [
                _section(
                    "feasibility",
                    "全体的な実現可能性",
                    "既存の見積データに基づき、本プロジェクトは実行可能な範囲です。スコープと体制を明確にすれば推進できます。",
                    rating=complexity if complexity != "high" else "medium",
                ),
                _section(
                    "readiness",
                    "プロジェクト準備状況",
                    "要求事項とモジュール構成は整理済みです。意思決定者の確認と前提条件の合意が次のステップです。",
                    rating="medium",
                ),
                _section(
                    "complexity",
                    "複雑さ",
                    f"作業項目数は約{feature_count}件です。モジュール数や外部連携の有無が複雑さの主な要因です。",
                    rating=complexity,
                    drivers=modules[:5],
                ),
                _section(
                    "risks",
                    "リスク",
                    "主なリスクは次のとおりです。",
                    bullets=risks[:8] or ["要求の変動", "技術的な不確実性"],
                ),
                _section(
                    "recommendation",
                    "推奨",
                    (
                        "高リスク領域を検証する概念実証（Proof of Concept）を先行することを推奨します。"
                        if poc_recommended
                        else "本見積の範囲で実装提案へ進むことを推奨します。"
                    ),
                ),
                _section(
                    "poc_recommendation",
                    "概念実証は必要か",
                    (
                        "はい。特に不確実性の高い機能を先に検証することを推奨します。"
                        if poc_recommended
                        else "必須ではありません。必要に応じて限定的な検証を検討できます。"
                    ),
                    poc_recommended=poc_recommended,
                ),
            ],
            "poc_recommended": poc_recommended,
            "summary_cost_note": (
                f"一次性のプロジェクト費用の目安: {costs.get('one_time_project_cost_jpy')} 円"
            ),
        }

    return {
        "sections": [
            _section(
                "feasibility",
                "Overall feasibility",
                "Based on the existing estimate, this project is feasible if scope and staffing remain aligned with the current plan.",
                rating="high" if complexity == "low" else "medium",
            ),
            _section(
                "readiness",
                "Project readiness",
                "Requirements and module structure are captured. Confirm stakeholder decisions and assumptions before kickoff.",
                rating="medium",
            ),
            _section(
                "complexity",
                "Complexity",
                f"About {feature_count} work items are planned. Module count and integrations are the main complexity drivers.",
                rating=complexity,
                drivers=modules[:5],
            ),
            _section(
                "risks",
                "Risks",
                "Key risks from the estimate analysis:",
                bullets=risks[:8] or ["Scope change", "Technical uncertainty"],
            ),
            _section(
                "recommendation",
                "Recommendation",
                (
                    "Proceed with a focused Proof of Concept for high-uncertainty areas before full delivery."
                    if poc_recommended
                    else "Proceed to a full implementation proposal based on the current estimate."
                ),
            ),
            _section(
                "poc_recommendation",
                "Is a Proof of Concept recommended?",
                (
                    "Yes. Validate the highest-risk capabilities first."
                    if poc_recommended
                    else "Not required. A limited validation can still be useful if stakeholders prefer it."
                ),
                poc_recommended=poc_recommended,
            ),
        ],
        "poc_recommended": poc_recommended,
        "summary_cost_note": (
            f"Indicative one-time project cost: {costs.get('one_time_project_cost_jpy')} JPY"
        ),
    }


def stub_proposal_body(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    features = snapshot.get("features") or []
    modules = snapshot.get("modules") or []
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}
    risks = snapshot.get("risks") or []
    project = snapshot.get("project_name") or "the project"
    client = snapshot.get("client_name") or "the client"

    included = [
        feature_label(f, locale) for f in features[:12] if feature_label(f, locale)
    ]
    excluded = (snapshot.get("assumptions") or [])[:8]
    if not excluded:
        excluded = ["Items not listed in the estimate scope", "Post go-live enhancements beyond monthly support"]

    phases = gantt.get("phases") or []
    milestones = []
    if gantt.get("project_start_date"):
        milestones.append(
            {
                "id": "kickoff",
                "name": "Project kickoff" if locale == "en" else "プロジェクト開始",
                "date": gantt.get("project_start_date"),
            }
        )
    for phase in phases:
        milestones.append(
            {
                "id": f"phase_{phase.get('phase')}",
                "name": _phase_label(str(phase.get("phase") or ""), locale),
                "date": phase.get("end_date"),
            }
        )
    if gantt.get("project_end_date"):
        milestones.append(
            {
                "id": "go_live",
                "name": "Delivery acceptance" if locale == "en" else "納品・検収",
                "date": gantt.get("project_end_date"),
            }
        )

    if locale == "ja":
        body = {
            "sections": [
                _section(
                    "executive_summary",
                    "エグゼクティブサマリー",
                    f"{client} 様向け「{project}」の実装提案です。要求分析と見積に基づき、範囲・スケジュール・費用の概要を示します。",
                ),
                _section(
                    "objectives",
                    "プロジェクト目的",
                    "ビジネス目標を達成するシステムを、合意した品質とスケジュールで提供すること。",
                    bullets=modules[:6] or ["業務要件の実現", "運用しやすい仕組みの構築"],
                ),
                _section(
                    "proposed_solution",
                    "提案する解決策",
                    "段階的な設計・開発・検証により、合意スコープを確実に届けます。",
                ),
                _section("included_scope", "含まれる範囲", "本提案に含まれる主な作業項目です。", bullets=included),
                _section("excluded_scope", "含まれない範囲", "本提案の対象外です。", bullets=excluded),
                _section(
                    "deliverables",
                    "成果物",
                    "主な成果物は次のとおりです。",
                    bullets=["要件・設計ドキュメント", "動作するシステム", "テスト結果", "引継ぎ資料"],
                ),
                _section(
                    "timeline_summary",
                    "スケジュール概要",
                    f"開始: {gantt.get('project_start_date') or '未設定'} / 終了: {gantt.get('project_end_date') or '未設定'} / 稼働日数目安: {gantt.get('total_working_days') or costs.get('total_effort_days')}",
                ),
                _section(
                    "cost_summary",
                    "費用概要",
                    "見積に基づく費用サマリーです（略語なし）。",
                    bullets=[
                        f"一次性のプロジェクト費用: {costs.get('one_time_project_cost_jpy')} 円",
                        f"月次の継続費用: {costs.get('monthly_recurring_cost_jpy')} 円",
                        f"初年度合計: {costs.get('first_year_total_jpy')} 円",
                    ],
                ),
                _section(
                    "assumptions",
                    "前提条件",
                    "本提案は次の前提に基づきます。",
                    bullets=snapshot.get("assumptions") or ["関係者のタイムリーな意思決定", "必要な情報・環境へのアクセス"],
                ),
                _section("risks", "リスク", "留意すべきリスクです。", bullets=risks[:8] or ["スコープ変更"]),
                _section(
                    "next_steps",
                    "次のステップ",
                    "ご確認のうえ、キックオフまたは概念実証の要否をご指示ください。",
                    bullets=["本提案内容の確認", "契約条件の合意", "開始日の確定"],
                ),
            ]
        }
    else:
        body = {
            "sections": [
                _section(
                    "executive_summary",
                    "Executive summary",
                    f"This proposal outlines a practical delivery plan for {project} for {client}, based on the completed estimate.",
                ),
                _section(
                    "objectives",
                    "Project objectives",
                    "Deliver a working solution that meets agreed business outcomes on a clear timeline and budget.",
                    bullets=modules[:6] or ["Deliver core business capabilities", "Establish a maintainable operating model"],
                ),
                _section(
                    "proposed_solution",
                    "Proposed solution",
                    "A phased design, build, and validation approach that delivers the agreed scope with clear checkpoints.",
                ),
                _section("included_scope", "Included scope", "Primary work items included in this proposal.", bullets=included),
                _section("excluded_scope", "Excluded scope", "Out of scope for this proposal.", bullets=excluded),
                _section(
                    "deliverables",
                    "Deliverables",
                    "Key deliverables include:",
                    bullets=[
                        "Requirements and design documentation",
                        "Working system",
                        "Test evidence",
                        "Handover materials",
                    ],
                ),
                _section(
                    "timeline_summary",
                    "Timeline summary",
                    f"Start: {gantt.get('project_start_date') or 'TBD'} · End: {gantt.get('project_end_date') or 'TBD'} · Working days: {gantt.get('total_working_days') or costs.get('total_effort_days')}",
                ),
                _section(
                    "cost_summary",
                    "Cost summary",
                    "Figures are taken from the estimate (stakeholder wording).",
                    bullets=[
                        f"One-time project cost: {costs.get('one_time_project_cost_jpy')} JPY",
                        f"Monthly recurring cost: {costs.get('monthly_recurring_cost_jpy')} JPY",
                        f"First-year total: {costs.get('first_year_total_jpy')} JPY",
                    ],
                ),
                _section(
                    "assumptions",
                    "Assumptions",
                    "This proposal assumes:",
                    bullets=snapshot.get("assumptions")
                    or ["Timely stakeholder decisions", "Access to required systems and information"],
                ),
                _section("risks", "Risks", "Risks to monitor:", bullets=risks[:8] or ["Scope change"]),
                _section(
                    "next_steps",
                    "Next steps",
                    "Please review this pack and confirm whether to proceed to kickoff or a Proof of Concept.",
                    bullets=["Confirm proposal content", "Agree commercial terms", "Set a start date"],
                ),
            ]
        }

    diagrams = [
        {
            "id": "solution_overview",
            "title": "Proposed solution overview" if locale == "en" else "提案ソリューション概要",
            "engine": "mermaid",
            "source": (
                "flowchart TD\n"
                f"  A[{_escape_mermaid(client)}] --> B[{_escape_mermaid(project)}]\n"
                "  B --> C[Design]\n"
                "  C --> D[Build]\n"
                "  D --> E[Validate]\n"
                "  E --> F[Operate]\n"
            ),
        },
        {
            "id": "delivery_flow",
            "title": "Delivery flow" if locale == "en" else "デリバリーフロー",
            "engine": "mermaid",
            "source": (
                "flowchart TD\n"
                "  K[Kickoff] --> D[Design]\n"
                "  D --> B[Build]\n"
                "  B --> T[Test]\n"
                "  T --> A[Acceptance]\n"
                "  A --> O[Operate]\n"
            ),
        },
    ]
    if locale == "ja":
        tables = [
            {
                "id": "cost_timeline",
                "title": "費用・スケジュール概要",
                "headers": ["項目", "値"],
                "rows": [
                    ["一次性のプロジェクト費用", f"{costs.get('one_time_project_cost_jpy')} 円"],
                    ["月次の継続費用", f"{costs.get('monthly_recurring_cost_jpy')} 円"],
                    ["初年度合計", f"{costs.get('first_year_total_jpy')} 円"],
                    [
                        "稼働日数目安",
                        str(gantt.get("total_working_days") or costs.get("total_effort_days") or "—"),
                    ],
                ],
            },
            {
                "id": "risks_mitigation",
                "title": "リスクと緩和策",
                "headers": ["リスク", "影響", "緩和策"],
                "rows": [
                    [str(r), "中〜高", "早期に範囲を確定し段階的に検証"]
                    for r in (risks[:4] or ["スコープ変更"])
                ],
            },
        ]
    else:
        tables = [
            {
                "id": "cost_timeline",
                "title": "Cost and timeline summary",
                "headers": ["Item", "Value"],
                "rows": [
                    [
                        "One-time project cost",
                        f"{costs.get('one_time_project_cost_jpy')} JPY",
                    ],
                    [
                        "Monthly recurring cost",
                        f"{costs.get('monthly_recurring_cost_jpy')} JPY",
                    ],
                    ["First-year total", f"{costs.get('first_year_total_jpy')} JPY"],
                    [
                        "Working days (reference)",
                        str(gantt.get("total_working_days") or costs.get("total_effort_days") or "—"),
                    ],
                ],
            },
            {
                "id": "risks_mitigation",
                "title": "Risks and mitigation",
                "headers": ["Risk", "Impact", "Mitigation"],
                "rows": [
                    [str(r), "Medium–High", "Confirm scope early and validate in stages"]
                    for r in (risks[:4] or ["Scope change"])
                ],
            },
        ]
    preset = get_preset(purpose)
    diagrams = diagrams[: max(1, preset.min_diagrams)]
    n_tables = min_tables_for_part(purpose, "proposal")
    body["tables"] = tables[:n_tables] if n_tables else []
    return body, diagrams, milestones


def _escape_mermaid(text: str) -> str:
    cleaned = str(text).replace('"', "'").replace("[", "(").replace("]", ")")
    return cleaned[:40] or "Project"


def stub_poc(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
    *,
    purpose: GenerationPurpose = "detailed",
) -> dict[str, Any]:
    features = snapshot.get("features") or []
    ranked = sorted(
        features,
        key=lambda f: (
            0 if "ai" in str(f.get("name", "")).lower() else 1,
            -float(f.get("hours") or 0),
        ),
    )
    selected = ranked[: max(1, min(5, len(ranked)))]
    selected_ids = [str(f["id"]) for f in selected]
    costs = snapshot.get("costs") or {}
    official = price_poc_selection(
        selected_feature_ids=selected_ids,
        features=features,
        role_breakdown=costs.get("role_breakdown") or [],
        gantt=snapshot.get("gantt") or {},
    )
    excluded = [f for f in features if str(f["id"]) not in set(selected_ids)]
    brief = build_project_brief_from_snapshot(snapshot, locale)
    selected_names = [feature_label(f, locale) for f in selected if feature_label(f, locale)]
    excluded_names = [
        feature_label(f, locale) for f in excluded[:10] if feature_label(f, locale)
    ]
    risks = snapshot.get("risks") or []
    modules = snapshot.get("modules") or []
    gantt = snapshot.get("gantt") or {}

    if locale == "ja":
        sections = [
            _section(
                "executive_summary",
                "エグゼクティブサマリー",
                "本概念実証（Proof of Concept）は、見積データに基づき技術的実現可能性を検証するための限定スコープです。本番同等の完成度は目指しません。",
            ),
            _section(
                "problem_statement",
                "課題定義",
                "解決すべき課題は次のとおりです。",
                bullets=risks[:6] or ["前提: 課題が未記入のため、主要業務課題の検証を想定します。"],
            ),
            _section(
                "objectives",
                "目的",
                "限られた期間で技術的実現可能性と価値を確認し、本開発の投資判断材料を得ること。",
            ),
            _section(
                "scope_in",
                "スコープ（対象）",
                "概念実証で検証する作業項目です。",
                bullets=selected_names,
                feature_ids=selected_ids,
            ),
            _section(
                "scope_out",
                "スコープ（対象外）",
                "本開発へ回す項目です。",
                bullets=excluded_names or ["本番運用機能、広域ロールアウト、完全な非機能最適化"],
            ),
            _section(
                "success_criteria",
                "成功基準",
                "成功の判断基準です。",
                bullets=[
                    "主要シナリオがエンドツーエンドで動作すること",
                    "関係者が次工程への判断ができること",
                    "公式見積の工数・費用と検証結果を突き合わせられること",
                ],
            ),
            _section(
                "assumptions",
                "前提条件",
                "情報不足箇所は仮定として明示しています。",
                bullets=[
                    "ステークホルダーが検証期間中にフィードバック可能であること",
                    "対象機能のテストデータが用意できること",
                ],
            ),
            _section(
                "technical_approach",
                "技術アプローチ",
                "既存見積のモジュール構成を踏まえ、高不確実領域を優先して薄く実装し検証します。",
            ),
            _section(
                "proposed_architecture",
                "提案アーキテクチャ",
                "概念実証向けの簡易構成です。下図は検証用の論理構成を示します。",
            ),
            _section(
                "technology_stack",
                "技術スタック",
                "見積モジュールと一般的なエンタープライズ構成に基づく想定です。不足分は仮定です。",
                bullets=modules[:8] or ["前提: 技術スタック未指定のため、Webアプリ＋API＋クラウド基盤を想定"],
            ),
            _section(
                "implementation_plan",
                "実装計画",
                "準備 → コア実装 → 統合検証 → ステークホルダーレビューの順で進めます。",
            ),
            _section(
                "risks_mitigation",
                "リスクと対策",
                "主なリスクと緩和策は表を参照してください。",
            ),
            _section(
                "testing_validation",
                "テスト・検証方針",
                "シナリオ試験、基本的な統合試験、ステークホルダーによる受け入れ確認を実施します。",
            ),
            _section(
                "expected_outcomes",
                "期待成果",
                "実現可能性の判断、残リスクの明確化、本開発スコープの優先順位付け。",
            ),
            _section(
                "timeline_milestones",
                "タイムラインとマイルストーン",
                f"推奨する検証期間の目安は2〜4週間です。見積上の稼働日数は {gantt.get('total_working_days') or '—'} 日です（参考）。",
            ),
            _section(
                "deliverables",
                "成果物",
                "動作デモ、検証結果サマリー、推奨次ステップ、公式費用サマリー。",
                bullets=["デモ環境", "検証レポート", "次工程推奨事項"],
            ),
            _section(
                "recommendations",
                "推奨／次のステップ",
                "検証結果を踏まえ、本開発への移行、スコープ調整、または追加検証を判断してください。",
            ),
        ]
        tables = [
            {
                "id": "tech_stack",
                "title": "技術スタック（想定）",
                "headers": ["領域", "想定技術", "備考"],
                "rows": [
                    ["アプリケーション", "、".join(modules[:3]) or "Web / API", "Assumption を含む場合あり"],
                    ["基盤", "クラウド", "本番同等冗長は対象外"],
                    ["連携", "既存システム API", "検証範囲は選定機能に限定"],
                ],
            },
            {
                "id": "risks",
                "title": "リスクと緩和策",
                "headers": ["リスク", "影響", "緩和策"],
                "rows": [
                    [str(r), "中〜高", "早期プロトタイプで確認"]
                    for r in (risks[:4] or ["技術的不確実性"])
                ],
            },
            {
                "id": "success_matrix",
                "title": "成功基準マトリクス",
                "headers": ["基準", "検証方法", "合格の目安"],
                "rows": [
                    ["主要シナリオの動作", "エンドツーエンド試験", "クリティカルパスが完走"],
                    ["関係者判断", "レビュー会", "次工程の意思決定が可能"],
                    ["費用・工数の突合", "公式見積との比較", "残リスクが説明可能"],
                ],
            },
        ]
        diagrams = [
            {
                "id": "poc_architecture",
                "title": "概念実証アーキテクチャ",
                "engine": "mermaid",
                "source": (
                    "flowchart TD\n"
                    "  U[利用者] --> A[検証用UI]\n"
                    "  A --> B[概念実証API]\n"
                    "  B --> C[選定機能]\n"
                    "  B --> D[モック/簡易連携]\n"
                ),
            },
            {
                "id": "poc_validation_flow",
                "title": "検証フロー",
                "engine": "mermaid",
                "source": (
                    "flowchart TD\n"
                    "  P[準備] --> I[コア実装]\n"
                    "  I --> T[統合試験]\n"
                    "  T --> R[ステークホルダーレビュー]\n"
                    "  R --> D[次工程判断]\n"
                ),
            },
        ]
        milestones = [
            {"id": "kickoff", "name": "キックオフ", "date": gantt.get("project_start_date")},
            {"id": "demo", "name": "中間デモ", "date": None},
            {"id": "review", "name": "ステークホルダーレビュー", "date": None},
        ]
        window = "2〜4週間（目安）"
    else:
        sections = [
            _section(
                "executive_summary",
                "Executive Summary",
                "This Proof of Concept validates technical feasibility for the highest-uncertainty capabilities "
                "drawn from the estimate. It is intentionally limited and is not production-ready delivery.",
            ),
            _section(
                "problem_statement",
                "Problem Statement",
                "The business and delivery problems to validate are:",
                bullets=risks[:6]
                or [
                    "Assumption: business problem was not detailed in the estimate; validating core workflow feasibility."
                ],
            ),
            _section(
                "objectives",
                "Objectives",
                "Confirm technical feasibility and decision-ready evidence within a bounded validation window.",
            ),
            _section(
                "scope_in",
                "Scope — In Scope",
                "Work items selected for Proof of Concept validation.",
                bullets=selected_names,
                feature_ids=selected_ids,
            ),
            _section(
                "scope_out",
                "Scope — Out of Scope",
                "Deferred to full delivery.",
                bullets=excluded_names
                or [
                    "Production hardening, broad rollout, and full non-functional optimization",
                ],
            ),
            _section(
                "success_criteria",
                "Success Criteria",
                "The Proof of Concept succeeds when:",
                bullets=[
                    "Critical scenarios run end-to-end",
                    "Stakeholders can decide whether to proceed",
                    "Official engine effort/cost can be compared with observed feasibility",
                ],
            ),
            _section(
                "assumptions",
                "Assumptions",
                "Gaps in the estimate are treated as explicit assumptions.",
                bullets=[
                    "Stakeholders can provide feedback during the validation window",
                    "Representative test data can be prepared for selected scenarios",
                ],
            ),
            _section(
                "technical_approach",
                "Technical Approach",
                "Prioritize thin vertical slices for high-uncertainty capabilities using the estimate module structure.",
            ),
            _section(
                "proposed_architecture",
                "Proposed Architecture",
                "A simplified logical architecture for validation is shown in the diagram below.",
            ),
            _section(
                "technology_stack",
                "Technology Stack",
                "Derived from estimate modules where available; otherwise stated as assumptions.",
                bullets=modules[:8]
                or [
                    "Assumption: technology stack was not specified; assuming web application, API, and cloud platform."
                ],
            ),
            _section(
                "implementation_plan",
                "Implementation Plan",
                "Prepare environment → implement core slices → integrate → stakeholder review.",
            ),
            _section(
                "risks_mitigation",
                "Risks and Mitigation",
                "Key risks and mitigations are summarized in the table.",
            ),
            _section(
                "testing_validation",
                "Testing & Validation Strategy",
                "Scenario tests, basic integration checks, and stakeholder acceptance review.",
            ),
            _section(
                "expected_outcomes",
                "Expected Outcomes",
                "Feasibility decision, residual risk clarity, and prioritized full-delivery scope.",
            ),
            _section(
                "timeline_milestones",
                "Timeline & Milestones",
                f"Suggested validation window is about two to four weeks. Estimate working days "
                f"(reference): {gantt.get('total_working_days') or '—'}.",
            ),
            _section(
                "deliverables",
                "Deliverables",
                "Working demo, validation summary, recommended next steps, and official cost summary.",
                bullets=["Demo environment", "Validation report", "Go / adjust / stop recommendation"],
            ),
            _section(
                "recommendations",
                "Recommendations / Next Steps",
                "Use validation outcomes to proceed to full delivery, adjust scope, or run a follow-up validation.",
            ),
        ]
        tables = [
            {
                "id": "tech_stack",
                "title": "Technology stack (assumed)",
                "headers": ["Area", "Assumed technology", "Notes"],
                "rows": [
                    [
                        "Application",
                        ", ".join(modules[:3]) or "Web / API",
                        "May include assumptions",
                    ],
                    ["Platform", "Cloud", "Production-grade HA out of scope"],
                    ["Integration", "Existing system APIs", "Limited to selected features"],
                ],
            },
            {
                "id": "risks",
                "title": "Risks and mitigation",
                "headers": ["Risk", "Impact", "Mitigation"],
                "rows": [
                    [str(r), "Medium–High", "Validate early with a thin prototype"]
                    for r in (risks[:4] or ["Technical uncertainty"])
                ],
            },
            {
                "id": "success_matrix",
                "title": "Success criteria matrix",
                "headers": ["Criterion", "How validated", "Pass signal"],
                "rows": [
                    [
                        "Critical scenarios work",
                        "End-to-end scenario tests",
                        "Critical path completes",
                    ],
                    [
                        "Stakeholder decision readiness",
                        "Review workshop",
                        "Clear go / adjust / stop call",
                    ],
                    [
                        "Cost and effort reconciliation",
                        "Compare with official estimate",
                        "Residual risks are explainable",
                    ],
                ],
            },
        ]
        diagrams = [
            {
                "id": "poc_architecture",
                "title": "Proof of Concept architecture",
                "engine": "mermaid",
                "source": (
                    "flowchart TD\n"
                    "  U[Users] --> A[Validation UI]\n"
                    "  A --> B[Proof of Concept API]\n"
                    "  B --> C[Selected capabilities]\n"
                    "  B --> D[Mocked integrations]\n"
                ),
            },
            {
                "id": "poc_validation_flow",
                "title": "Validation flow",
                "engine": "mermaid",
                "source": (
                    "flowchart TD\n"
                    "  P[Prepare] --> I[Implement core slices]\n"
                    "  I --> T[Integration tests]\n"
                    "  T --> R[Stakeholder review]\n"
                    "  R --> D[Next-step decision]\n"
                ),
            },
        ]
        milestones = [
            {"id": "kickoff", "name": "Kickoff", "date": gantt.get("project_start_date")},
            {"id": "demo", "name": "Interim demo", "date": None},
            {"id": "review", "name": "Stakeholder review", "date": None},
        ]
        window = "About two to four weeks (guidance only)"

    preset = get_preset(purpose)
    diagrams = diagrams[: max(1, preset.min_diagrams)]
    n_tables = min_tables_for_part(purpose, "poc")
    tables = tables[:n_tables] if n_tables else []

    return {
        "project_brief": brief,
        "sections": sections,
        "tables": tables,
        "diagrams": diagrams,
        "milestones": milestones,
        "official": official,
        "suggested_validation_window": window,
    }


def build_project_brief_from_snapshot(snapshot: dict[str, Any], locale: Locale) -> dict[str, str]:
    modules = snapshot.get("modules") or []
    funcs = snapshot.get("functional_requirements") or []
    risks = snapshot.get("risks") or []
    gaps = snapshot.get("gaps") or []
    roles = snapshot.get("user_roles") or []
    exclusions = snapshot.get("assumptions") or []
    costs = snapshot.get("costs") or {}
    gantt = snapshot.get("gantt") or {}
    project_name = str(snapshot.get("project_name") or "").strip()

    if locale == "ja":
        def assume(msg: str) -> str:
            return f"前提: {msg}"

        description = (
            f"モジュール: {', '.join(str(m) for m in modules[:8])}。"
            if modules
            else assume("プロジェクト説明が不足しているため、主要モジュールの実現可能性検証を想定します。")
        )
        if funcs:
            description += " 要件例: " + "; ".join(str(x) for x in funcs[:5])
        problem_bits = [str(x) for x in (risks or gaps)[:6]]
        business_problem = (
            "；".join(problem_bits)
            if problem_bits
            else assume("ビジネス課題が未記載のため、主要業務課題の検証を想定します。")
        )
        target_users = (
            "、".join(str(r) for r in roles)
            if roles
            else assume("利用者ロールが未指定のため、管理者と一般利用者を想定します。")
        )
        technology_stack = (
            "、".join(str(m) for m in modules[:10])
            if modules
            else assume("技術スタックが未指定のため、Webアプリ、API、クラウド基盤を想定します。")
        )
        constraint_parts = []
        if costs.get("one_time_project_cost_jpy") is not None:
            constraint_parts.append(f"一次性費用（参考）: {costs.get('one_time_project_cost_jpy')} JPY")
        if gantt.get("total_working_days"):
            constraint_parts.append(f"想定稼働日数（参考）: {gantt.get('total_working_days')}")
        if exclusions:
            constraint_parts.append("除外: " + "、".join(str(x) for x in exclusions[:5]))
        constraints = (
            "；".join(constraint_parts)
            if constraint_parts
            else assume("予算・期限・コンプライアンス制約が未記載のため、限定期間の技術検証を想定します。")
        )
        return {
            "project_name": project_name or assume("プロジェクト名が未設定です。"),
            "project_description": description,
            "business_problem": business_problem,
            "target_users": target_users,
            "technology_stack": technology_stack,
            "constraints": constraints,
        }

    def assume(msg: str) -> str:
        return f"Assumption: {msg}"

    description = (
        f"Modules: {', '.join(str(m) for m in modules[:8])}."
        if modules
        else assume(
            "project description was incomplete; assuming a feasibility validation of core modules."
        )
    )
    if funcs:
        description += " Sample requirements: " + "; ".join(str(x) for x in funcs[:5])
    problem_bits = [str(x) for x in (risks or gaps)[:6]]
    business_problem = (
        "; ".join(problem_bits)
        if problem_bits
        else assume("business problem was not detailed; validating the primary workflow pain points.")
    )
    target_users = (
        ", ".join(str(r) for r in roles)
        if roles
        else assume("target users were not specified; assuming Admin and end users.")
    )
    technology_stack = (
        ", ".join(str(m) for m in modules[:10])
        if modules
        else assume(
            "technology stack was not specified; assuming web application, API services, and a cloud platform."
        )
    )
    constraint_parts = []
    if costs.get("one_time_project_cost_jpy") is not None:
        constraint_parts.append(
            f"One-time project cost (reference): {costs.get('one_time_project_cost_jpy')} JPY"
        )
    if gantt.get("total_working_days"):
        constraint_parts.append(
            f"Estimated working days (reference): {gantt.get('total_working_days')}"
        )
    if exclusions:
        constraint_parts.append("Exclusions: " + ", ".join(str(x) for x in exclusions[:5]))
    constraints = (
        "; ".join(constraint_parts)
        if constraint_parts
        else assume(
            "budget, timeline, and compliance constraints were not listed; assuming a time-boxed technical validation."
        )
    )
    return {
        "project_name": project_name or assume("project name is missing."),
        "project_description": description,
        "business_problem": business_problem,
        "target_users": target_users,
        "technology_stack": technology_stack,
        "constraints": constraints,
    }


async def _purpose_for_stub(part: Literal["assessment", "proposal", "poc"]) -> GenerationPurpose:
    try:
        from app.admin.proposal_ai_config import get_proposal_ai_settings
        from app.database import SessionLocal

        async with SessionLocal() as db:
            settings = await get_proposal_ai_settings(db)
            return purpose_for_part(settings, part)
    except Exception:
        logger.exception("Failed to load proposal AI purpose; using defaults")
        return purpose_for_part(DEFAULT_PROPOSAL_AI_SETTINGS, part)


async def generate_assessment_content(snapshot: dict[str, Any], locale: Locale) -> dict[str, Any]:
    """Generate assessment via AI when available; fall back to stub on failure."""
    try:
        from app.proposals import ai_client

        if hasattr(ai_client, "generate_assessment"):
            result = await ai_client.generate_assessment(snapshot, locale)
            if result:
                return result
    except Exception:
        logger.exception("Proposal assessment AI failed; using stub")
    return stub_assessment(snapshot, locale)


async def generate_proposal_content(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        from app.proposals import ai_client

        if hasattr(ai_client, "generate_proposal"):
            result = await ai_client.generate_proposal(snapshot, assessment, locale)
            if result:
                return result
    except Exception:
        logger.exception("Proposal body AI failed; using stub")
    purpose = await _purpose_for_stub("proposal")
    return stub_proposal_body(snapshot, assessment, locale, purpose=purpose)


async def generate_poc_content(
    snapshot: dict[str, Any],
    assessment: dict[str, Any],
    locale: Locale,
) -> dict[str, Any]:
    try:
        from app.proposals import ai_client

        if hasattr(ai_client, "generate_poc"):
            result = await ai_client.generate_poc(snapshot, assessment, locale)
            if result:
                # Re-price with engine regardless of AI narrative
                feature_ids = []
                for section in result.get("sections") or []:
                    if section.get("id") in {"scope_in", "in_scope"}:
                        feature_ids = list(section.get("feature_ids") or [])
                        break
                if not feature_ids:
                    feature_ids = list((result.get("official") or {}).get("selected_feature_ids") or [])
                costs = snapshot.get("costs") or {}
                result["official"] = price_poc_selection(
                    selected_feature_ids=feature_ids,
                    features=snapshot.get("features") or [],
                    role_breakdown=costs.get("role_breakdown") or [],
                    gantt=snapshot.get("gantt") or {},
                )
                if not result.get("project_brief"):
                    result["project_brief"] = build_project_brief_from_snapshot(snapshot, locale)
                return result
    except Exception:
        logger.exception("Proposal POC AI failed; using stub")
    purpose = await _purpose_for_stub("poc")
    return stub_poc(snapshot, assessment, locale, purpose=purpose)


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
