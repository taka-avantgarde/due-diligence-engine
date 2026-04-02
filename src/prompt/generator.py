"""IDE AI向け構造化プロンプト生成モジュール。

DDE のヒューリスティック分析結果を、IDE 内 AI（Claude Code, Cursor 等）が
理解・評価できる構造化プロンプトとして出力する。

特徴:
- 非IT業界の利用者向けに全技術用語に注釈を付与（ほんやくコンニャク方式）
- 6次元スコアリング + ステータスバー表示 (100点満点)
- 強み・弱みの詳細分析と「何ができるようになるか」の事例説明
- 「こうすればもっと良くなる」改善提案
- サービスサイトURL貼り付けによる主張vs実態の乖離分析を促進
- マッチ率（主張と実装の一致度）表示
- 投資家向け質問リストの自動生成
"""

from __future__ import annotations

import json
from typing import Any

from src.models import AnalysisResult, RedFlag


# ---------------------------------------------------------------------------
# 用語集（Glossary）: IT業界外の読者向け
# ---------------------------------------------------------------------------

GLOSSARY_EN = {
    "API wrapper ratio": (
        "The percentage of code that merely calls external services (e.g. OpenAI, AWS) "
        "rather than implementing its own logic. A high ratio means the product has "
        "little original technology — like a restaurant that only reheats frozen meals."
    ),
    "CI/CD": (
        "Continuous Integration / Continuous Delivery — an automated system that tests "
        "and deploys code every time a developer makes a change. Think of it as a "
        "factory's quality control line. Without CI/CD, quality depends entirely on "
        "manual checks."
    ),
    "Rush commits": (
        "A burst of 20+ code changes within 24 hours. This may indicate deadline panic, "
        "but in AI-assisted development (Claude Code, Cursor) it's normal — like a chef "
        "using a food processor instead of chopping by hand."
    ),
    "Dependency count": (
        "The number of external software libraries the project relies on. Like ingredients "
        "in a recipe — more ingredients mean more things that could go wrong, but also "
        "richer functionality."
    ),
    "Consistency score": (
        "How well the project's documentation claims match the actual code. Like comparing "
        "a restaurant's menu description with what actually arrives on your plate."
    ),
    "Red flag": (
        "A warning sign found during analysis. Like a health inspector's report — ranges from "
        "INFO (minor note) to CRITICAL (potential deal-breaker)."
    ),
    "Git forensics": (
        "Analysis of the project's version control history — who wrote what, when, "
        "and how often. Like reviewing a building's construction log to see "
        "if it was built carefully or rushed."
    ),
    "Test coverage": (
        "The percentage of code that has automated tests. Like a car manufacturer "
        "testing each component — higher coverage means fewer hidden defects."
    ),
    "Monorepo": (
        "A single code repository containing multiple projects (e.g. frontend + backend + "
        "mobile app). Like a department store vs. separate shops — dependency counts "
        "are naturally higher."
    ),
    "Technical debt": (
        "Shortcuts taken during development that will need to be fixed later. Like "
        "building a house quickly with temporary materials — it works now, but "
        "maintenance costs increase over time."
    ),
    "E2EE": (
        "End-to-End Encryption — messages encrypted on the sender's device, "
        "decryptable only by the recipient. Even the service provider cannot read them. "
        "Like sending a letter in a lockbox that only the recipient has the key to."
    ),
}

GLOSSARY_JA = {
    "APIラッパー比率": (
        "外部サービス（OpenAI、AWS等）を呼び出すだけのコードの割合。"
        "たとえるなら「冷凍食品を温めて出すだけのレストラン」のようなもの。"
        "高いほど独自技術がなく、他社のサービスに完全に依存しています。"
    ),
    "CI/CD": (
        "継続的インテグレーション/継続的デリバリー。開発者がコードを変更するたびに"
        "自動でテスト・デプロイする仕組み。工場の品質検査ラインのようなもの。"
        "これがないと品質チェックが人手頼みで、不良品が出荷されるリスクがあります。"
    ),
    "ラッシュコミット": (
        "24時間以内に20件以上のコード変更が集中すること。"
        "手作業なら「締め切り前の徹夜」を疑いますが、AI開発ツール（Claude Code等）を"
        "使えばフードプロセッサーで調理するように高速開発は普通です。"
    ),
    "依存パッケージ数": (
        "プロジェクトが利用している外部ライブラリの数。料理のレシピの材料数のようなもの。"
        "多いほど機能は豊富ですが、どれか一つに問題が起きると全体に影響します。"
    ),
    "整合性スコア": (
        "ドキュメントの主張と実際のコードがどれだけ一致しているか（0〜100%）。"
        "レストランのメニュー写真と実際に出てくる料理がどれだけ一致するか、のようなもの。"
    ),
    "レッドフラグ": (
        "分析中に発見された警告サイン。保健所の検査レポートのようなもの。"
        "INFO（軽微な注意点）からCRITICAL（投資判断を左右する重大な問題）まで5段階。"
    ),
    "Gitフォレンジック": (
        "バージョン管理の履歴分析。建物の施工記録を確認するようなもの。"
        "丁寧に建てたのか、急いで建てたのかが分かります。"
    ),
    "テストカバレッジ": (
        "自動テストでカバーされているコードの割合。自動車メーカーの部品検査のようなもの。"
        "高いほど隠れた欠陥が少なく、信頼性が高いことを示します。"
    ),
    "モノレポ": (
        "フロントエンド＋バックエンド＋モバイルアプリ等を1つのリポジトリで管理する構成。"
        "百貨店（1棟に全テナント）と専門店（別々の建物）の違い。"
        "依存パッケージ数が多いのは構造上の特性です。"
    ),
    "技術的負債": (
        "開発を急ぐために取ったショートカットの蓄積。仮設材料で急いで建てた家のようなもの。"
        "今は動きますが、時間が経つほど修繕コストが膨らみます。"
    ),
    "E2EE": (
        "エンドツーエンド暗号化。送信者の端末で暗号化し、受信者だけが解読できる方式。"
        "受取人だけが鍵を持つ金庫で手紙を送るようなもの。"
        "サービス運営者でさえ中身を読めません。"
    ),
    "マッチ率": (
        "サービスサイトやドキュメントの主張が、実際のソースコードでどれだけ実現されているかの割合。"
        "100%なら「言っていることが全て実装されている」、0%なら「口だけで実態がない」ことを意味します。"
    ),
}


# ---------------------------------------------------------------------------
# 評価基準定義
# ---------------------------------------------------------------------------

DIMENSIONS_EN = [
    {
        "name": "Technical Originality",
        "weight": "25%",
        "what": "How much of the code is genuinely original vs. calling external APIs",
        "levels": "Lv.1 (Copy) → Lv.5 (Extended) → Lv.10 (Frontier/paradigm-shifting)",
        "analogy": "A chef creating original recipes vs. reheating frozen meals",
    },
    {
        "name": "Technology Advancement",
        "weight": "20%",
        "what": "How modern and forward-looking the technology choices are",
        "levels": "Lv.1 (Legacy/10yr old) → Lv.5 (Current standard) → Lv.10 (5yr ahead)",
        "analogy": "Driving a classic car vs. industry standard vs. prototype electric vehicle",
    },
    {
        "name": "Implementation Depth",
        "weight": "20%",
        "what": "Is this a prototype or production-ready software?",
        "levels": "Lv.1 (UI mockup) → Lv.5 (Beta with tests) → Lv.10 (Mission-critical grade)",
        "analogy": "A concept car vs. a test model vs. an FDA-approved medical device",
    },
    {
        "name": "Architecture Quality",
        "weight": "15%",
        "what": "How well-organized and maintainable the codebase is",
        "levels": "Lv.1 (Spaghetti code) → Lv.5 (Clean separation) → Lv.10 (Distributed/scalable)",
        "analogy": "A cluttered desk vs. an organized office vs. a smart building",
    },
    {
        "name": "Claim Consistency",
        "weight": "10%",
        "what": "Do the team's documentation claims match the actual code?",
        "levels": "Lv.1 (Fabricated claims) → Lv.5 (50% verifiable) → Lv.10 (Fully transparent)",
        "analogy": "A menu photo vs. the actual dish — how close is the match?",
    },
    {
        "name": "Security Posture",
        "weight": "10%",
        "what": "How seriously the team treats security and data protection",
        "levels": "Lv.1 (Negligent) → Lv.5 (Industry standard) → Lv.10 (Military-grade)",
        "analogy": "An unlocked door vs. a keycard system vs. a bank vault",
    },
]

DIMENSIONS_JA = [
    {
        "name": "技術独自性 (Technical Originality)",
        "weight": "25%",
        "what": "コードがどの程度オリジナルか。外部APIを呼ぶだけか、独自ロジックがあるか",
        "levels": "Lv.1（コピー）→ Lv.5（拡張あり）→ Lv.10（パラダイム転換級）",
        "analogy": "冷凍食品を温めるだけの店 vs. オリジナルレシピの名店",
    },
    {
        "name": "技術先進性 (Technology Advancement)",
        "weight": "20%",
        "what": "技術選定がどの程度先進的か",
        "levels": "Lv.1（10年前の技術）→ Lv.5（業界標準）→ Lv.10（5年先を行く）",
        "analogy": "クラシックカー vs. 最新の量産車 vs. プロトタイプEV",
    },
    {
        "name": "実装深度 (Implementation Depth)",
        "weight": "20%",
        "what": "プロトタイプか、本番運用レベルか",
        "levels": "Lv.1（UIモックのみ）→ Lv.5（テスト付きベータ）→ Lv.10（ミッションクリティカル級）",
        "analogy": "コンセプトカー vs. テスト車両 vs. FDA認可の医療機器",
    },
    {
        "name": "設計品質 (Architecture Quality)",
        "weight": "15%",
        "what": "コードの整理度・保守性・拡張しやすさ",
        "levels": "Lv.1（スパゲッティ）→ Lv.5（責務分離済）→ Lv.10（分散・スケーラブル）",
        "analogy": "書類が散らかった机 vs. 整理されたオフィス vs. スマートビル",
    },
    {
        "name": "主張整合性 (Claim Consistency)",
        "weight": "10%",
        "what": "ドキュメントやWebサイトの主張が、実際のコードと一致しているか",
        "levels": "Lv.1（虚偽）→ Lv.5（50%検証可）→ Lv.10（完全透明）",
        "analogy": "メニュー写真と実際の料理 — どれだけ一致するか",
    },
    {
        "name": "セキュリティ態勢 (Security Posture)",
        "weight": "10%",
        "what": "セキュリティとデータ保護にどの程度真剣に取り組んでいるか",
        "levels": "Lv.1（無防備）→ Lv.5（業界標準）→ Lv.10（軍事レベル）",
        "analogy": "鍵のかかっていないドア vs. カードキーシステム vs. 銀行の金庫室",
    },
]


# ---------------------------------------------------------------------------
# メイン生成関数
# ---------------------------------------------------------------------------

def generate_prompt(
    result: AnalysisResult,
    lang: str = "en",
    stage: str = "unknown",
) -> str:
    """IDE AI向けの構造化プロンプトを生成する。

    Args:
        result: DDE ヒューリスティック分析結果。
        lang: 出力言語 ("en" or "ja")。
        stage: スタートアップのステージ ("seed", "series_a", "series_b", "growth", "unknown")。

    Returns:
        IDE AI にそのまま渡せる構造化プロンプト文字列。
    """
    if lang == "ja":
        return _generate_ja(result, stage)
    return _generate_en(result, stage)


def _generate_en(result: AnalysisResult, stage: str) -> str:
    """English prompt generation."""
    sections: list[str] = []

    sections.append(_HEADER_EN)
    sections.append("## Glossary (for non-technical readers)\n")
    for term, definition in GLOSSARY_EN.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## Heuristic Analysis Results (automated, no AI used)\n")
    sections.append(_format_heuristic_en(result))

    sections.append("## Match Rate: Claims vs. Reality\n")
    sections.append(_format_match_rate_en(result))

    sections.append("## Red Flags Detected\n")
    sections.append(_format_red_flags_en(result))

    sections.append("## Scoring Framework (6 dimensions, 10-level scale)\n")
    sections.append(
        "Evaluate each dimension on a 1-10 scale, then convert to 0-100 points.\n"
        "Final score = weighted average of all dimensions.\n"
    )
    for dim in DIMENSIONS_EN:
        sections.append(
            f"### {dim['name']} (Weight: {dim['weight']})\n"
            f"**What to evaluate**: {dim['what']}\n"
            f"**Scale**: {dim['levels']}\n"
            f"**In plain terms**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_en(stage))
    sections.append(_EVAL_INSTRUCTIONS_EN)
    sections.append(_SITE_ANALYSIS_PROMPT_EN)
    sections.append(_QUESTION_INSTRUCTIONS_EN)

    return "\n".join(sections)


def _generate_ja(result: AnalysisResult, stage: str) -> str:
    """Japanese prompt generation."""
    sections: list[str] = []

    sections.append(_HEADER_JA)
    sections.append("## 用語集（IT業界外の方向け — ほんやくコンニャク）\n")
    for term, definition in GLOSSARY_JA.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## ヒューリスティック分析結果（自動分析・AI不使用）\n")
    sections.append(_format_heuristic_ja(result))

    sections.append("## マッチ率: 主張 vs 実態\n")
    sections.append(_format_match_rate_ja(result))

    sections.append("## 検出されたレッドフラグ（警告サイン）\n")
    sections.append(_format_red_flags_ja(result))

    sections.append("## スコアリング基準（6次元 × 10段階評価）\n")
    sections.append(
        "各次元を1〜10で評価し、100点満点に変換してください。\n"
        "最終スコア = 全次元の加重平均です。\n"
    )
    for dim in DIMENSIONS_JA:
        sections.append(
            f"### {dim['name']}（重み: {dim['weight']}）\n"
            f"**評価観点**: {dim['what']}\n"
            f"**尺度**: {dim['levels']}\n"
            f"**たとえるなら**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_ja(stage))
    sections.append(_EVAL_INSTRUCTIONS_JA)
    sections.append(_SITE_ANALYSIS_PROMPT_JA)
    sections.append(_QUESTION_INSTRUCTIONS_JA)

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Match Rate（主張 vs 実態の一致度）
# ---------------------------------------------------------------------------

def _format_match_rate_en(result: AnalysisResult) -> str:
    consistency = result.consistency
    total_claims = len(consistency.verified_claims) + len(consistency.unverified_claims)
    if total_claims == 0:
        return "No claims found in documentation to verify.\n"

    match_rate = len(consistency.verified_claims) / total_claims * 100
    bar = _make_bar(match_rate)

    lines = [
        f"**Overall Match Rate**: {match_rate:.0f}%",
        f"```",
        f"Claims vs Code: {bar} {match_rate:.0f}%",
        f"```",
        f"",
        f"| Category | Count | Meaning |",
        f"|----------|-------|---------|",
        f"| ✅ Verified | {len(consistency.verified_claims)} | Claims confirmed by actual code — \"they do what they say\" |",
        f"| ❓ Unverified | {len(consistency.unverified_claims)} | Claims not found in code — could be future plans, or overstatement |",
        f"| ❌ Contradictions | {len(consistency.contradictions)} | Claims that directly conflict with code — potential deception |",
        f"",
        f"**What this means**: A match rate above 70% suggests the team is honest about their capabilities. "
        f"Below 50% is a warning sign — the team may be overpromising. "
        f"Contradictions are the most serious: they suggest the team knows the truth but says otherwise.",
        f"",
    ]
    return "\n".join(lines)


def _format_match_rate_ja(result: AnalysisResult) -> str:
    consistency = result.consistency
    total_claims = len(consistency.verified_claims) + len(consistency.unverified_claims)
    if total_claims == 0:
        return "ドキュメントに検証可能な主張が見つかりませんでした。\n"

    match_rate = len(consistency.verified_claims) / total_claims * 100
    bar = _make_bar(match_rate)

    lines = [
        f"**全体マッチ率**: {match_rate:.0f}%",
        f"```",
        f"主張 vs コード: {bar} {match_rate:.0f}%",
        f"```",
        f"",
        f"| 区分 | 件数 | 意味 |",
        f"|------|------|------|",
        f"| ✅ 検証済み | {len(consistency.verified_claims)} | 実際のコードで確認できた主張 — 「言った通りのことを実装している」 |",
        f"| ❓ 未検証 | {len(consistency.unverified_claims)} | コード内に証拠が見つからない — 将来の計画か、過大な主張の可能性 |",
        f"| ❌ 矛盾 | {len(consistency.contradictions)} | コードと矛盾する主張 — 事実と異なることを述べている可能性 |",
        f"",
        f"**見方**: マッチ率70%以上ならチームは技術力について誠実と判断できます。",
        f"50%未満は要注意 — 実力以上のことを主張している可能性があります。",
        f"矛盾が最も深刻で、「事実を知っていながら異なる説明をしている」ことを示唆します。",
        f"",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Heuristic formatting
# ---------------------------------------------------------------------------

def _format_heuristic_en(result: AnalysisResult) -> str:
    code = result.code_analysis
    git = result.git_forensics
    consistency = result.consistency
    doc = result.doc_analysis

    lines = [
        "### Code Analysis\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total files | {code.total_files:,} | Number of source code files in the project |",
        f"| Total lines | {code.total_lines:,} | Lines of code (larger = more substantial product) |",
        f"| Languages | {_format_langs(code.languages)} | Programming languages used |",
        f"| API wrapper ratio | {code.api_wrapper_ratio:.1%} | % of code that just calls external services (lower = more original) |",
        f"| Has tests | {'Yes ✓' if code.has_tests else 'No ✗'} | Whether automated quality checks exist |",
        f"| Has CI/CD | {'Yes ✓' if code.has_ci_cd else 'No ✗'} | Whether automated build/deploy pipeline exists |",
        f"| Has documentation | {'Yes ✓' if code.has_documentation else 'No ✗'} | Whether technical docs exist |",
        f"| Dependency count | {code.dependency_count} | Number of external libraries used |",
        "",
        "### Git History Analysis (reading the development story)\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total commits | {git.total_commits:,} | Number of code changes recorded (the project's diary) |",
        f"| Unique authors | {git.unique_authors} | Number of developers who contributed |",
        f"| First commit | {git.first_commit_date or 'N/A'} | When development started |",
        f"| Last commit | {git.last_commit_date or 'N/A'} | Most recent activity |",
        f"| Rush commit ratio | {git.rush_commit_ratio:.1%} | % of commits in high-activity bursts |",
        "",
        "### Document & Claim Analysis\n",
        f"| Metric | Value | What this means |",
        f"|--------|-------|-----------------|",
        f"| Total claims found | {len(doc.claims)} | Statements about technology/performance in docs |",
        f"| Performance claims | {len(doc.performance_claims)} | Claims about speed, scale, uptime |",
        f"| Architecture claims | {len(doc.architecture_claims)} | Claims about system design, patents |",
        f"| Verified claims | {len(consistency.verified_claims)} | Claims confirmed by actual code |",
        f"| Unverified claims | {len(consistency.unverified_claims)} | Claims not found in code |",
        f"| Contradictions | {len(consistency.contradictions)} | Claims that conflict with code |",
        f"| Consistency score | {consistency.consistency_score:.1f}% | Overall match between claims and code |",
        "",
    ]
    return "\n".join(lines)


def _format_heuristic_ja(result: AnalysisResult) -> str:
    code = result.code_analysis
    git = result.git_forensics
    consistency = result.consistency
    doc = result.doc_analysis

    lines = [
        "### コード分析\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 総ファイル数 | {code.total_files:,} | プロジェクト内のソースコードファイル数 |",
        f"| 総行数 | {code.total_lines:,} | 書かれたコードの行数（多いほど実質的な製品） |",
        f"| 使用言語 | {_format_langs(code.languages)} | 使用されているプログラミング言語 |",
        f"| APIラッパー比率 | {code.api_wrapper_ratio:.1%} | 外部サービスを呼ぶだけのコードの割合（低いほど独自性が高い） |",
        f"| テスト有無 | {'あり ✓' if code.has_tests else 'なし ✗'} | 自動品質チェックが存在するか |",
        f"| CI/CD有無 | {'あり ✓' if code.has_ci_cd else 'なし ✗'} | 自動ビルド・デプロイの仕組みがあるか |",
        f"| ドキュメント有無 | {'あり ✓' if code.has_documentation else 'なし ✗'} | 技術文書が存在するか |",
        f"| 依存パッケージ数 | {code.dependency_count} | 外部ライブラリの数 |",
        "",
        "### Git履歴分析（開発の歩みを読み解く）\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 総コミット数 | {git.total_commits:,} | 記録されたコード変更の回数（プロジェクトの日記帳） |",
        f"| 開発者数 | {git.unique_authors} | コードに貢献した人数 |",
        f"| 開発開始日 | {git.first_commit_date or 'N/A'} | 最初のコード変更日 |",
        f"| 最終更新日 | {git.last_commit_date or 'N/A'} | 最新の活動日 |",
        f"| ラッシュコミット率 | {git.rush_commit_ratio:.1%} | 短時間に集中したコード変更の割合 |",
        "",
        "### ドキュメント・主張分析\n",
        f"| 指標 | 値 | 意味 |",
        f"|------|-----|------|",
        f"| 検出された主張数 | {len(doc.claims)} | 技術力やパフォーマンスに関する記述の数 |",
        f"| 性能に関する主張 | {len(doc.performance_claims)} | 速度・規模・稼働率に関する主張 |",
        f"| 設計に関する主張 | {len(doc.architecture_claims)} | システム設計・特許に関する主張 |",
        f"| 検証済み主張 | {len(consistency.verified_claims)} | 実際のコードで確認できた主張 |",
        f"| 未検証主張 | {len(consistency.unverified_claims)} | コード内に証拠が見つからない主張 |",
        f"| 矛盾 | {len(consistency.contradictions)} | コードと矛盾する主張 |",
        f"| 整合性スコア | {consistency.consistency_score:.1f}% | 主張とコードの全体的な一致度 |",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Red flag formatting
# ---------------------------------------------------------------------------

def _format_red_flags_en(result: AnalysisResult) -> str:
    all_flags = _collect_flags(result)
    if not all_flags:
        return "No red flags detected.\n"

    lines: list[str] = []
    severity_labels = {
        "critical": "🔴 CRITICAL (potential deal-breaker — like finding structural damage in a building)",
        "high": "🟠 HIGH (significant concern — like a restaurant failing a hygiene inspection)",
        "medium": "🟡 MEDIUM (worth investigating — like an unusual item on a financial statement)",
        "low": "🔵 LOW (minor note — like a cosmetic scratch on a car)",
        "info": "ℹ️  INFO (for reference only)",
    }

    for severity in ["critical", "high", "medium", "low", "info"]:
        flags = [f for f in all_flags if f.severity.value == severity]
        if flags:
            lines.append(f"### {severity_labels[severity]}\n")
            for flag in flags:
                lines.append(f"- **{flag.title}**: {flag.description}")
            lines.append("")

    return "\n".join(lines)


def _format_red_flags_ja(result: AnalysisResult) -> str:
    all_flags = _collect_flags(result)
    if not all_flags:
        return "レッドフラグは検出されませんでした。\n"

    lines: list[str] = []
    severity_labels = {
        "critical": "🔴 CRITICAL — 投資判断を左右する重大な問題（建物の構造欠陥のようなもの）",
        "high": "🟠 HIGH — 要注意（衛生検査に不合格のレストランのようなもの）",
        "medium": "🟡 MEDIUM — 追加調査推奨（決算書の不自然な項目のようなもの）",
        "low": "🔵 LOW — 軽微な注意点（車の小さな傷のようなもの）",
        "info": "ℹ️  INFO — 参考情報",
    }

    for severity in ["critical", "high", "medium", "low", "info"]:
        flags = [f for f in all_flags if f.severity.value == severity]
        if flags:
            lines.append(f"### {severity_labels[severity]}\n")
            for flag in flags:
                lines.append(f"- **{flag.title}**: {flag.description}")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage context
# ---------------------------------------------------------------------------

def _get_stage_context_en(stage: str) -> str:
    contexts = {
        "seed": (
            "## Stage Context: Seed\n\n"
            "At the seed stage, expect:\n"
            "- Smaller codebases (1K-10K lines is normal)\n"
            "- 1-3 developers\n"
            "- Limited or no CI/CD (acceptable at this stage)\n"
            "- Focus on: Does the core idea work? Is there genuine technical capability?\n"
            "- Red flags: API-only wrappers, no original code, fabricated claims\n"
        ),
        "series_a": (
            "## Stage Context: Series A\n\n"
            "At Series A, expect:\n"
            "- Medium codebases (10K-100K lines)\n"
            "- 3-10 developers\n"
            "- Basic CI/CD and tests should exist\n"
            "- Focus on: Is the architecture scalable? Is the team growing effectively?\n"
            "- Red flags: No tests, no CI/CD, single-developer dependency\n"
        ),
        "series_b": (
            "## Stage Context: Series B\n\n"
            "At Series B, expect:\n"
            "- Large codebases (100K+ lines)\n"
            "- 10+ developers with comprehensive CI/CD and testing\n"
            "- Focus on: Scalability, security, technical debt management\n"
            "- Red flags: Poor security, no monitoring, high tech debt\n"
        ),
        "growth": (
            "## Stage Context: Growth/Late Stage\n\n"
            "At growth stage, expect:\n"
            "- Very large codebases (500K+ lines) with 30+ developers\n"
            "- Enterprise-grade CI/CD, security, and compliance\n"
            "- Focus on: Operational excellence, compliance, disaster recovery\n"
            "- Red flags: Compliance gaps, scalability bottlenecks\n"
        ),
    }
    return contexts.get(stage, (
        "## Stage Context\n\n"
        "The startup's development stage was not specified. "
        "When evaluating, consider whether the findings are appropriate "
        "for the company's current phase (seed → Series A → Series B → growth).\n"
    ))


def _get_stage_context_ja(stage: str) -> str:
    contexts = {
        "seed": (
            "## ステージ別の判断基準: シード期\n\n"
            "シード期では以下が一般的です:\n"
            "- コード規模: 1,000〜10,000行程度\n"
            "- 開発者: 1〜3名\n"
            "- CI/CDやテストは未整備でも許容範囲\n"
            "- 重要な評価ポイント: コアのアイデアは動くか？ 本物の技術力があるか？\n"
            "- この段階でのレッドフラグ: API呼び出しだけ、独自コードなし、虚偽の主張\n"
        ),
        "series_a": (
            "## ステージ別の判断基準: シリーズA\n\n"
            "シリーズAでは以下が期待されます:\n"
            "- コード規模: 10,000〜100,000行\n"
            "- 開発者: 3〜10名\n"
            "- 基本的なCI/CDとテストが存在すべき\n"
            "- 重要な評価ポイント: 設計は拡張可能か？ チームは成長しているか？\n"
            "- この段階でのレッドフラグ: テストなし、CI/CDなし、一人依存\n"
        ),
        "series_b": (
            "## ステージ別の判断基準: シリーズB\n\n"
            "シリーズBでは以下が期待されます:\n"
            "- コード規模: 100,000行以上\n"
            "- 開発者: 10名以上。包括的なCI/CD・テストが必須\n"
            "- 重要な評価ポイント: スケーラビリティ、セキュリティ、技術的負債の管理\n"
            "- この段階でのレッドフラグ: セキュリティ不備、監視なし、技術的負債過大\n"
        ),
        "growth": (
            "## ステージ別の判断基準: グロース/レイト\n\n"
            "グロース段階では以下が期待されます:\n"
            "- コード規模: 500,000行以上、開発者30名以上\n"
            "- エンタープライズ級のCI/CD、セキュリティ、コンプライアンス\n"
            "- 重要な評価ポイント: 運用の卓越性、コンプライアンス、災害復旧\n"
            "- この段階でのレッドフラグ: コンプライアンス不備、スケーラビリティの壁\n"
        ),
    }
    return contexts.get(stage, (
        "## ステージ別の判断基準\n\n"
        "スタートアップの開発ステージが指定されていません。\n"
        "評価時は、発見事項がそのステージ（シード → シリーズA → シリーズB → グロース）\n"
        "に対して適切かどうかを考慮してください。\n"
    ))


# ---------------------------------------------------------------------------
# Header / Instructions templates
# ---------------------------------------------------------------------------

_HEADER_EN = """# DDE Technical Due Diligence — AI Evaluation Prompt

> **How to use**: This prompt was generated by [DDE (Due Diligence Engine)](https://github.com/taka-avantgarde/Due-diligence-engine).
> Paste this entire output into your AI terminal (Claude Code, Cursor, GitHub Copilot, etc.)
> and the AI will evaluate the project using the data below.
>
> **No API keys required** — your IDE's AI subscription handles the analysis cost.
>
> **For non-technical readers**: A glossary of technical terms is included below.
> All metrics include plain-language explanations. Think of this as a "translation device"
> that converts engineering jargon into business language.
"""

_HEADER_JA = """# DDE テクニカルデューデリジェンス — AI評価プロンプト

> **使い方**: このプロンプトは [DDE (Due Diligence Engine)](https://github.com/taka-avantgarde/Due-diligence-engine) が自動生成しました。
> この出力全体を AI ターミナル（Claude Code, Cursor, GitHub Copilot 等）に貼り付けると、
> AI がデータを読み取って評価レポートを作成します。
>
> **APIキー不要** — お使いのIDEのAIサブスクリプションで分析できます。
>
> **IT業界以外の方へ**: 下記に「ほんやくコンニャク」（用語集）を掲載しています。
> エンジニア用語をビジネス言語に翻訳し、各指標の「意味」列で平易に説明しています。
"""

_EVAL_INSTRUCTIONS_EN = """## Your Evaluation Task

Based on the heuristic data above, perform the following:

1. **Read all code in the repository** to verify and supplement the heuristic findings
2. **Score each of the 6 dimensions** on a 1-10 scale with evidence and plain-language explanation
3. **Calculate the final score**: Each level × 10 = points (0-100), then weighted average
4. **Assign a grade**: A (90+), B (75+), C (60+), D (40+), F (<40)
5. **Re-evaluate red flags**: The heuristic analysis may have false positives
   - Rush commits from AI-assisted development are normal, not suspicious
   - Technical terms (E2EE, Signal Protocol) are not "buzzwords" if actually implemented
   - High dependency counts in monorepos are structural, not a risk
6. **Identify strengths**: What this technology enables — give concrete examples
   - "Because this feature exists, users can do X"
   - "This architecture allows the system to handle Y"
7. **Identify weaknesses**: What could go wrong and why it matters
8. **Recommend improvements**: "If you do X, you could also achieve Y"
9. **Generate investor questions**: Plain language questions for non-technical investors

### Output Format

Use status bars for visual scoring (copy this format exactly):

```
## DDE AI Evaluation Report: {Project Name}

### Overall Score
██████████████████░░░░░░░░░░░░░░ 87/100 (Grade: B)

### Dimension Scores (status bar + plain language)

Technical Originality (25%)
████████████████████████████░░░░ 92/100 — Lv.9 Original
→ In plain terms: [explanation of what this means for a non-engineer]
→ This enables: [what the user/business can do because of this]

Technology Advancement (20%)
██████████████████████████░░░░░░ 88/100 — Lv.9 Leading-Edge
→ In plain terms: [explanation]
→ This enables: [capability]

[...repeat for all 6 dimensions...]

### Strengths — What This Technology Makes Possible
1. [Strength] → "Because of this, [concrete capability/benefit]"
2. ...

### Weaknesses — What Could Go Wrong
1. [Weakness] → "This matters because [real-world impact]"
2. ...

### Red Flag Re-evaluation
| Heuristic Flag | AI Assessment | Verdict |
|----------------|---------------|---------|

### Match Rate: Claims vs Reality
Claims Match: ██████████████████████░░░░░░░░░░ 72%
→ [plain language explanation]

### How to Improve — "If you do X, Y becomes possible"
1. [Improvement] → "This would enable [new capability]"
2. ...

### Questions for the Startup Team
1. ...
```
"""

_EVAL_INSTRUCTIONS_JA = """## あなたへの評価タスク

上記のヒューリスティックデータに基づいて、以下を実行してください:

1. **リポジトリ内の全コードを読み**、ヒューリスティック結果を検証・補足
2. **6次元それぞれを1〜10で評価**（根拠＋平易な日本語での説明を添えて）
3. **最終スコアを計算**: 各レベル × 10 = ポイント（0〜100）→ 加重平均
4. **グレードを付与**: A（90以上）、B（75以上）、C（60以上）、D（40以上）、F（40未満）
5. **レッドフラグの再評価**: ヒューリスティック分析には誤検知がありえます
   - AI駆動開発によるラッシュコミットは正常（不審ではない）
   - E2EEやSignal Protocol等は実装済みなら「バズワード」ではない
   - モノレポの依存数が多いのは構造的特性（リスクではない）
6. **強みの分析**: この技術で何が可能になるか — 具体例を挙げて
   - 「この機能があるおかげで、ユーザーは○○ができます」
   - 「このアーキテクチャにより、△△が可能になっています」
7. **弱みの分析**: 何が起こりうるか、なぜ問題か
8. **改善提案**: 「○○すれば、さらに△△もできるようになるかもしれません」
9. **投資家向け質問**: 非技術者でも聞ける平易な表現で

### 出力フォーマット

ステータスバーでスコアを視覚的に表示してください:

```
## DDE AI評価レポート: {プロジェクト名}

### 総合スコア
██████████████████░░░░░░░░░░░░░░ 87/100（グレード: B）

### 次元別スコア（ステータスバー＋平易な解説）

技術独自性（25%）
████████████████████████████░░░░ 92/100 — Lv.9 オリジナル
→ わかりやすく言うと: [エンジニア以外にもわかる説明]
→ この技術のおかげで: [何ができるようになっているか]

技術先進性（20%）
██████████████████████████░░░░░░ 88/100 — Lv.9 先端的
→ わかりやすく言うと: [説明]
→ この技術のおかげで: [できること]

[...6次元すべて繰り返し...]

### 強み — この技術で何ができるようになっているか
1. [強み] → 「これがあるおかげで、[具体的にできること・事例]」
2. ...

### 弱み — 何が起こりうるか
1. [弱み] → 「なぜ問題かというと、[実際の影響]」
2. ...

### レッドフラグ再評価
| ヒューリスティックの指摘 | AI評価 | 判定 |
|--------------------------|--------|------|

### マッチ率: 主張 vs 実態
主張の一致度: ██████████████████████░░░░░░░░░░ 72%
→ [平易な解説]

### こうすればもっと良くなる — 「○○すれば△△も可能に」
1. [改善策] → 「これにより、[新たに可能になること]」
2. ...

### スタートアップチームへの質問
1. ...
```
"""

_SITE_ANALYSIS_PROMPT_EN = """## Optional: Service Site Cross-Validation

**Want to check if the company's website claims match their actual code?**

If you have access to the company's service website or product page, paste the URL below
and the AI will:
1. Read the website content
2. Compare claims against the code analysis above
3. Calculate a **Website Claim Match Rate** — how much of what they say is actually implemented
4. Flag any exaggerations or outright fabrications

This is like comparing a restaurant's menu photos with the actual dishes served.

```
Service site URL: [paste URL here if available]
```

If a URL is provided above, add this section to your report:

```
### Website vs Code — Claim Verification
Website Match Rate: ██████████████████░░░░░░░░░░░░░░ 65%

| Website Claim | Code Evidence | Match? |
|---------------|---------------|--------|
| "AI-powered analysis" | Found: OpenAI API calls only | ❌ Overstated |
| "End-to-end encryption" | Found: libsignal implementation | ✅ Verified |
| ... | ... | ... |

→ [Plain language summary of findings]
```
"""

_SITE_ANALYSIS_PROMPT_JA = """## オプション: サービスサイトとのクロス検証

**企業のWebサイトの主張が、実際のコードと一致しているか確認したいですか？**

サービスサイトやプロダクトページのURLがあれば、以下に貼り付けてください。
AIが以下を実行します:
1. Webサイトの内容を読み取り
2. 上記のコード分析結果と主張を照合
3. **Webサイト主張マッチ率**を算出 — 言っていることがどれだけ実装されているか
4. 誇張や虚偽の主張をフラグ付け

メニューの写真と実際に出てくる料理を比較するようなものです。

```
サービスサイトURL: [ここにURLを貼り付け]
```

URLが提供された場合は、レポートに以下のセクションを追加してください:

```
### Webサイト vs コード — 主張の検証
Webサイトマッチ率: ██████████████████░░░░░░░░░░░░░░ 65%

| Webサイトの主張 | コード上の証拠 | 一致? |
|-----------------|----------------|-------|
| 「AI分析搭載」 | 見つかった: OpenAI API呼び出しのみ | ❌ 過大表現 |
| 「エンドツーエンド暗号化」 | 見つかった: libsignal実装 | ✅ 検証済み |
| ... | ... | ... |

→ [平易な言葉での発見事項のまとめ]
```
"""

_QUESTION_INSTRUCTIONS_EN = """## Auto-Generate Questions for the Startup

Based on your analysis, generate 5-10 questions that an investor should ask the startup team.
**Use plain language that a non-technical investor can ask confidently.**

Focus on:
- Areas where claims could not be verified — "Your website says X, but we couldn't find evidence of X in the code. Can you explain?"
- Missing safeguards — "What happens if your main server goes down? Is there a backup plan?"
- Growth readiness — "If your users grow 10x, what needs to change in your technology?"
- Team risk — "How many people can maintain this system? What happens if the lead developer leaves?"
- Improvement plans — "What are your top 3 technical priorities for the next 6 months?"
- Data protection — "How do you protect user data? Have you had a security audit?"
"""

_QUESTION_INSTRUCTIONS_JA = """## スタートアップへの質問を自動生成

分析結果に基づき、投資家がスタートアップに聞くべき質問を5〜10個生成してください。
**IT用語を避け、非技術系の投資家が自信を持って聞ける表現にしてください。**

以下に焦点を当ててください:
- コードで検証できなかった主張 — 「御社のサイトには○○と書かれていますが、コード上では確認できませんでした。詳しく教えていただけますか？」
- 安全装置の不足 — 「メインサーバーが止まった場合、バックアップ体制はどうなっていますか？」
- 成長への備え — 「ユーザーが10倍に増えた場合、技術面で何を変える必要がありますか？」
- チームリスク — 「このシステムを維持できる人は何人いますか？ 主要開発者が抜けた場合は？」
- 改善計画 — 「今後6ヶ月の技術面での最優先課題は何ですか？」
- データ保護 — 「ユーザーデータの保護はどのように行っていますか？ セキュリティ監査を受けたことは？」
"""


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def _make_bar(value: float, width: int = 30) -> str:
    """Generate a status bar: ██████████░░░░░░░░░░"""
    filled = int(value / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def _format_langs(languages: dict[str, int]) -> str:
    if not languages:
        return "N/A"
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    top = sorted_langs[:5]
    parts = [f"{lang} ({count:,})" for lang, count in top]
    if len(sorted_langs) > 5:
        parts.append(f"+{len(sorted_langs) - 5} more")
    return ", ".join(parts)


def _collect_flags(result: AnalysisResult) -> list[RedFlag]:
    flags: list[RedFlag] = []
    flags.extend(result.code_analysis.red_flags)
    flags.extend(result.doc_analysis.red_flags)
    flags.extend(result.git_forensics.red_flags)
    flags.extend(result.consistency.red_flags)
    return flags


# ===========================================================================
# Consulting Prompt (--pdf mode)
# ===========================================================================


def generate_consulting_prompt(
    result: AnalysisResult,
    lang: str = "en",
    stage: str = "unknown",
) -> str:
    """Generate an enhanced prompt that instructs IDE AI to produce JSON + PDF.

    When ``dde prompt --pdf`` is used, this prompt replaces the standard one.
    It includes:
      - All heuristic data (same as normal prompt)
      - Role assignment (world-class consultant)
      - SWOT / future outlook / strategic advice / investment thesis instructions
      - Strict JSON output schema
      - ``dde report --consulting`` command to generate PDF
    """
    if lang == "ja":
        return _generate_consulting_ja(result, stage)
    return _generate_consulting_en(result, stage)


def _generate_consulting_en(result: AnalysisResult, stage: str) -> str:
    sections: list[str] = []

    sections.append(_CONSULTING_HEADER_EN)
    sections.append("## Glossary\n")
    for term, definition in GLOSSARY_EN.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## Heuristic Analysis Results\n")
    sections.append(_format_heuristic_en(result))

    sections.append("## Match Rate: Claims vs. Reality\n")
    sections.append(_format_match_rate_en(result))

    sections.append("## Red Flags Detected\n")
    sections.append(_format_red_flags_en(result))

    sections.append("## Scoring Framework (6 dimensions, 10-level scale)\n")
    for dim in DIMENSIONS_EN:
        sections.append(
            f"### {dim['name']} (Weight: {dim['weight']})\n"
            f"**Evaluate**: {dim['what']}\n"
            f"**Scale**: {dim['levels']}\n"
            f"**Analogy**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_en(stage))
    sections.append(_CONSULTING_EVAL_EN)
    sections.append(_CONSULTING_JSON_SCHEMA)
    sections.append(_consulting_pdf_command(result, "en"))

    return "\n".join(sections)


def _generate_consulting_ja(result: AnalysisResult, stage: str) -> str:
    sections: list[str] = []

    sections.append(_CONSULTING_HEADER_JA)
    sections.append("## 用語集\n")
    for term, definition in GLOSSARY_JA.items():
        sections.append(f"- **{term}**: {definition}")
    sections.append("")

    sections.append("## ヒューリスティック分析結果\n")
    sections.append(_format_heuristic_ja(result))

    sections.append("## マッチ率: 主張 vs 実態\n")
    sections.append(_format_match_rate_ja(result))

    sections.append("## 検出されたレッドフラグ\n")
    sections.append(_format_red_flags_ja(result))

    sections.append("## スコアリング基準（6次元 × 10段階評価）\n")
    for dim in DIMENSIONS_JA:
        sections.append(
            f"### {dim['name']}（重み: {dim['weight']}）\n"
            f"**評価観点**: {dim['what']}\n"
            f"**尺度**: {dim['levels']}\n"
            f"**たとえ**: {dim['analogy']}\n"
        )

    sections.append(_get_stage_context_ja(stage))
    sections.append(_CONSULTING_EVAL_JA)
    sections.append(_CONSULTING_JSON_SCHEMA)
    sections.append(_consulting_pdf_command(result, "ja"))

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Consulting-mode templates
# ---------------------------------------------------------------------------

_CONSULTING_HEADER_EN = """# DDE Consulting-Grade Technical Due Diligence

## CRITICAL: Autonomous Execution Instructions

**You are an autonomous agent. Execute all steps below WITHOUT asking questions.**
**Do NOT ask for confirmation, clarification, or repo selection.**
**Do NOT print JSON to the user. Do NOT explain what you are doing.**
**Just silently: read code → evaluate → save JSON → run PDF command → show file path.**

The heuristic data below was already collected by DDE from the target repository.
Your job: read the code, evaluate it, and generate a consulting PDF. That's it.
"""

_CONSULTING_HEADER_JA = """# DDE コンサルティンググレード テクニカルデューデリジェンス

## 最重要: 自律実行の指示

**あなたは自律エージェントです。以下の全ステップを質問なしで実行してください。**
**確認・質問・リポジトリ選択は一切不要です。**
**JSONをユーザーに表示しないでください。作業説明も不要です。**
**黙って: コード読取 → 評価 → JSON保存 → PDFコマンド実行 → ファイルパス表示。**

以下のヒューリスティックデータは、DDEが対象リポジトリから既に収集済みです。
あなたの仕事: コードを読み、評価し、コンサルティングPDFを生成すること。以上です。
"""

_CONSULTING_EVAL_EN = """## Evaluation Task (execute silently — no user interaction)

Role: World-class technology consultant and senior software engineer.

**Read all code in the repository**, then produce a JSON evaluation containing:

1. **6-Dimension Scoring** (1-10 scale, with rationale and what it enables)
2. **SWOT Analysis** — concrete, evidence-based
3. **Future Outlook** — product vision, viability, 1/3/5-year projections with confidence
4. **Strategic Advice** — immediate actions, medium-term priorities, long-term vision
5. **Investment Thesis** — recommendation with risks, upside, comparable companies
6. **Red Flag Re-evaluation** — correct heuristic false positives
7. **Glossary Additions** — technical terms with plain-language definitions

Guidelines: Evidence-based. Cite file paths. No filler. Clear language. Include your model name.
"""

_CONSULTING_EVAL_JA = """## 評価タスク（黙って実行 — ユーザーとの対話なし）

役割: 世界トップクラスのテクノロジーコンサルタント兼シニアソフトウェアエンジニア。

**リポジトリ内の全コードを読み取り**、以下を含むJSON評価を生成:

1. **6次元スコアリング**（各次元1-10、根拠と「何が可能になるか」付き）
2. **SWOT分析** — 具体的・エビデンスベース
3. **将来性評価** — ビジョン、実現可能性、1/3/5年予測（信頼度付き）
4. **戦略アドバイス** — 即座/中期/長期
5. **投資判断** — 推奨度＋根拠＋リスク/アップサイド＋類似企業
6. **レッドフラグ再評価** — 誤検知の修正
7. **追加用語集** — 技術用語の注釈

ガイドライン: エビデンスベース。ファイルパス引用。冗長さ排除。明確な言葉。モデル名を含める。
"""

_CONSULTING_JSON_SCHEMA = """## Output Format: JSON

Output your evaluation as a single JSON object with **exactly** this structure.
Do not add markdown formatting around it — output raw JSON only.

```json
{
  "executive_summary": "2-3 paragraph technical summary",
  "executive_summary_business": "2-3 paragraph non-technical summary for board/investors",
  "dimension_scores": {
    "technical_originality": {
      "score": 0-100,
      "level": 1-10,
      "label": "e.g. Original, Extended, Frontier",
      "rationale": "evidence-based explanation",
      "business_explanation": "what this means in business terms",
      "enables": "what this capability makes possible"
    },
    "technology_advancement": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "implementation_depth": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "architecture_quality": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "claim_consistency": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" },
    "security_posture": { "score": 0-100, "level": 1-10, "label": "", "rationale": "", "business_explanation": "", "enables": "" }
  },
  "overall_score": 0-100,
  "grade": "A|B|C|D|F",
  "swot": {
    "strengths": [
      { "point": "title", "explanation": "detail", "business_analogy": "real-world comparison" }
    ],
    "weaknesses": [
      { "point": "title", "explanation": "detail", "business_impact": "consequence" }
    ],
    "opportunities": [
      { "point": "title", "explanation": "detail", "potential_value": "upside" }
    ],
    "threats": [
      { "point": "title", "explanation": "detail", "mitigation": "how to address" }
    ]
  },
  "future_outlook": {
    "product_vision": "what this product/service is trying to achieve",
    "viability_assessment": "can they pull it off? why or why not?",
    "year_1": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] },
    "year_3": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] },
    "year_5": { "projection": "...", "confidence": "high|medium|low", "key_milestones": ["..."] }
  },
  "strategic_advice": {
    "immediate_actions": [
      { "action": "what to do", "rationale": "why", "expected_impact": "outcome" }
    ],
    "medium_term": [
      { "action": "what to do", "rationale": "why", "expected_impact": "outcome" }
    ],
    "long_term_vision": "where this should be heading"
  },
  "investment_thesis": {
    "recommendation": "strong_invest|invest_with_conditions|cautious|pass|strong_pass",
    "rationale": "3-5 sentences explaining the recommendation",
    "key_risks": ["risk 1", "risk 2"],
    "key_upside": ["upside 1", "upside 2"],
    "comparable_companies": ["company 1", "company 2"],
    "suggested_valuation_factors": "what affects valuation"
  },
  "red_flags": [
    { "title": "flag title", "description": "detail", "severity": "critical|high|medium|low", "business_impact": "impact" }
  ],
  "tech_level_summary": {
    "overall_level": 1-10,
    "overall_label": "e.g. Production-Grade",
    "plain_explanation": "what this level means in everyday terms"
  },
  "glossary_additions": [
    { "term": "technical term", "definition": "plain-language explanation" }
  ],
  "ai_model_used": "your model name (e.g. Claude Sonnet 4, GPT-4o, etc.)"
}
```
"""


def _consulting_pdf_command(result: AnalysisResult, lang: str) -> str:
    """Generate the final instruction to save JSON and produce PDF."""
    from datetime import datetime

    project_safe = result.project_name.replace("/", "_").replace("\\", "_")
    date_stamp = datetime.now().strftime("%Y%m%d")
    filename = f"dde_consulting_{project_safe}_{date_stamp}.json"

    if lang == "ja":
        return f"""## 実行手順（質問せずに全て実行すること）

**Step 1**: リポジトリのコードを読み取り、上記スキーマに従ったJSONを生成する
**Step 2**: JSONを `/tmp/{filename}` に保存する（Write toolまたはcatコマンドで）
**Step 3**: 以下のコマンドを実行する:

```bash
dde report --consulting /tmp/{filename} --pdf --lang ja
```

**Step 4**: PDFは `~/Downloads/` に保存される。ファイルパスをユーザーに伝える

**禁止事項:**
- JSONの内容をユーザーに表示しない
- 「どのリポジトリを分析しますか」等の質問をしない
- 作業の途中経過を説明しない
- 実行前に許可を求めない（ツール実行の同意のみ必要）
"""
    else:
        return f"""## Execution Steps (do NOT ask questions — just execute)

**Step 1**: Read the repository code and generate JSON following the schema above
**Step 2**: Save JSON to `/tmp/{filename}` (via Write tool or cat command)
**Step 3**: Run this command:

```bash
dde report --consulting /tmp/{filename} --pdf --lang en
```

**Step 4**: PDF is saved to `~/Downloads/`. Tell the user the file path.

**Do NOT:**
- Print the JSON to the user
- Ask "which repository?" or any clarification questions
- Explain what you are doing step by step
- Ask for permission before executing (only tool approval is needed)
"""
